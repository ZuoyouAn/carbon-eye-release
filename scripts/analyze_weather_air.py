#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Merge long-term SIP weather with monthly air-quality data and compute correlations.

This script uses only the Python standard library. It reports Pearson, Spearman,
and month-of-year de-meaned Pearson correlations. Results are descriptive and
must never be described as causal effects.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from statistics import mean
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
BUNDLE_ROOT = SCRIPT_DIR.parent
DEFAULT_WEATHER = BUNDLE_ROOT / '01_data' / 'weather' / 'weather_park_monthly.csv'
DEFAULT_OUTPUT_DIR = BUNDLE_ROOT / '01_data' / 'weather'

POLLUTANT_ALIASES = {
    'aqi': ['aqi', 'AQI'],
    'pm25': ['pm25', 'pm2_5', 'pm2.5', 'PM2.5', 'PM25'],
    'pm10': ['pm10', 'PM10'],
    'co': ['co', 'CO'],
    'no2': ['no2', 'NO2'],
    'so2': ['so2', 'SO2'],
    'o3': ['o3', 'O3', 'o3_8h', 'O3_8h'],
}
WEATHER_VARS = [
    'avg_temp_c',
    'relative_humidity_pct',
    'precipitation_mm',
    'sunshine_hours',
    'shortwave_radiation_mj_m2',
    'avg_wind_speed_kmh',
    'pressure_msl_hpa',
]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description='Compute descriptive air-weather correlations.')
    p.add_argument('--air-json', type=Path, required=True, help='Existing monthly_trends.json')
    p.add_argument('--weather-csv', type=Path, default=DEFAULT_WEATHER)
    p.add_argument('--output-dir', type=Path, default=DEFAULT_OUTPUT_DIR)
    return p.parse_args()


def as_float(value: Any) -> float | None:
    if value is None or value == '':
        return None
    try:
        x = float(value)
        return x if math.isfinite(x) else None
    except (TypeError, ValueError):
        return None


def first_value(row: dict[str, Any], aliases: list[str]) -> Any:
    for key in aliases:
        if key in row and row[key] not in (None, ''):
            return row[key]
    return None


def normalize_month(value: Any) -> str | None:
    if value is None:
        return None
    s = str(value).strip()
    if len(s) >= 7 and s[4] in '-/':
        return s[:7].replace('/', '-')
    if len(s) == 6 and s.isdigit():
        return s[:4] + '-' + s[4:]
    return None


def load_air(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(path)
    obj = json.loads(path.read_text(encoding='utf-8'))
    if isinstance(obj, list):
        rows = obj
    elif isinstance(obj, dict):
        rows = obj.get('records') or obj.get('data') or obj.get('items')
    else:
        rows = None
    if not isinstance(rows, list):
        raise ValueError('Air JSON must be a list or contain records/data/items list')
    result = {}
    for raw in rows:
        if not isinstance(raw, dict):
            continue
        month = normalize_month(raw.get('date') or raw.get('month'))
        if not month:
            continue
        # Explicitly exclude partial months when present.
        if raw.get('is_partial') is True or raw.get('partial_month') is True:
            continue
        clean = {'month': month}
        for canonical, aliases in POLLUTANT_ALIASES.items():
            clean[canonical] = as_float(first_value(raw, aliases))
        result[month] = clean
    if not result:
        raise ValueError('No valid monthly air-quality rows found')
    return result


def load_weather(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(
            f'{path} not found. Run fetch_sip_weather.py first.'
        )
    result = {}
    with path.open('r', encoding='utf-8-sig', newline='') as f:
        for raw in csv.DictReader(f):
            month = normalize_month(raw.get('month'))
            if not month:
                continue
            if str(raw.get('is_complete', '')).lower() not in ('true', '1', 'yes'):
                continue
            clean = {'month': month}
            for key in WEATHER_VARS:
                clean[key] = as_float(raw.get(key))
            result[month] = clean
    if not result:
        raise ValueError('No complete monthly weather rows found')
    return result


def pearson(xs: list[float], ys: list[float]) -> float | None:
    if len(xs) != len(ys) or len(xs) < 3:
        return None
    mx, my = mean(xs), mean(ys)
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    denx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    deny = math.sqrt(sum((y - my) ** 2 for y in ys))
    if denx == 0 or deny == 0:
        return None
    return num / (denx * deny)


def average_ranks(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i + 1
        while j < len(order) and values[order[j]] == values[order[i]]:
            j += 1
        avg_rank = (i + 1 + j) / 2.0
        for k in range(i, j):
            ranks[order[k]] = avg_rank
        i = j
    return ranks


def spearman(xs: list[float], ys: list[float]) -> float | None:
    if len(xs) < 3:
        return None
    return pearson(average_ranks(xs), average_ranks(ys))


def seasonal_demean(months: list[str], values: list[float]) -> list[float]:
    groups: dict[int, list[float]] = defaultdict(list)
    for month, value in zip(months, values):
        groups[int(month[5:7])].append(value)
    means = {m: mean(vals) for m, vals in groups.items()}
    return [value - means[int(month[5:7])] for month, value in zip(months, values)]


def strength_label(r: float | None) -> str:
    if r is None:
        return '不可计算'
    a = abs(r)
    if a >= 0.7:
        return '强相关'
    if a >= 0.4:
        return '中等相关'
    if a >= 0.2:
        return '弱相关'
    return '很弱相关'


def main() -> int:
    args = parse_args()
    air = load_air(args.air_json)
    weather = load_weather(args.weather_csv)
    months = sorted(set(air) & set(weather))
    if len(months) < 24:
        raise ValueError(f'Only {len(months)} overlapping complete months; at least 24 required')

    merged = []
    for month in months:
        row = {'month': month}
        row.update({k: air[month].get(k) for k in POLLUTANT_ALIASES})
        row.update({k: weather[month].get(k) for k in WEATHER_VARS})
        merged.append(row)

    correlations = []
    for pollutant in POLLUTANT_ALIASES:
        for weather_var in WEATHER_VARS:
            pairs = [
                (r['month'], r[pollutant], r[weather_var])
                for r in merged
                if r[pollutant] is not None and r[weather_var] is not None
            ]
            pair_months = [p[0] for p in pairs]
            xs = [p[1] for p in pairs]
            ys = [p[2] for p in pairs]
            pr = pearson(xs, ys)
            sr = spearman(xs, ys)
            sadj = pearson(seasonal_demean(pair_months, xs), seasonal_demean(pair_months, ys)) if len(xs) >= 24 else None
            correlations.append({
                'pollutant': pollutant,
                'weather_variable': weather_var,
                'n': len(xs),
                'pearson_r': None if pr is None else round(pr, 4),
                'spearman_rho': None if sr is None else round(sr, 4),
                'season_adjusted_pearson_r': None if sadj is None else round(sadj, 4),
                'strength_by_season_adjusted': strength_label(sadj),
                'interpretation': '描述性关联；相关不等于因果。',
            })

    ranked = sorted(
        [r for r in correlations if r['season_adjusted_pearson_r'] is not None],
        key=lambda r: abs(r['season_adjusted_pearson_r']),
        reverse=True,
    )
    priority = ranked[:12]

    args.output_dir.mkdir(parents=True, exist_ok=True)
    merged_path = args.output_dir / 'weather_air_merged.csv'
    with merged_path.open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(merged[0].keys()))
        writer.writeheader()
        writer.writerows(merged)

    output = {
        'metadata': {
            'generated_at': datetime.now().astimezone().isoformat(),
            'air_source_file': str(args.air_json),
            'weather_source_file': str(args.weather_csv),
            'overlap_months': len(months),
            'first_month': months[0],
            'last_month': months[-1],
            'methods': ['Pearson', 'Spearman', '按月份去季节均值后的Pearson'],
            'warning': '所有结果仅为描述性相关，相关不等于因果；不得写成气象因素造成污染变化。',
        },
        'priority_descriptive_associations': priority,
        'correlations': correlations,
        'interpretation_rules': {
            'absolute_r_ge_0_7': '强相关',
            'absolute_r_ge_0_4': '中等相关',
            'absolute_r_ge_0_2': '弱相关',
            'otherwise': '很弱相关',
        },
    }
    (args.output_dir / 'weather_air_correlations.json').write_text(
        json.dumps(output, ensure_ascii=False, indent=2), encoding='utf-8'
    )
    print(f'Done: {len(months)} overlapping months, {len(correlations)} correlations')
    print(args.output_dir / 'weather_air_correlations.json')
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f'ERROR: {type(exc).__name__}: {exc}', file=sys.stderr)
        raise SystemExit(2)
