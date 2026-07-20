from __future__ import annotations

import asyncio
import re
from datetime import datetime, timedelta, timezone
from threading import Lock
from typing import Any

import requests
from lxml import html


# The public station page is used only for the current dashboard state.  Values
# stay in process memory and are never written into the project data archive.
CACHE_TTL = timedelta(hours=1)
AQICN_STATION_URL = "https://aqicn.org/city/jiangsu/suzhou/suzhougongyeyuanqu/cn/"
POLLUTANTS = ("aqi", "pm25", "pm10", "o3", "no2", "so2", "co")
POLLUTANT_LABELS = {
    "aqi": "AQI",
    "pm25": "PM2.5",
    "pm10": "PM10",
    "o3": "O3",
    "no2": "NO2",
    "so2": "SO2",
    "co": "CO",
}
POLLUTANT_UNITS = {
    "aqi": "AQI",
    "pm25": "ug/m3",
    "pm10": "ug/m3",
    "o3": "ug/m3",
    "no2": "ug/m3",
    "so2": "ug/m3",
    "co": "mg/m3",
}
_cache: dict[str, Any] = {"fetched_at": None, "data": None}
_cache_lock = Lock()


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _read_cell(document: html.HtmlElement, element_id: str) -> str | None:
    values = document.xpath(f'//*[@id="{element_id}"]//text()')
    text = " ".join(value.strip() for value in values if value.strip()).strip()
    return text or None


def _number(value: str | None) -> float | None:
    if not value:
        return None
    match = re.search(r"[-+]?\d+(?:\.\d+)?", value.replace(",", ""))
    return float(match.group()) if match else None


def _display_number(value: float | None, fallback: str | None) -> str | None:
    if value is None:
        return fallback
    return str(int(value)) if value.is_integer() else f"{value:.3f}".rstrip("0").rstrip(".")


def _build_item(document: html.HtmlElement, pollutant: str) -> dict[str, Any] | None:
    current_text = _read_cell(document, f"cur_{pollutant}")
    minimum_text = _read_cell(document, f"min_{pollutant}")
    maximum_text = _read_cell(document, f"max_{pollutant}")

    # AQICN's page normally exposes cur_/min_/max_ IDs.  Keep a row fallback
    # for harmless markup rearrangements of the supplied crawler target.
    if not current_text:
        row_values = document.xpath(f'//tr[@id="tr_{pollutant}"]//td//text()')
        normalized = [value.strip() for value in row_values if value.strip()]
        if len(normalized) >= 2:
            current_text = normalized[1]
            minimum_text = minimum_text or (normalized[2] if len(normalized) > 2 else None)
            maximum_text = maximum_text or (normalized[3] if len(normalized) > 3 else None)

    current_numeric = _number(current_text)
    if current_numeric is None:
        return None
    minimum_numeric = _number(minimum_text)
    maximum_numeric = _number(maximum_text)
    return {
        "pollutant": pollutant,
        "label": POLLUTANT_LABELS[pollutant],
        "current_value": _display_number(current_numeric, current_text),
        "current_numeric": current_numeric,
        "min_value": _display_number(minimum_numeric, minimum_text),
        "min_numeric": minimum_numeric,
        "max_value": _display_number(maximum_numeric, maximum_text),
        "max_numeric": maximum_numeric,
        "unit": POLLUTANT_UNITS[pollutant],
    }


def fetch_from_aqicn_page() -> dict[str, Any]:
    response = requests.get(
        AQICN_STATION_URL,
        timeout=20,
        headers={"User-Agent": "CarbonEye-Academic-Prototype/2.1 (+https://carbon-eye-sip.netlify.app)"},
    )
    response.raise_for_status()
    document = html.fromstring(response.content)
    items = [item for pollutant in POLLUTANTS if pollutant != "aqi" and (item := _build_item(document, pollutant))]
    aqi_text = _read_cell(document, "aqiwgtvalue") or _read_cell(document, "cur_aqi")
    aqi_numeric = _number(aqi_text)
    if aqi_numeric is not None:
        items.insert(
            0,
            {
                "pollutant": "aqi",
                "label": "AQI",
                "current_value": _display_number(aqi_numeric, aqi_text),
                "current_numeric": aqi_numeric,
                "min_value": None,
                "min_numeric": None,
                "max_value": None,
                "max_numeric": None,
                "unit": "AQI",
            },
        )
    if not items:
        raise RuntimeError("AQICN station page did not contain current pollutant values")

    return {
        "station": "苏州工业园区 AQICN 公开站点页面",
        "source": "AQICN public station page",
        "source_url": AQICN_STATION_URL,
        "status": "ok",
        "message": "公开站点页面抓取成功；仅展示当前状态。",
        "updated_at": _read_cell(document, "aqiwgtutime"),
        "fetched_at": now_iso(),
        "cache_ttl_seconds": int(CACHE_TTL.total_seconds()),
        "refresh_policy": "best-effort hourly in-memory refresh and refresh-on-demand after cache expiry",
        "cached": False,
        "items": items,
        "boundary": "当前公开页面状态，不归档或再分发第三方历史观测；不代表园区内部连续监测。",
    }


def unavailable(message: str) -> dict[str, Any]:
    return {
        "station": "苏州工业园区 AQICN 公开站点页面",
        "source": "AQICN public station page",
        "source_url": AQICN_STATION_URL,
        "status": "unavailable",
        "message": message,
        "updated_at": None,
        "fetched_at": now_iso(),
        "cache_ttl_seconds": int(CACHE_TTL.total_seconds()),
        "refresh_policy": "best-effort hourly in-memory refresh and refresh-on-demand after cache expiry",
        "cached": False,
        "items": [],
        "boundary": "当前公开页面状态，不归档或再分发第三方历史观测；不代表园区内部连续监测。",
    }


def get_realtime_aqi(force_refresh: bool = False) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    with _cache_lock:
        cached_at = _cache.get("fetched_at")
        cached_data = _cache.get("data")
        if not force_refresh and cached_at and cached_data and now - cached_at < CACHE_TTL:
            result = dict(cached_data)
            result["cached"] = True
            return result

        try:
            result = fetch_from_aqicn_page()
            _cache["fetched_at"] = now
            _cache["data"] = result
            return result
        except (requests.RequestException, ValueError, RuntimeError, OSError) as exc:
            if cached_data:
                result = dict(cached_data)
                result["status"] = "stale"
                result["cached"] = True
                result["message"] = "公开站点页面本次刷新失败，展示最近一次内存缓存。"
                result["refresh_error"] = type(exc).__name__
                return result
            return unavailable("公开站点页面暂不可用，请稍后重试。")


async def refresh_realtime_aqi_hourly(stop_event: asyncio.Event) -> None:
    """Best-effort scheduler for a running service; request-time refresh is the fallback."""
    while not stop_event.is_set():
        await asyncio.to_thread(get_realtime_aqi, True)
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=CACHE_TTL.total_seconds())
        except TimeoutError:
            continue
