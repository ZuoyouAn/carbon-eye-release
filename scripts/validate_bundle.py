#!/usr/bin/env python3
"""Validate the Carbon Eye release data without changing source values."""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime
from pathlib import Path


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def check(condition: bool, message: str, passed: list[str], errors: list[str]) -> None:
    (passed if condition else errors).append(message)


def markdown_report(report: dict) -> str:
    status = "通过" if report["status"] == "pass" else "失败"
    lines = [
        "# Carbon Eye 数据质量报告",
        "",
        f"- 状态：{status}",
        f"- 生成时间：{report['generated_at']}",
        f"- 通过项：{len(report['passed'])}",
        f"- 警告项：{len(report['warnings'])}",
        f"- 错误项：{len(report['errors'])}",
        "",
        "## 通过项",
    ]
    lines.extend(f"- {item}" for item in report["passed"])
    if report["warnings"]:
        lines.extend(["", "## 警告项"])
        lines.extend(f"- {item}" for item in report["warnings"])
    if report["errors"]:
        lines.extend(["", "## 错误项"])
        lines.extend(f"- {item}" for item in report["errors"])
    lines.extend([
        "",
        "## 口径提醒",
        "- 月度空气质量为苏州市级背景，不能等同于园区内部连续监测。",
        "- 园区六点位数据是 2026 年 6 月、7 天官方短期监测快照。",
        "- 用电结果仅为园区购电间接排放位置法代理估算；2020-2022 保持缺口。",
        "- 气象结果仅用于描述性相关，相关不等于因果。",
    ])
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Carbon Eye project data")
    parser.add_argument("--project-root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()

    root = args.project_root.resolve()
    data = root / "backend" / "data" / "carbon_eye"
    sources = data / "sources"
    weather_dir = data / "weather"
    passed: list[str] = []
    errors: list[str] = []
    warnings: list[str] = []

    required = [
        sources / "sip_electricity_official.csv",
        sources / "jiangsu_electricity_emission_factors.csv",
        sources / "sip_characteristic_air_snapshot.csv",
        data / "monthly_trends.json",
        data / "park_electricity_emissions.json",
        data / "park_environment_snapshot.json",
        data / "industry_profile.json",
        data / "cdci.json",
        data / "cdci_sensitivity.json",
        weather_dir / "weather_park_monthly.csv",
        weather_dir / "weather_air_correlations.json",
    ]
    for path in required:
        check(path.exists(), f"文件存在：{path.relative_to(root).as_posix()}", passed, errors)
    if errors:
        report = {"generated_at": datetime.now().astimezone().isoformat(), "status": "fail", "passed": passed, "warnings": warnings, "errors": errors}
        (root / "DATA_QUALITY_REPORT.md").write_text(markdown_report(report), encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 2

    electricity = read_csv(sources / "sip_electricity_official.csv")
    snapshot_csv = read_csv(sources / "sip_characteristic_air_snapshot.csv")
    sites = read_csv(sources / "sip_monitoring_sites.csv")
    park_electricity = read_json(data / "park_electricity_emissions.json")
    snapshot = read_json(data / "park_environment_snapshot.json")
    industry = read_json(data / "industry_profile.json")
    monthly = read_json(data / "monthly_trends.json")
    weather = read_csv(weather_dir / "weather_park_monthly.csv")
    correlations = read_json(weather_dir / "weather_air_correlations.json")
    cdci = read_json(data / "cdci.json")

    years = [int(row["year"]) for row in electricity]
    check(len(electricity) == 4 and years == [2019, 2023, 2024, 2025], "官方园区用电记录为4条（2019、2023、2024、2025）", passed, errors)
    check(not ({2020, 2021, 2022} & set(years)), "2020-2022 年用电缺口未被填补", passed, errors)
    check(len(sites) == 6, "园区官方监测点位为6个", passed, errors)
    check(len(snapshot_csv) == 84 and len(snapshot.get("records", [])) == 84, "特征因子记录为84条（14项×6点）", passed, errors)
    check(len({item["pollutant"] for item in snapshot_csv}) == 14, "特征因子种类为14项", passed, errors)
    check(len(industry.get("profiles", [])) == 6, "产业画像为6类", passed, errors)

    for item in park_electricity.get("records", []):
        expected = float(item["total_electricity_100m_kwh"]) * 10 * float(item["factor_kgco2_per_kwh"])
        actual = float(item["total_purchased_electricity_scope2_10k_tco2"])
        check(abs(expected - actual) <= 0.0011, f"{item['year']} 全社会购电代理公式复算一致", passed, errors)

    check(len(monthly) == 152, "月度空气质量记录为152条", passed, errors)
    partial = next((item for item in monthly if item.get("date") == "2026-07"), None)
    check(bool(partial and partial.get("is_partial") and partial.get("excluded_from_annual_statistics")), "2026-07 标识为部分月并排除年度统计", passed, errors)
    check(len(weather) >= 145, "长期气象月度记录不少于145条", passed, errors)
    incomplete = [item["month"] for item in weather if str(item.get("is_complete", "")).lower() not in {"true", "1", "yes"}]
    check(not incomplete, "长期气象只包含完整月份", passed, errors)
    coverage = [float(item.get("coverage_pct", 0)) for item in weather]
    check(bool(coverage) and min(coverage) >= 95, "长期气象各月六点覆盖率不低于95%", passed, errors)
    metadata = correlations.get("metadata", {})
    check(metadata.get("overlap_months", 0) >= 145 and metadata.get("last_month") == "2026-06", "气象相关分析排除2026-07部分月", passed, errors)
    warning_text = str(metadata.get("warning", ""))
    check("相关不等于因果" in warning_text, "相关分析保留非因果警告", passed, errors)
    check(len(cdci.get("records", [])) == 48, "实验性 CDCI 仅对具备年度能碳数据的月份计算", passed, errors)

    report = {
        "generated_at": datetime.now().astimezone().isoformat(),
        "status": "pass" if not errors else "fail",
        "passed": passed,
        "warnings": warnings,
        "errors": errors,
    }
    (data / "validation_summary.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    (root / "DATA_QUALITY_REPORT.md").write_text(markdown_report(report), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not errors else 2


if __name__ == "__main__":
    raise SystemExit(main())
