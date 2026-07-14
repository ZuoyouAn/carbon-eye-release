from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any

import requests


CACHE_TTL = timedelta(minutes=10)
WAQI_ENDPOINT = "https://api.waqi.info/feed/geo:31.316;120.700/"
WAQI_DOCUMENTATION_URL = "https://aqicn.org/api/"
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
    "pm25": "µg/m3",
    "pm10": "µg/m3",
    "o3": "µg/m3",
    "no2": "µg/m3",
    "so2": "µg/m3",
    "co": "mg/m3",
}
_cache: dict[str, Any] = {"fetched_at": None, "data": None}


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def unavailable(message: str) -> dict[str, Any]:
    return {
        "station": "苏州工业园区附近公开空气质量接口",
        "source": "WAQI Data Platform API",
        "source_url": WAQI_DOCUMENTATION_URL,
        "status": "unavailable",
        "message": message,
        "fetched_at": now_iso(),
        "cache_ttl_seconds": int(CACHE_TTL.total_seconds()),
        "cached": False,
        "items": [],
        "boundary": "仅用于当前展示；不归档或再分发第三方历史观测，也不代表园区内部连续监测。",
    }


def fetch_from_waqi(token: str) -> dict[str, Any]:
    response = requests.get(
        WAQI_ENDPOINT,
        params={"token": token},
        timeout=15,
        headers={"User-Agent": "CarbonEye-Academic-Prototype/2.0"},
    )
    response.raise_for_status()
    payload = response.json()
    if payload.get("status") != "ok" or not isinstance(payload.get("data"), dict):
        raise RuntimeError("WAQI returned an unavailable response")

    data = payload["data"]
    iaqi = data.get("iaqi") or {}
    items = []
    for pollutant, label in POLLUTANT_LABELS.items():
        value = data.get("aqi") if pollutant == "aqi" else (iaqi.get(pollutant) or {}).get("v")
        if value is None:
            continue
        items.append(
            {
                "pollutant": pollutant,
                "label": label,
                "current_value": value,
                "current_numeric": value,
                "min_value": None,
                "min_numeric": None,
                "max_value": None,
                "max_numeric": None,
                "unit": POLLUTANT_UNITS[pollutant],
            }
        )

    city = data.get("city") or {}
    time_info = data.get("time") or {}
    return {
        "station": city.get("name") or "苏州工业园区附近公开空气质量接口",
        "source": "WAQI Data Platform API",
        "source_url": WAQI_DOCUMENTATION_URL,
        "status": "ok",
        "message": "实时空气质量数据已从正式API获取。",
        "updated_at": time_info.get("s"),
        "fetched_at": now_iso(),
        "cache_ttl_seconds": int(CACHE_TTL.total_seconds()),
        "cached": False,
        "items": items,
        "boundary": "仅用于当前展示；不归档或再分发第三方历史观测，也不代表园区内部连续监测。",
    }


def get_realtime_aqi() -> dict[str, Any]:
    token = os.getenv("AQICN_TOKEN", "").strip()
    if not token:
        return unavailable("未配置实时接口，因此不展示实时数值。")

    now = datetime.now(timezone.utc)
    cached_at = _cache.get("fetched_at")
    cached_data = _cache.get("data")
    if cached_at and cached_data and now - cached_at < CACHE_TTL:
        result = dict(cached_data)
        result["cached"] = True
        return result

    try:
        result = fetch_from_waqi(token)
        _cache["fetched_at"] = now
        _cache["data"] = result
        return result
    except (requests.RequestException, ValueError, RuntimeError):
        if cached_data:
            result = dict(cached_data)
            result["status"] = "stale"
            result["cached"] = True
            result["message"] = "实时接口暂不可用，正在展示最近一次内存缓存。"
            return result
        return unavailable("实时接口暂不可用，请稍后重试。")
