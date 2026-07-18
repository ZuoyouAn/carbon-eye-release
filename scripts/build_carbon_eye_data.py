from __future__ import annotations

import csv
import hashlib
import json
import math
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any, Iterable


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = PROJECT_ROOT / "outputs" / "carbon_report"
DATA_DIR = PROJECT_ROOT / "backend" / "data" / "carbon_eye"
SOURCE_DIR = DATA_DIR / "sources"
WEATHER_DIR = DATA_DIR / "weather"

MONTHLY_RISK_CSV = SOURCE_DIR / "monthly_risk_index.csv"
MONTHLY_ANOMALIES_CSV = SOURCE_DIR / "monthly_anomalies_2023_2026.csv"
DAILY_RISK_CSV = SOURCE_DIR / "daily_cleaned_risk_sample.csv"

POLLUTANTS = ("no2", "so2", "co", "pm25", "o3")
TYPE_RENAMES = {
    "交通燃烧型": "含氮燃烧活动指示型",
    "工业燃烧型": "含硫工业燃烧可能关联型",
    "臭氧污染型": "臭氧光化学风险型",
    "颗粒物污染型": "颗粒物累积风险型",
    "臭氧复合污染型": "臭氧-多污染物复合风险型",
    "复合污染型": "多污染物复合风险型",
}


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(name: str, payload: Any) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    (DATA_DIR / name).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize_park_electricity_payload(park_payload: dict[str, Any]) -> dict[str, Any]:
    """Keep verified annual records separate from intentionally missing years."""
    limitations = park_payload.get("limitations", [])
    scope = park_payload.get("scope")
    available_records = []
    for source_record in park_payload.get("records", []):
        if source_record.get("total_electricity_100m_kwh") is None:
            continue
        record = dict(source_record)
        record["record_status"] = "available"
        record.setdefault("source_period", "全年")
        record.setdefault("missing_reason", None)
        record.setdefault("scope", scope)
        record.setdefault("limitations", limitations)
        available_records.append(record)

    available_records.sort(key=lambda item: item["year"])
    by_year = {int(item["year"]): item for item in available_records}
    missing_years = [int(year) for year in park_payload.get("missing_years", [])]
    year_slots = []
    for year in range(2019, 2026):
        if year in by_year:
            year_slots.append(by_year[year])
            continue
        year_slots.append(
            {
                "year": year,
                "period": "全年",
                "source_period": "全年",
                "record_status": "missing",
                "total_electricity_100m_kwh": None,
                "industrial_electricity_100m_kwh": None,
                "total_purchased_electricity_scope2_10k_tco2": None,
                "industrial_electricity_scope2_10k_tco2": None,
                "factor_reference_year": 2023,
                "factor_kgco2_per_kwh": 0.5827,
                "source_url": None,
                "data_quality": "未写入主数据",
                "missing_reason": "未找到同时包含全社会用电量和工业用电量、且口径明确为全年并可访问复核的官方公开记录。",
                "method": "缺失年份不插值、不倒推、不参与购电代理、强度、EAI、CEI 或 CDCI 计算。",
                "scope": scope,
                "limitations": limitations,
            }
        )

    park_payload["records"] = available_records
    park_payload["year_slots"] = year_slots
    park_payload["missing_years"] = missing_years
    park_payload["record_policy"] = {
        "main_chart_records": "仅 record_status=available 的官方全年成对用电记录",
        "missing_year_representation": "year_slots 返回显式 null，前端绘制断点，不以零值代替。",
    }
    return park_payload


def build_economic_intensity_payload(park_payload: dict[str, Any]) -> dict[str, Any]:
    records = []
    for item in park_payload.get("records", []):
        intensity = dict(item.get("economic_intensity", {}))
        intensity.update(
            {
                "record_status": "available",
                "source_period": item.get("source_period", "全年"),
                "source_url": item.get("source_url"),
                "data_quality": item.get("data_quality"),
                "factor_reference_year": item.get("factor_reference_year"),
                "method": item.get("method"),
                "scope": item.get("scope"),
                "limitations": item.get("limitations"),
                "missing_reason": None,
            }
        )
        records.append(intensity)
    return {
        "metric_name": "园区购电间接排放及经济强度代理",
        "records": records,
        "missing_years": park_payload.get("missing_years", []),
        "missing_year_policy": park_payload.get("missing_year_policy"),
        "scope": park_payload.get("scope"),
        "limitations": park_payload.get("limitations", []),
        "warning": "GDP 和规上工业总产值为宏观分母，仅用于趋势比较，不是企业或产品碳强度。",
    }


def as_float(value: Any, default: float | None = None) -> float | None:
    if value in (None, ""):
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def rounded(value: float | None, digits: int = 3) -> float | None:
    return None if value is None else round(value, digits)


def risk_level(score: float | None) -> str:
    if score is None:
        return "未计算"
    if score < 40:
        return "低风险"
    if score < 70:
        return "中风险"
    return "高风险"


def normalize_type(value: str | None) -> str:
    return TYPE_RENAMES.get(value or "", value or "多污染物复合风险型")


def governance_advice(risk_type: str) -> str:
    if "臭氧" in risk_type:
        return "在高温或强辐射条件下，建议开展VOCs与NOx协同控制和涉VOCs工序错峰复核；结论为治理优先级建议，不构成源解析。"
    if "颗粒物" in risk_type:
        return "建议优先复核颗粒物、施工扬尘和燃烧活动管理，并结合低风速、少降水等描述性气象条件安排现场巡查。"
    if "含氮" in risk_type:
        return "建议优先排查含氮燃烧活动和交通活动，不能仅依据该指标确定具体排放源。"
    if "含硫" in risk_type:
        return "建议优先核查含硫燃料、酸雾收集与治理设施；该建议不替代现场审计或企业责任认定。"
    return "建议开展多污染物协同复核，并结合园区现场数据、气象和排放清单确定治理顺序。"


def contribution_details(row: dict[str, str]) -> tuple[str, dict[str, float]]:
    scores = {
        "NO2": as_float(row.get("no2_contrib"), 0.0) or 0.0,
        "SO2": as_float(row.get("so2_contrib"), 0.0) or 0.0,
        "CO": as_float(row.get("co_contrib"), 0.0) or 0.0,
        "PM2.5": as_float(row.get("pm25_contrib"), 0.0) or 0.0,
        "O3": as_float(row.get("o3_contrib"), 0.0) or 0.0,
    }
    return max(scores, key=scores.get), {key: round(value, 2) for key, value in scores.items()}


def load_monthly_trends() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with MONTHLY_RISK_CSV.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            date = (row.get("ym") or row["date"][:7]).strip()
            partial = date == "2026-07"
            legacy_score = as_float(row.get("risk_score"), 0.0) or 0.0
            main_contributor, contribution_scores = contribution_details(row)
            main_type = normalize_type(row.get("main_risk_type"))
            record = {
                "date": date,
                "aqi": as_float(row.get("aqi")),
                "pm25": as_float(row.get("pm25")),
                "pm10": as_float(row.get("pm10")),
                "co": as_float(row.get("co")),
                "no2": as_float(row.get("no2")),
                "so2": as_float(row.get("so2")),
                "o3": as_float(row.get("o3")),
                "quality_level": row.get("quality_level"),
                "season": row.get("season"),
                "absolute_risk_score": round(legacy_score, 1),
                "absolute_risk_level": risk_level(legacy_score),
                "risk_score": round(legacy_score, 1),
                "risk_level": risk_level(legacy_score),
                "relative_anomaly": False,
                "anomaly_items": [],
                "historical_threshold_rule": "2013-2022同月历史90%分位数",
                "main_contributor": main_contributor,
                "contribution_scores": contribution_scores,
                "main_risk_type": main_type,
                "governance_advice": governance_advice(main_type),
                "time_scale": "月度",
                "data_scope": "苏州市级空气质量背景，不代表园区内部连续监测",
                "is_partial": partial,
                "observation_days": None if partial else None,
                "excluded_from_annual_statistics": partial,
            }
            records.append(record)
    records.sort(key=lambda item: item["date"])
    if len(records) != 152:
        raise ValueError(f"Expected 152 monthly records, found {len(records)}")
    return records


def load_anomaly_index() -> dict[str, dict[str, Any]]:
    items: dict[str, dict[str, Any]] = {}
    with MONTHLY_ANOMALIES_CSV.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            date = row["date"][:7]
            raw_items = row.get("exceeded_items", "")
            items[date] = {
                "anomaly_items": [value.strip() for value in raw_items.split("、") if value.strip()],
                "exceeded_count": int(float(row.get("exceeded_count") or 0)),
                "max_ratio": as_float(row.get("max_ratio")),
            }
    return items


def apply_anomalies(records: list[dict[str, Any]], anomaly_index: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    warnings: list[dict[str, Any]] = []
    for record in records:
        anomaly = anomaly_index.get(record["date"])
        if anomaly and not record["is_partial"]:
            record["relative_anomaly"] = True
            record["anomaly_items"] = anomaly["anomaly_items"]
            warnings.append(
                {
                    "date": record["date"],
                    "relative_anomaly": True,
                    "anomaly_items": anomaly["anomaly_items"],
                    "exceeded_items": "；".join(anomaly["anomaly_items"]),
                    "exceeded_count": anomaly["exceeded_count"],
                    "max_ratio": anomaly["max_ratio"],
                    "absolute_risk_score": record["absolute_risk_score"],
                    "absolute_risk_level": record["absolute_risk_level"],
                    "risk_score": record["absolute_risk_score"],
                    "risk_level": record["absolute_risk_level"],
                    "main_contributor": record["main_contributor"],
                    "main_risk_type": record["main_risk_type"],
                    "governance_advice": record["governance_advice"],
                    "time_scale": "月度",
                    "data_scope": "苏州市级空气质量背景",
                }
            )
    warnings.sort(key=lambda item: (-item["exceeded_count"], -item["max_ratio"], item["date"]))
    if len(warnings) != 13:
        raise ValueError(f"Expected 13 anomaly months, found {len(warnings)}")
    return warnings


def load_daily_cases() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with DAILY_RISK_CSV.open("r", encoding="utf-8-sig", newline="") as handle:
        source = list(csv.DictReader(handle))
    source.sort(key=lambda row: as_float(row.get("risk_score"), 0.0) or 0.0, reverse=True)
    for row in source[:10]:
        risk_type = normalize_type(row.get("main_risk_type"))
        main_contributor, contribution_scores = contribution_details(row)
        score = as_float(row.get("risk_score"), 0.0) or 0.0
        rows.append(
            {
                "date": row["date"],
                "aqi": as_float(row.get("aqi")),
                "quality_level": row.get("quality_level"),
                "pm25": as_float(row.get("pm25")),
                "pm10": as_float(row.get("pm10")),
                "co": as_float(row.get("co")),
                "no2": as_float(row.get("no2")),
                "so2": as_float(row.get("so2")),
                "o3_8h": as_float(row.get("o3_8h")),
                "absolute_risk_score": round(score, 1),
                "absolute_risk_level": risk_level(score),
                "risk_score": round(score, 1),
                "risk_level": risk_level(score),
                "main_contributor": main_contributor,
                "contribution_scores": contribution_scores,
                "main_risk_type": risk_type,
                "advice": governance_advice(risk_type),
                "time_scale": "日级历史案例",
                "data_range": "2013-12-02 至 2015-07-31",
                "data_correction": "20个日表月份中18个月完成CO/NO2/SO2字段纠偏；月均平均相对误差约0.0182。",
            }
        )
    return rows


def load_weather() -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    path = WEATHER_DIR / "weather_park_monthly.json"
    if not path.exists():
        return None, []
    payload = read_json(path)
    records = payload.get("records", []) if isinstance(payload, dict) else []
    return payload.get("metadata", {}) if isinstance(payload, dict) else {}, records


def weather_2024(weather_records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    for row in weather_records:
        if not str(row.get("month", "")).startswith("2024-"):
            continue
        result.append(
            {
                "month": row["month"],
                "avg_temp": row.get("avg_temp_c"),
                "precipitation": row.get("precipitation_mm"),
                "sunshine_hours": row.get("sunshine_hours"),
                "relative_humidity": row.get("relative_humidity_pct"),
                "avg_wind_speed": row.get("avg_wind_speed_kmh"),
                "unit_note": "温度(°C)、降水(mm)、日照(h)、湿度(%)、风速(km/h)",
                "source": "Open-Meteo Historical Weather API / ERA5；园区六点位空间平均",
                "time_scale": "月度",
                "non_causal_warning": "用于描述性解释，不代表气象因素造成污染变化。",
            }
        )
    return result


def minmax(values: Iterable[float]) -> list[float]:
    source = list(values)
    if not source:
        return []
    low, high = min(source), max(source)
    if math.isclose(low, high):
        return [50.0 for _ in source]
    return [(value - low) / (high - low) * 100 for value in source]


def load_electricity_yoy() -> dict[int, float]:
    path = SOURCE_DIR / "sip_electricity_official.csv"
    result: dict[int, float] = {}
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            year = int(row["year"])
            value = as_float(row.get("total_yoy_pct"))
            if value is not None:
                result[year] = value
    return result


def build_annual_dimensions(park_payload: dict[str, Any]) -> list[dict[str, Any]]:
    records = sorted(
        (
            item
            for item in park_payload.get("records", [])
            if item.get("record_status", "available") == "available"
        ),
        key=lambda item: item["year"],
    )
    yoy_by_year = load_electricity_yoy()
    electricity = [float(item["total_electricity_100m_kwh"]) for item in records]
    yoy = [float(yoy_by_year.get(int(item["year"]), 0.0)) for item in records]
    intensity = [float(item["economic_intensity"]["total_scope2_tco2_per_10k_gdp"]) for item in records]
    electricity_scores = minmax(electricity)
    yoy_scores = minmax(yoy)
    intensity_scores = minmax(intensity)
    dimensions = []
    for item, electricity_score, yoy_score, intensity_score in zip(records, electricity_scores, yoy_scores, intensity_scores):
        eai = 0.7 * electricity_score + 0.3 * yoy_score
        dimensions.append(
            {
                "year": item["year"],
                "pri": None,
                "eai": round(eai, 1),
                "cei": round(intensity_score, 1),
                "total_electricity_100m_kwh": item["total_electricity_100m_kwh"],
                "total_electricity_yoy_pct": yoy_by_year.get(int(item["year"])),
                "scope2_proxy_tco2_per_10k_gdp": item["economic_intensity"]["total_scope2_tco2_per_10k_gdp"],
                "time_scale": "年度",
                "method": "EAI=0.7×全社会用电量相对位置+0.3×用电同比相对位置；CEI=每万元GDP购电间接排放代理强度相对位置。",
                "scope": "园区购电间接排放位置法代理估算；不是园区总碳排放或正式碳核算。",
                "source": item.get("source_url"),
            }
        )
    return dimensions


def spearman(xs: list[float], ys: list[float]) -> float | None:
    if len(xs) != len(ys) or len(xs) < 3:
        return None

    def ranks(values: list[float]) -> list[float]:
        order = sorted(range(len(values)), key=lambda index: values[index])
        result = [0.0] * len(values)
        index = 0
        while index < len(order):
            end = index + 1
            while end < len(order) and values[order[end]] == values[order[index]]:
                end += 1
            rank = (index + 1 + end) / 2
            for position in range(index, end):
                result[order[position]] = rank
            index = end
        return result

    rx, ry = ranks(xs), ranks(ys)
    mx, my = mean(rx), mean(ry)
    numerator = sum((x - mx) * (y - my) for x, y in zip(rx, ry))
    denominator = math.sqrt(sum((x - mx) ** 2 for x in rx) * sum((y - my) ** 2 for y in ry))
    return None if denominator == 0 else numerator / denominator


def build_cdci(monthly: list[dict[str, Any]], dimensions: list[dict[str, Any]]) -> tuple[dict[str, Any], dict[str, Any]]:
    dimension_by_year = {int(item["year"]): item for item in dimensions}
    weights = {"pri": 0.5, "eai": 0.2, "cei": 0.3}
    records: list[dict[str, Any]] = []
    for row in monthly:
        year = int(row["date"][:4])
        dimension = dimension_by_year.get(year)
        if row["is_partial"] or dimension is None:
            continue
        pri = float(row["absolute_risk_score"])
        score = weights["pri"] * pri + weights["eai"] * dimension["eai"] + weights["cei"] * dimension["cei"]
        records.append(
            {
                "date": row["date"],
                "year": year,
                "pri": round(pri, 1),
                "eai": dimension["eai"],
                "cei": dimension["cei"],
                "cdci": round(score, 1),
                "cdci_level": risk_level(score),
                "relative_anomaly": row["relative_anomaly"],
                "main_contributor": row["main_contributor"],
                "main_risk_type": row["main_risk_type"],
                "time_frequency_note": "PRI为月度，EAI和CEI为年度背景；属于混合时间频率实验性展示。",
                "scope": "减污降碳协同态势指数（实验性原型），不用于实时碳排放判断。",
            }
        )

    scenarios = {
        "baseline_0.5_0.2_0.3": {"pri": 0.5, "eai": 0.2, "cei": 0.3},
        "alternative_0.4_0.3_0.3": {"pri": 0.4, "eai": 0.3, "cei": 0.3},
        "equal_1_3": {"pri": 1 / 3, "eai": 1 / 3, "cei": 1 / 3},
    }
    scenario_scores: dict[str, list[dict[str, Any]]] = {}
    for name, scheme in scenarios.items():
        values = []
        for record in records:
            score = scheme["pri"] * record["pri"] + scheme["eai"] * record["eai"] + scheme["cei"] * record["cei"]
            values.append({"date": record["date"], "score": round(score, 4), "level": risk_level(score)})
        scenario_scores[name] = values

    baseline = scenario_scores["baseline_0.5_0.2_0.3"]
    top_count = max(1, math.ceil(len(baseline) * 0.2))
    baseline_high = {item["date"] for item in sorted(baseline, key=lambda item: item["score"], reverse=True)[:top_count]}
    comparisons = []
    for name, values in scenario_scores.items():
        candidate_high = {item["date"] for item in sorted(values, key=lambda item: item["score"], reverse=True)[:top_count]}
        denominator = len(baseline_high | candidate_high)
        overlap = len(baseline_high & candidate_high) / denominator if denominator else None
        changed = sum(a["level"] != b["level"] for a, b in zip(baseline, values)) / len(baseline) if baseline else None
        ranking = spearman([item["score"] for item in baseline], [item["score"] for item in values])
        comparisons.append(
            {
                "scenario": name,
                "weights": scenarios[name],
                "rank_spearman": rounded(ranking, 4),
                "high_risk_month_overlap_rate": rounded(overlap, 4),
                "level_change_rate": rounded(changed, 4),
                "high_risk_definition": "各方案得分前20%的月份",
            }
        )

    cdci = {
        "name": "减污降碳协同态势指数（实验性原型）",
        "formula": "CDCI = 0.5×PRI + 0.2×EAI + 0.3×CEI",
        "weights": weights,
        "annual_dimensions": dimensions,
        "records": records,
        "latest": records[-1] if records else None,
        "limitations": [
            "PRI为月度城市背景污染压力；EAI和CEI为园区年度背景，存在混合时间频率。",
            "购电间接排放代理与用电量相关，默认优先展示三维态势，CDCI只作为实验性选项。",
            "仅对2019、2023、2024、2025年有年度能碳数据的月份计算；2020-2022保持缺失。",
            "不使用机器学习拟合权重，不报告统计显著性。",
        ],
    }
    sensitivity = {
        "name": "CDCI权重敏感性分析",
        "sample_size": len(records),
        "comparison_note": "排名相关和等级变化仅用于方案稳健性对比，不构成统计显著性检验。",
        "scenarios": scenario_scores,
        "comparisons": comparisons,
    }
    return cdci, sensitivity


def build_governance_explanation(monthly: list[dict[str, Any]]) -> dict[str, Any]:
    latest = next((item for item in reversed(monthly) if not item["is_partial"]), None)
    return {
        "name": "规则驱动的治理建议解释",
        "method": "专家规则模板；不调用大模型，不替代现场审计。",
        "latest_context": {
            "date": latest["date"] if latest else None,
            "trigger": [latest["main_contributor"], latest["main_risk_type"]] if latest else [],
            "advice": latest["governance_advice"] if latest else None,
            "data_gap": "缺少企业级用电、燃料、VOCs、排放清单和现场工况。",
        },
        "rules": [
            {
                "trigger_basis": "O3较高且气温、日照或短波辐射处于相对较高条件",
                "applicable_industries": "涉VOCs相关产业场景",
                "action": "开展VOCs与NOx协同控制和涉VOCs工序错峰复核。",
                "data_gap": "无企业VOCs排放和工序时段数据。",
            },
            {
                "trigger_basis": "PM2.5较高且风速较低或降水较少的描述性条件",
                "applicable_industries": "建设、物流、制造及园区公共管理场景",
                "action": "复核颗粒物、施工扬尘和燃烧活动管理。",
                "data_gap": "无实时扬尘与燃料燃烧清单。",
            },
            {
                "trigger_basis": "NO2贡献较高",
                "applicable_industries": "含氮燃烧和交通活动相关场景",
                "action": "优先复核含氮燃烧和交通活动，避免直接定性为单一来源。",
                "data_gap": "无源解析和交通流量数据。",
            },
            {
                "trigger_basis": "SO2或硫酸雾特征较高",
                "applicable_industries": "可能涉及含硫燃料或酸雾治理的场景",
                "action": "核查含硫燃料、酸雾收集与治理设施。",
                "data_gap": "无企业设施运行台账。",
            },
            {
                "trigger_basis": "购电强度代理较高",
                "applicable_industries": "高电力使用产业和园区公共设施",
                "action": "评估绿电、冷站、空压、洁净室和电机系统优化。",
                "data_gap": "无分行业和企业级负荷曲线。",
            },
        ],
        "boundary": "建议按触发依据匹配治理方向，不识别具体污染企业，也不替代现场审计。",
    }


def build_methodology() -> dict[str, Any]:
    return {
        "risk_index_name": "污染压力指数 PRI（原型）",
        "pri_formula": "PRI = 0.25×NO2标准化值 + 0.20×SO2标准化值 + 0.20×CO标准化值 + 0.20×PM2.5标准化值 + 0.15×O3标准化值",
        "pri_role": "PRI用于月度污染压力排序和治理解释，不是官方标准。",
        "three_dimension_situation": {
            "pri": "月度污染压力指数，使用原型污染物权重。",
            "eai": "年度能源活动指数，基于全社会用电量与同比的相对位置。",
            "cei": "年度购电间接排放强度指数，基于tCO2/万元GDP代理强度的相对位置。",
        },
        "experimental_cdci": "CDCI = 0.5×PRI + 0.2×EAI + 0.3×CEI；仅在年度能碳数据存在时计算，标注为混合时间频率实验性原型。",
        "park_electricity_title": "苏州工业园区购电间接排放估算（位置法代理值）",
        "park_electricity_boundary": [
            "不含直接燃烧。",
            "不含外购热力。",
            "不含工业过程。",
            "不含交通和废弃物。",
            "未进行绿电绿证市场法调整。",
            "2019、2024、2025采用2023江苏0.5827 kgCO2/kWh统一因子横向比较情景，不是对应年度正式清单。",
        ],
        "anomaly_rule": "相对异常使用2013-2022同月历史90%分位数；绝对风险使用PRI的0-40低、40-70中、70-100高等级，两者独立呈现。",
        "weather_rule": "所有气象-污染结果为Pearson、Spearman和去季节Pearson的描述性相关，相关不等于因果。",
        "data_boundaries": [
            "月度空气质量为苏州市级背景，不能表述为园区内部连续监测。",
            "园区六点位特征因子为2026年6月、7天官方短期监测快照，不代表全年均值或实时序列。",
            "苏州市CO2为城市级年度背景；园区购电代理不是园区总碳排放或正式碳核算。",
            "日级案例仅覆盖2013-12-02至2015-07-31。",
        ],
    }


def build_metadata(weather_meta: dict[str, Any] | None, monthly: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "system_version": "2.0.0",
        "build_time": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "air_quality_range": f"{monthly[0]['date']} 至 {monthly[-1]['date']}",
        "weather_range": None if not weather_meta else f"{weather_meta.get('start_date')} 至 {weather_meta.get('end_date')}",
        "monthly_air_scale": "苏州市级空气质量背景",
        "park_snapshot_scale": "苏州工业园区六点位官方短期监测快照",
        "carbon_scope": "园区购电间接排放位置法代理估算",
        "aqi_standard_note": "跨2026年3月的AQI序列须注意HJ 633标准版本变化；本系统按原始数据源口径展示，不将跨期差异解释为单一环境变化。",
        "partial_month": {"date": "2026-07", "is_partial": True, "excluded_from_annual_statistics": True, "observation_days": None},
    }


def build_data_quality(monthly: list[dict[str, Any]], daily_cases: list[dict[str, Any]], weather_records: list[dict[str, Any]], park: dict[str, Any], snapshot: dict[str, Any]) -> dict[str, Any]:
    weather_validation_path = WEATHER_DIR / "weather_validation_summary.json"
    weather_validation = read_json(weather_validation_path) if weather_validation_path.exists() else None
    return {
        "monthly_records": len(monthly),
        "monthly_range": [monthly[0]["date"], monthly[-1]["date"]],
        "partial_month": next(item for item in monthly if item["is_partial"]),
        "daily_source_records": 602,
        "daily_case_range": "2013-12-02 至 2015-07-31",
        "daily_field_correction": {"months_checked": 20, "months_corrected": 18, "mean_relative_error": 0.0182},
        "weather_months": len(weather_records),
        "weather_validation": weather_validation,
        "official_electricity_records": len(park.get("records", [])),
        "electricity_missing_years": park.get("missing_years", []),
        "monitoring_sites": snapshot.get("site_count"),
        "snapshot_records": len(snapshot.get("records", [])),
        "snapshot_monitoring_days": snapshot.get("monitoring_days"),
        "data_boundary": "质量检查描述数据覆盖和处理状态，不将代理估算扩展为正式核算。",
    }


def build_provenance_registry(source_registry: list[dict[str, Any]]) -> dict[str, Any]:
    source_context = {
        "S01": {
            "temporal_coverage": "monthly 2013-12 to 2026-07; daily 2013-12-02 to 2015-07-31",
            "spatial_scale": "Suzhou city background",
            "field_units": "AQI; PM2.5, PM10, CO, NO2, SO2, O3; see data_dictionary.md",
            "license_or_terms": "unknown; original platform, download date and reuse terms require confirmation",
            "provenance_status": "pending_original_source_confirmation",
            "processing_script": "scripts/build_carbon_report.py; scripts/build_carbon_eye_data.py",
        },
        "S02": {"temporal_coverage": "2019 annual", "spatial_scale": "Suzhou Industrial Park", "field_units": "electricity in 100m kWh; GDP/output in 100m CNY", "license_or_terms": "official public PDF", "provenance_status": "verified", "processing_script": "scripts/build_carbon_eye_data.py"},
        "S03": {"temporal_coverage": "2023 annual", "spatial_scale": "Suzhou Industrial Park", "field_units": "electricity in 100m kWh; GDP/output in 100m CNY", "license_or_terms": "official public page", "provenance_status": "verified", "processing_script": "scripts/build_carbon_eye_data.py"},
        "S04": {"temporal_coverage": "2024 annual", "spatial_scale": "Suzhou Industrial Park", "field_units": "electricity in 100m kWh; GDP/output in 100m CNY", "license_or_terms": "official public page", "provenance_status": "verified", "processing_script": "scripts/build_carbon_eye_data.py"},
        "S05": {"temporal_coverage": "2025 annual", "spatial_scale": "Suzhou Industrial Park", "field_units": "electricity in 100m kWh; GDP/output in 100m CNY", "license_or_terms": "official public page", "provenance_status": "verified", "processing_script": "scripts/build_carbon_eye_data.py"},
        "S06": {"temporal_coverage": "factor reference year 2023", "spatial_scale": "Jiangsu Province", "field_units": "kgCO2/kWh", "license_or_terms": "official public document", "provenance_status": "verified", "processing_script": "scripts/build_carbon_eye_data.py"},
        "S07": {"temporal_coverage": "2026-06, 7 days", "spatial_scale": "six Suzhou Industrial Park sites", "field_units": "14 characteristic factors; see snapshot source data", "license_or_terms": "official public PDF", "provenance_status": "verified", "processing_script": "scripts/import_carbon_eye_bundle.py"},
        "S08": {"temporal_coverage": "2013-12 to 2026-06, complete months only", "spatial_scale": "six-site spatial mean", "field_units": "temperature, precipitation, sunshine, humidity, wind and radiation; see weather_field_schema.csv", "license_or_terms": "Open-Meteo Historical API / ERA5 attribution required", "provenance_status": "validated", "processing_script": "scripts/fetch_sip_weather.py; scripts/analyze_weather_air.py"},
        "S09": {"temporal_coverage": "policy-era classification", "spatial_scale": "Suzhou Industrial Park", "field_units": "six industry categories", "license_or_terms": "official public page", "provenance_status": "verified", "processing_script": "scripts/import_carbon_eye_bundle.py"},
        "S10": {"temporal_coverage": "policy document", "spatial_scale": "Suzhou Industrial Park", "field_units": "policy text", "license_or_terms": "official public page", "provenance_status": "verified", "processing_script": "documentation only"},
        "S11": {"temporal_coverage": "annual city background through 2019", "spatial_scale": "Suzhou city", "field_units": "CO2 inventory", "license_or_terms": "see CEADs access terms", "provenance_status": "reused_project_data", "processing_script": "scripts/build_carbon_eye_data.py"},
        "S12": {"temporal_coverage": "current station status only", "spatial_scale": "Suzhou Industrial Park station", "field_units": "AQI and pollutant concentrations", "license_or_terms": "Token and attribution required; no historical redistribution", "provenance_status": "optional_not_configured", "processing_script": "backend/main.py"},
    }
    tracked_paths = [
        "sources/monthly_risk_index.csv", "sources/monthly_anomalies_2023_2026.csv", "sources/daily_cleaned_risk_sample.csv",
        "sources/sip_electricity_official.csv", "sources/sip_electricity_missing_years_template.csv", "sources/jiangsu_electricity_emission_factors.csv",
        "sources/sip_economic_activity_official.csv", "sources/sip_characteristic_air_snapshot.csv", "sources/industry_profile.csv",
        "monthly_trends.json", "daily_cases.json", "park_electricity_emissions.json", "sip_economic_carbon_intensity.json",
        "park_environment_snapshot.json", "carbon_emissions.json", "cdci.json", "weather/weather_park_monthly.csv", "weather/weather_validation_summary.json",
    ]
    file_manifest = []
    for relative_path in tracked_paths:
        path = DATA_DIR / relative_path
        if path.exists():
            file_manifest.append(
                {
                    "path": relative_path.replace("\\", "/"),
                    "sha256": sha256_file(path),
                    "bytes": path.stat().st_size,
                    "generated_or_checked_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
                }
            )
    sources = []
    for source in source_registry:
        item = dict(source)
        item.update(source_context.get(item.get("source_id"), {}))
        item["download_date"] = "not recorded in the historic bundle" if item.get("source_id") == "S01" else "not recorded; source page retained for audit"
        sources.append(item)
    return {
        "schema_version": "1.0.0",
        "audit_date": datetime.now(timezone.utc).astimezone().date().isoformat(),
        "purpose": "Trace source, scale, processing route and SHA-256 checksums for Carbon Eye competition evidence.",
        "sources": sources,
        "file_manifest": file_manifest,
        "known_gaps": {
            "electricity_2020_2022": "No verified official annual paired total and industrial electricity values; kept as explicit missing years.",
            "air_quality_original_platform": "Original platform, download date and licence for S01 remain pending confirmation.",
        },
    }


def main() -> None:
    for path in (MONTHLY_RISK_CSV, MONTHLY_ANOMALIES_CSV, DAILY_RISK_CSV):
        if not path.exists():
            raise FileNotFoundError(path)
    for name in ("park_electricity_emissions.json", "park_environment_snapshot.json", "industry_profile.json", "source_registry.json", "carbon_emissions.json"):
        if not (DATA_DIR / name).exists():
            raise FileNotFoundError(f"Missing required data file: {DATA_DIR / name}")

    monthly = load_monthly_trends()
    warnings = apply_anomalies(monthly, load_anomaly_index())
    daily_cases = load_daily_cases()
    weather_meta, weather_records = load_weather()
    weather_current_year = weather_2024(weather_records)
    park = normalize_park_electricity_payload(
        read_json(DATA_DIR / "park_electricity_emissions.json")
    )
    snapshot = read_json(DATA_DIR / "park_environment_snapshot.json")
    source_registry = read_json(DATA_DIR / "source_registry.json")
    annual_dimensions = build_annual_dimensions(park)
    cdci, sensitivity = build_cdci(monthly, annual_dimensions)
    governance = build_governance_explanation(monthly)
    methodology = build_methodology()
    metadata = build_metadata(weather_meta, monthly)
    data_quality = build_data_quality(monthly, daily_cases, weather_records, park, snapshot)
    data_quality["electricity_year_slots"] = len(park.get("year_slots", []))
    city_carbon = read_json(DATA_DIR / "carbon_emissions.json")
    latest_complete = next(item for item in reversed(monthly) if not item["is_partial"])
    overview = {
        "projectName": "园区碳眼",
        "positioning": "基于城市背景、园区短期监测、长期气象和购电间接排放代理的减污降碳协同预警原型。",
        "dataRanges": {
            "monthlyAirQuality": metadata["air_quality_range"],
            "weather": metadata["weather_range"],
            "dailyCases": "2013-12-02 至 2015-07-31",
            "cityCarbonBackground": "苏州市年度CO2背景",
            "parkElectricity": "2019、2023、2024、2025；2020-2022保留缺口",
            "parkSnapshot": "2026年6月、6点位、7天、14项特征因子",
        },
        "latestMonthly": latest_complete,
        "latestParkElectricityProxy": park.get("records", [])[-1] if park.get("records") else None,
        "threeDimensionSituation": {"latestAnnual": annual_dimensions[-1] if annual_dimensions else None, "latestMonthlyPRI": latest_complete["absolute_risk_score"]},
        "riskSummary": {"warningCount": len(warnings), "highestMonthlyRisk": max(monthly, key=lambda item: item["absolute_risk_score"]), "latestExperimentalCdci": cdci.get("latest")},
        "dataVersion": metadata,
        "limitations": methodology["data_boundaries"],
    }
    validation = {
        "monthly_trends_count": len(monthly),
        "weather_long_term_count": len(weather_records),
        "weather_2024_count": len(weather_current_year),
        "city_carbon_count": len(city_carbon),
        "warnings_count": len(warnings),
        "daily_cases_count": len(daily_cases),
        "park_electricity_record_count": len(park.get("records", [])),
        "park_electricity_year_slots": len(park.get("year_slots", [])),
        "cdci_record_count": len(cdci.get("records", [])),
        "checks": {
            "monthly_records_expected_152": len(monthly) == 152,
            "weather_coverage_at_least_145_months": len(weather_records) >= 145,
            "electricity_gap_not_filled": park.get("missing_years") == [2020, 2021, 2022],
            "snapshot_expected_84_records": len(snapshot.get("records", [])) == 84,
            "partial_month_excluded": bool(monthly[-1]["is_partial"] and monthly[-1]["excluded_from_annual_statistics"]),
        },
    }

    write_json("overview.json", overview)
    write_json("monthly_trends.json", monthly)
    write_json("weather_2024.json", weather_current_year)
    write_json("warnings.json", warnings)
    write_json("daily_cases.json", daily_cases)
    write_json("methodology.json", methodology)
    write_json("cdci.json", cdci)
    write_json("cdci_sensitivity.json", sensitivity)
    write_json("governance_explanation.json", governance)
    write_json("metadata.json", metadata)
    write_json("data_quality.json", data_quality)
    write_json("validation_summary.json", validation)
    write_json("park_electricity_emissions.json", park)
    write_json("sip_economic_carbon_intensity.json", build_economic_intensity_payload(park))
    write_json("data_provenance_registry.json", build_provenance_registry(source_registry))
    print(f"Carbon Eye data rebuilt in {DATA_DIR}")
    print(json.dumps(validation, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
