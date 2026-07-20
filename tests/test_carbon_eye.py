from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "backend" / "data" / "carbon_eye"
os.environ["CARBON_EYE_STANDALONE"] = "true"
sys.path.insert(0, str(ROOT / "backend"))

import main as backend_main  # noqa: E402
import carbon_eye_realtime  # noqa: E402


def read_json(name: str):
    return json.loads((DATA_DIR / name).read_text(encoding="utf-8"))


def test_release_data_boundaries_and_counts():
    monthly = read_json("monthly_trends.json")
    electricity = read_json("park_electricity_emissions.json")
    snapshot = read_json("park_environment_snapshot.json")
    industry = read_json("industry_profile.json")

    assert len(monthly) == 152
    july = next(item for item in monthly if item["date"] == "2026-07")
    assert july["is_partial"] is True
    assert july["excluded_from_annual_statistics"] is True
    assert electricity["missing_years"] == [2020, 2021, 2022]
    assert len(electricity["records"]) == 4
    assert [item["year"] for item in electricity["year_slots"]] == list(range(2019, 2026))
    missing_slots = [item for item in electricity["year_slots"] if item["record_status"] == "missing"]
    assert [item["year"] for item in missing_slots] == [2020, 2021, 2022]
    assert all(item["total_electricity_100m_kwh"] is None for item in missing_slots)
    assert all(item["missing_reason"] for item in missing_slots)
    assert len(snapshot["sites"]) == 6
    assert len(snapshot["records"]) == 84
    assert len(industry["profiles"]) == 6


def test_electricity_proxy_formula_is_reproducible():
    data = read_json("park_electricity_emissions.json")
    for item in data["records"]:
        expected = item["total_electricity_100m_kwh"] * 10 * item["factor_kgco2_per_kwh"]
        assert abs(expected - item["total_purchased_electricity_scope2_10k_tco2"]) <= 0.0011
        for key in ("source_url", "source_period", "data_quality", "factor_reference_year", "method", "scope", "limitations", "missing_reason"):
            assert key in item


def test_provenance_registry_has_sources_and_checksums():
    registry = read_json("data_provenance_registry.json")
    assert len(registry["sources"]) == 12
    assert registry["known_gaps"]["electricity_2020_2022"]
    assert registry["known_gaps"]["air_quality_original_platform"]
    assert all(len(item["sha256"]) == 64 for item in registry["file_manifest"])


def test_weather_and_cdci_limits():
    weather = read_json("weather/weather_park_monthly.json")
    correlations = read_json("weather/weather_air_correlations.json")
    cdci = read_json("cdci.json")

    assert len(weather["records"]) >= 145
    assert all(item["is_complete"] is True for item in weather["records"])
    assert correlations["metadata"]["last_month"] == "2026-06"
    assert "相关不等于因果" in correlations["metadata"]["warning"]
    assert len(cdci["records"]) == 48
    assert {item["year"] for item in cdci["records"]} == {2019, 2023, 2024, 2025}


def test_static_api_endpoints_work_without_database():
    endpoints = [
        "/healthz",
        "/api/carbon-eye/overview",
        "/api/carbon-eye/monthly-trends",
        "/api/carbon-eye/weather-2024",
        "/api/carbon-eye/carbon-emissions",
        "/api/carbon-eye/warnings",
        "/api/carbon-eye/daily-cases",
        "/api/carbon-eye/methodology",
        "/api/carbon-eye/park-electricity-emissions",
        "/api/carbon-eye/economic-carbon-intensity",
        "/api/carbon-eye/park-environment-snapshot",
        "/api/carbon-eye/weather-long-term",
        "/api/carbon-eye/weather-correlations",
        "/api/carbon-eye/cdci",
        "/api/carbon-eye/cdci-sensitivity",
        "/api/carbon-eye/industry-profile",
        "/api/carbon-eye/data-quality",
        "/api/carbon-eye/sources",
    ]
    realtime_payload = {"status": "unavailable", "items": [], "message": "test response"}
    with patch.object(backend_main, "get_realtime_aqi", return_value=realtime_payload):
        with TestClient(backend_main.app) as client:
            for endpoint in endpoints:
                response = client.get(endpoint)
                assert response.status_code == 200, endpoint
            realtime = client.get("/api/carbon-eye/realtime-aqi")
            assert realtime.status_code == 200
            assert realtime.json()["status"] == "unavailable"


def test_realtime_page_parser_normalizes_current_minimum_and_maximum_values():
    document = carbon_eye_realtime.html.fromstring(
        "<table><tr id='tr_aqi'><td>AQI</td><td id='cur_aqi'>76</td><td id='min_aqi'>21</td><td id='max_aqi'>109</td></tr>"
        "<tr id='tr_pm25'><td>PM2.5</td><td id='cur_pm25'>35.2</td><td id='min_pm25'>12</td><td id='max_pm25'>48</td></tr></table>"
    )
    aqi = carbon_eye_realtime._build_item(document, "aqi")
    pm25 = carbon_eye_realtime._build_item(document, "pm25")

    assert aqi["current_numeric"] == 76
    assert aqi["min_value"] == "21"
    assert aqi["max_value"] == "109"
    assert pm25["current_value"] == "35.2"
    assert pm25["unit"] == "ug/m3"


def test_realtime_page_uses_aqicn_widget_value_for_aqi():
    document = carbon_eye_realtime.html.fromstring("<div id='aqiwgtvalue'>44</div><div id='aqiwgtutime'>更新时间 星期一17:00</div>")
    assert carbon_eye_realtime._number(carbon_eye_realtime._read_cell(document, "aqiwgtvalue")) == 44
    assert carbon_eye_realtime._read_cell(document, "aqiwgtutime") == "更新时间 星期一17:00"


def test_missing_static_json_returns_readable_503(tmp_path):
    with patch.object(backend_main, "CARBON_EYE_DATA_DIR", tmp_path):
        with TestClient(backend_main.app) as client:
            response = client.get("/api/carbon-eye/overview")
    assert response.status_code == 503
    detail = response.json()["detail"]
    assert detail["missing_file"] == "overview.json"
    assert "build_carbon_eye_data.py" in detail["generation_command"]
