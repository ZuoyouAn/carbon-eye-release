#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Download and aggregate long-term weather for Suzhou Industrial Park.

Data source: Open-Meteo Historical Weather API, fixed ERA5 model.
Spatial method: download each of six official SIP environmental monitoring sites,
then aggregate to a park-scale monthly series.

No API key is required for non-commercial Open-Meteo usage. The script never
fabricates values: if the API is unavailable or validation fails, it exits with
an error and does not replace previous valid outputs.
"""
from __future__ import annotations

import argparse
import calendar
import csv
import json
import math
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from statistics import mean
from typing import Any, Iterable

SCRIPT_DIR = Path(__file__).resolve().parent
BUNDLE_ROOT = SCRIPT_DIR.parent
DEFAULT_SITE_FILE = BUNDLE_ROOT / "01_data" / "sip_monitoring_sites.csv"
DEFAULT_OUTPUT_DIR = BUNDLE_ROOT / "01_data" / "weather"
API_ENDPOINT = "https://archive-api.open-meteo.com/v1/archive"
SOURCE_DOC = "https://open-meteo.com/en/docs/historical-weather-api"
DAILY_VARIABLES = [
    "temperature_2m_mean",
    "relative_humidity_2m_mean",
    "precipitation_sum",
    "sunshine_duration",
    "shortwave_radiation_sum",
    "wind_speed_10m_mean",
    "wind_direction_10m_dominant",
    "pressure_msl_mean",
]


def last_day_previous_month(today: date | None = None) -> date:
    today = today or date.today()
    return today.replace(day=1) - timedelta(days=1)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch ERA5 daily weather for six SIP sites and aggregate monthly.")
    parser.add_argument("--start-date", default="2013-12-01", help="YYYY-MM-DD")
    parser.add_argument(
        "--end-date",
        default=last_day_previous_month().isoformat(),
        help="YYYY-MM-DD; defaults to last day of the previous complete month",
    )
    parser.add_argument("--site-file", type=Path, default=DEFAULT_SITE_FILE)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--model", default="era5", help="Use era5 for a consistent long-term series")
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--retries", type=int, default=4)
    parser.add_argument("--force", action="store_true", help="Ignore cached raw API responses")
    return parser.parse_args()


def validate_iso_date(value: str) -> date:
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValueError(f"Invalid date {value!r}; expected YYYY-MM-DD") from exc


def read_sites(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"Site file not found: {path}")
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    required = {"site_id", "site_name", "longitude", "latitude", "functional_zone"}
    if not rows or not required.issubset(rows[0]):
        raise ValueError(f"Site file missing required columns: {sorted(required)}")
    if len(rows) != 6:
        raise ValueError(f"Expected exactly six official monitoring sites, got {len(rows)}")
    for row in rows:
        row["longitude"] = float(row["longitude"])
        row["latitude"] = float(row["latitude"])
    return rows


def api_url(site: dict[str, Any], start_date: str, end_date: str, model: str) -> str:
    params = {
        "latitude": f"{site['latitude']:.6f}",
        "longitude": f"{site['longitude']:.6f}",
        "start_date": start_date,
        "end_date": end_date,
        "daily": ",".join(DAILY_VARIABLES),
        "timezone": "Asia/Shanghai",
        "models": model,
        "wind_speed_unit": "kmh",
    }
    return API_ENDPOINT + "?" + urllib.parse.urlencode(params)


def fetch_json(url: str, timeout: int, retries: int) -> dict[str, Any]:
    headers = {
        "User-Agent": "CarbonEye-Academic-Prototype/1.0 (+non-commercial research)",
        "Accept": "application/json",
    }
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            request = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(request, timeout=timeout) as response:
                body = response.read()
                if response.status != 200:
                    raise RuntimeError(f"HTTP {response.status}: {body[:200]!r}")
                return json.loads(body.decode("utf-8"))
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError, RuntimeError) as exc:
            last_error = exc
            if attempt < retries:
                time.sleep(min(2 ** attempt, 10))
    raise RuntimeError(f"Failed after {retries} attempts: {last_error}")


def atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(content, encoding="utf-8")
    temp.replace(path)


def save_csv_atomic(path: Path, fieldnames: list[str], rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    with temp.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    temp.replace(path)


def validate_response(payload: dict[str, Any], site_id: str) -> tuple[dict[str, list[Any]], dict[str, Any]]:
    if payload.get("error"):
        raise ValueError(f"Open-Meteo error for {site_id}: {payload.get('reason')}")
    daily = payload.get("daily")
    units = payload.get("daily_units", {})
    if not isinstance(daily, dict) or "time" not in daily:
        raise ValueError(f"No daily data returned for {site_id}")
    expected = ["time", *DAILY_VARIABLES]
    missing = [v for v in expected if v not in daily]
    if missing:
        raise ValueError(f"Missing variables for {site_id}: {missing}")
    lengths = {key: len(daily[key]) for key in expected}
    if len(set(lengths.values())) != 1:
        raise ValueError(f"Mismatched array lengths for {site_id}: {lengths}")
    if lengths["time"] == 0:
        raise ValueError(f"Empty response for {site_id}")
    return daily, units


def to_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def circular_mean_deg(values: list[tuple[float, float]]) -> float | None:
    """Weighted circular mean. Tuple is (degrees, non-negative weight)."""
    usable = [(deg, max(weight, 0.0)) for deg, weight in values if deg is not None and weight is not None]
    if not usable:
        return None
    if sum(w for _, w in usable) == 0:
        usable = [(deg, 1.0) for deg, _ in usable]
    x = sum(math.cos(math.radians(deg)) * w for deg, w in usable)
    y = sum(math.sin(math.radians(deg)) * w for deg, w in usable)
    if abs(x) < 1e-12 and abs(y) < 1e-12:
        return None
    return math.degrees(math.atan2(y, x)) % 360


def safe_mean(values: Iterable[float | None]) -> float | None:
    usable = [v for v in values if v is not None]
    return mean(usable) if usable else None


def safe_sum(values: Iterable[float | None]) -> float | None:
    usable = [v for v in values if v is not None]
    return sum(usable) if usable else None


def round_or_none(value: float | None, digits: int = 3) -> float | None:
    return None if value is None else round(value, digits)


def aggregate_monthly(daily_rows: list[dict[str, Any]], site_count_expected: int) -> list[dict[str, Any]]:
    by_site_month: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in daily_rows:
        month = row["date"][:7]
        by_site_month[(row["site_id"], month)].append(row)

    site_month_rows: list[dict[str, Any]] = []
    for (site_id, month), rows in sorted(by_site_month.items()):
        wind_values = [
            (r["wind_direction_10m_dominant"], r["wind_speed_10m_mean"] or 0.0)
            for r in rows
            if r["wind_direction_10m_dominant"] is not None
        ]
        site_month_rows.append({
            "site_id": site_id,
            "month": month,
            "avg_temp_c": safe_mean(r["temperature_2m_mean"] for r in rows),
            "relative_humidity_pct": safe_mean(r["relative_humidity_2m_mean"] for r in rows),
            "precipitation_mm": safe_sum(r["precipitation_sum"] for r in rows),
            "sunshine_hours": (safe_sum(r["sunshine_duration"] for r in rows) or 0.0) / 3600.0,
            "shortwave_radiation_mj_m2": safe_sum(r["shortwave_radiation_sum"] for r in rows),
            "avg_wind_speed_kmh": safe_mean(r["wind_speed_10m_mean"] for r in rows),
            "dominant_wind_direction_deg": circular_mean_deg(wind_values),
            "pressure_msl_hpa": safe_mean(r["pressure_msl_mean"] for r in rows),
            "days_observed": len({r["date"] for r in rows}),
        })

    by_month: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in site_month_rows:
        by_month[row["month"]].append(row)

    monthly: list[dict[str, Any]] = []
    for month, rows in sorted(by_month.items()):
        year, mon = map(int, month.split("-"))
        expected_days = calendar.monthrange(year, mon)[1]
        actual_site_days = sum(r["days_observed"] for r in rows)
        expected_site_days = expected_days * site_count_expected
        wind_values = [
            (r["dominant_wind_direction_deg"], r["avg_wind_speed_kmh"] or 0.0)
            for r in rows if r["dominant_wind_direction_deg"] is not None
        ]
        coverage = actual_site_days / expected_site_days * 100 if expected_site_days else 0
        monthly.append({
            "month": month,
            "avg_temp_c": round_or_none(safe_mean(r["avg_temp_c"] for r in rows)),
            "relative_humidity_pct": round_or_none(safe_mean(r["relative_humidity_pct"] for r in rows)),
            "precipitation_mm": round_or_none(safe_mean(r["precipitation_mm"] for r in rows)),
            "sunshine_hours": round_or_none(safe_mean(r["sunshine_hours"] for r in rows)),
            "shortwave_radiation_mj_m2": round_or_none(safe_mean(r["shortwave_radiation_mj_m2"] for r in rows)),
            "avg_wind_speed_kmh": round_or_none(safe_mean(r["avg_wind_speed_kmh"] for r in rows)),
            "dominant_wind_direction_deg": round_or_none(circular_mean_deg(wind_values), 1),
            "pressure_msl_hpa": round_or_none(safe_mean(r["pressure_msl_hpa"] for r in rows)),
            "site_count": len(rows),
            "days_observed": min(r["days_observed"] for r in rows) if rows else 0,
            "coverage_pct": round(coverage, 2),
            "is_complete": len(rows) == site_count_expected and coverage >= 95.0,
        })
    return monthly


def main() -> int:
    args = parse_args()
    start = validate_iso_date(args.start_date)
    end = validate_iso_date(args.end_date)
    if end < start:
        raise ValueError("end-date must be on or after start-date")
    if end >= date.today():
        raise ValueError("end-date must be in the past; use completed historical dates only")

    sites = read_sites(args.site_file)
    output_dir = args.output_dir.resolve()
    raw_dir = output_dir / "raw_open_meteo"
    raw_dir.mkdir(parents=True, exist_ok=True)
    error_log = output_dir / "weather_fetch_error.log"

    all_rows: list[dict[str, Any]] = []
    source_units: dict[str, Any] = {}
    try:
        for idx, site in enumerate(sites, start=1):
            cache = raw_dir / f"{site['site_id']}_{args.start_date}_{args.end_date}_{args.model}.json"
            url = api_url(site, args.start_date, args.end_date, args.model)
            print(f"[{idx}/{len(sites)}] {site['site_id']} {site['site_name']}")
            if cache.exists() and not args.force:
                payload = json.loads(cache.read_text(encoding="utf-8"))
                print(f"  using cache: {cache.name}")
            else:
                payload = fetch_json(url, timeout=args.timeout, retries=args.retries)
                atomic_write_text(cache, json.dumps(payload, ensure_ascii=False, indent=2))
                print("  downloaded")
            daily, units = validate_response(payload, site["site_id"])
            source_units = source_units or units
            for i, day in enumerate(daily["time"]):
                row = {
                    "site_id": site["site_id"],
                    "site_name": site["site_name"],
                    "functional_zone": site["functional_zone"],
                    "requested_longitude": site["longitude"],
                    "requested_latitude": site["latitude"],
                    "grid_longitude": payload.get("longitude"),
                    "grid_latitude": payload.get("latitude"),
                    "elevation_m": payload.get("elevation"),
                    "date": day,
                }
                for variable in DAILY_VARIABLES:
                    row[variable] = to_float(daily[variable][i])
                all_rows.append(row)
    except Exception as exc:
        error_log.write_text(
            f"{datetime.now().isoformat()}\n{type(exc).__name__}: {exc}\n",
            encoding="utf-8",
        )
        print(f"ERROR: {exc}", file=sys.stderr)
        print(f"Details: {error_log}", file=sys.stderr)
        return 2

    if not all_rows:
        print("ERROR: no weather rows downloaded", file=sys.stderr)
        return 2

    missing_count = sum(
        1 for row in all_rows for var in DAILY_VARIABLES if row[var] is None
    )
    total_values = len(all_rows) * len(DAILY_VARIABLES)
    missing_pct = missing_count / total_values * 100 if total_values else 100.0
    if missing_pct > 1.0:
        print(f"ERROR: missing weather values {missing_pct:.2f}% exceeds 1% threshold", file=sys.stderr)
        return 3

    monthly = aggregate_monthly(all_rows, site_count_expected=len(sites))
    incomplete = [r["month"] for r in monthly if not r["is_complete"]]
    if incomplete:
        print(f"WARNING: incomplete months detected: {incomplete[:12]}")

    daily_fields = [
        "site_id", "site_name", "functional_zone", "requested_longitude", "requested_latitude",
        "grid_longitude", "grid_latitude", "elevation_m", "date", *DAILY_VARIABLES,
    ]
    monthly_fields = list(monthly[0].keys())
    save_csv_atomic(output_dir / "weather_site_daily.csv", daily_fields, all_rows)
    save_csv_atomic(output_dir / "weather_park_monthly.csv", monthly_fields, monthly)

    metadata = {
        "dataset_name": "苏州工业园区六点位ERA5长期气象月度数据",
        "source": "Open-Meteo Historical Weather API / ERA5",
        "source_documentation": SOURCE_DOC,
        "model": args.model,
        "timezone": "Asia/Shanghai",
        "start_date": args.start_date,
        "end_date": args.end_date,
        "site_count": len(sites),
        "spatial_method": "六个官方环境监测点逐点下载，连续变量按点位平均；主导风向采用风速加权圆形平均",
        "temporal_method": "日数据聚合到月；降水、日照和短波辐射先按点月累计，再做六点平均",
        "units_from_api": source_units,
        "non_causal_warning": "气象与污染物相关性仅用于解释，不代表因果关系。",
        "generated_at": datetime.now().astimezone().isoformat(),
    }
    atomic_write_text(
        output_dir / "weather_park_monthly.json",
        json.dumps({"metadata": metadata, "records": monthly}, ensure_ascii=False, indent=2),
    )
    validation = {
        "status": "pass" if not incomplete and missing_pct <= 1.0 else "warning",
        "daily_rows": len(all_rows),
        "monthly_rows": len(monthly),
        "expected_sites": len(sites),
        "missing_value_count": missing_count,
        "missing_value_pct": round(missing_pct, 4),
        "incomplete_months": incomplete,
        "first_month": monthly[0]["month"],
        "last_month": monthly[-1]["month"],
        "generated_at": metadata["generated_at"],
    }
    atomic_write_text(
        output_dir / "weather_validation_summary.json",
        json.dumps(validation, ensure_ascii=False, indent=2),
    )
    if error_log.exists():
        error_log.unlink()

    print(f"Done: {len(all_rows)} site-day records, {len(monthly)} park-month records")
    print(output_dir / "weather_park_monthly.csv")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("Cancelled.", file=sys.stderr)
        raise SystemExit(130)
    except Exception as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(2)
