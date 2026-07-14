from __future__ import annotations

import itertools
import math
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFont


PROJECT_ROOT = Path(r"D:\personal-website")
DAILY_XLSX = Path(r"C:\Users\lenovo\Desktop\日数据.xlsx")
MONTHLY_XLSX = Path(r"C:\Users\lenovo\Desktop\月数据.xlsx")
OUT_DIR = PROJECT_ROOT / "outputs" / "carbon_report"
FIG_DIR = OUT_DIR / "figures"

FONT_REGULAR = Path(r"C:\Windows\Fonts\msyh.ttc")
FONT_BOLD = Path(r"C:\Windows\Fonts\msyhbd.ttc")

OFFICIAL_SOURCES = {
    "双碳赛官网": "https://cpipc.acge.org.cn/cw/hp/2c90800c8093eef401809d348f8b0653",
    "苏州工业园区碳达峰试点方案": "https://www.suzhou.gov.cn/szsrmzf/zfwj/202405/3df5e68dcc1a4bf79947e6cbb4524968.shtml",
    "HJ 633-2026": "https://www.mee.gov.cn/ywgz/fgbz/bz/bzwb/jcffbz/202602/t20260225_1144441.shtml",
}

PALETTE = {
    "blue": "#2F6BFF",
    "green": "#18A058",
    "orange": "#F08C00",
    "red": "#D9480F",
    "purple": "#7048E8",
    "cyan": "#0CA6A6",
    "gray": "#667085",
    "light_gray": "#EEF2F6",
    "axis": "#344054",
    "text": "#182230",
}


def ensure_dirs() -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    path = FONT_BOLD if bold and FONT_BOLD.exists() else FONT_REGULAR
    if path.exists():
        return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


def hex_to_rgb(color: str) -> tuple[int, int, int]:
    color = color.lstrip("#")
    return tuple(int(color[i : i + 2], 16) for i in (0, 2, 4))


def parse_date_range(series: pd.Series) -> tuple[str, str]:
    return series.min().strftime("%Y-%m-%d"), series.max().strftime("%Y-%m-%d")


def add_season(df: pd.DataFrame, month_col: str = "month_num") -> pd.DataFrame:
    season_map = {
        12: "冬季",
        1: "冬季",
        2: "冬季",
        3: "春季",
        4: "春季",
        5: "春季",
        6: "夏季",
        7: "夏季",
        8: "夏季",
        9: "秋季",
        10: "秋季",
        11: "秋季",
    }
    df = df.copy()
    df["season"] = df[month_col].map(season_map)
    return df


def read_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    monthly = pd.read_excel(MONTHLY_XLSX)
    monthly.columns = ["date", "aqi", "range", "quality_level", "pm25", "pm10", "co", "no2", "so2", "o3"]
    monthly["date"] = pd.to_datetime(monthly["date"])
    monthly["year"] = monthly["date"].dt.year
    monthly["month_num"] = monthly["date"].dt.month
    monthly["ym"] = monthly["date"].dt.strftime("%Y-%m")
    monthly = add_season(monthly)

    daily = pd.read_excel(DAILY_XLSX)
    daily.columns = ["date", "aqi", "quality_level", "pm25", "pm10", "CO_raw", "NO2_raw", "SO2_raw", "o3_8h"]
    daily["date"] = pd.to_datetime(daily["date"])
    daily["year"] = daily["date"].dt.year
    daily["month_num"] = daily["date"].dt.month
    daily["ym"] = daily["date"].dt.strftime("%Y-%m")
    daily = add_season(daily)
    return monthly, daily


def correct_daily_fields(daily: pd.DataFrame, monthly: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    raw_cols = ["CO_raw", "NO2_raw", "SO2_raw"]
    pollutants = ["co", "no2", "so2"]
    monthly_targets = monthly.set_index("ym")[pollutants].to_dict("index")
    corrected_groups = []
    log_rows = []

    for ym, group in daily.groupby("ym", sort=True):
        target = monthly_targets.get(ym)
        best = None
        for perm in itertools.permutations(pollutants):
            mapped_avg = {pollutant: float(group[raw].mean()) for raw, pollutant in zip(raw_cols, perm)}
            if target:
                error = sum(
                    abs(mapped_avg[p] - float(target[p])) / (abs(float(target[p])) if float(target[p]) else 1.0)
                    for p in pollutants
                )
            else:
                error = math.inf
            if best is None or error < best[0]:
                best = (error, dict(zip(raw_cols, perm)), mapped_avg)

        assert best is not None
        error, mapping, mapped_avg = best
        group = group.copy()
        for raw_col, pollutant in mapping.items():
            group[pollutant] = group[raw_col]
        corrected_groups.append(group)

        target = target or {p: np.nan for p in pollutants}
        identity = mapping == {"CO_raw": "co", "NO2_raw": "no2", "SO2_raw": "so2"}
        log_rows.append(
            {
                "month": ym,
                "row_count": len(group),
                "CO_raw_mapped_to": mapping["CO_raw"],
                "NO2_raw_mapped_to": mapping["NO2_raw"],
                "SO2_raw_mapped_to": mapping["SO2_raw"],
                "identity_mapping": identity,
                "relative_error": round(float(error), 6),
                "clean_month_avg_co": round(mapped_avg["co"], 6),
                "monthly_table_co": round(float(target["co"]), 6),
                "clean_month_avg_no2": round(mapped_avg["no2"], 6),
                "monthly_table_no2": round(float(target["no2"]), 6),
                "clean_month_avg_so2": round(mapped_avg["so2"], 6),
                "monthly_table_so2": round(float(target["so2"]), 6),
            }
        )

    corrected = pd.concat(corrected_groups, ignore_index=True).sort_values("date")
    return corrected, pd.DataFrame(log_rows)


def normalize(series: pd.Series) -> pd.Series:
    min_v = float(series.min())
    max_v = float(series.max())
    if math.isclose(min_v, max_v):
        return pd.Series(np.zeros(len(series)), index=series.index)
    return (series - min_v) / (max_v - min_v) * 100


def risk_level(score: float) -> str:
    if score < 40:
        return "低风险"
    if score < 70:
        return "中风险"
    return "高风险"


def classify_risk(row: pd.Series) -> str:
    contrib_cols = ["no2_contrib", "so2_contrib", "co_contrib", "pm25_contrib", "o3_contrib"]
    top = sorted(((col.replace("_contrib", ""), row[col]) for col in contrib_cols), key=lambda x: x[1], reverse=True)
    top_names = {top[0][0], top[1][0]}
    if "o3" in top_names and ("no2" in top_names or "pm25" in top_names):
        return "臭氧复合污染型"
    if "pm25" in top_names and ("so2" in top_names or "co" in top_names):
        return "颗粒物燃烧复合型"
    if {"no2", "co"}.issubset(top_names):
        return "交通燃烧型"
    if {"so2", "pm25"}.issubset(top_names):
        return "工业燃烧型"
    if top[0][0] == "o3":
        return "臭氧污染型"
    if top[0][0] == "pm25":
        return "颗粒物污染型"
    return "复合污染型"


def add_risk_index(df: pd.DataFrame, o3_col: str) -> pd.DataFrame:
    df = df.copy()
    df["no2_norm"] = normalize(df["no2"])
    df["so2_norm"] = normalize(df["so2"])
    df["co_norm"] = normalize(df["co"])
    df["pm25_norm"] = normalize(df["pm25"])
    df["o3_norm"] = normalize(df[o3_col])
    weights = {"no2": 0.25, "so2": 0.20, "co": 0.20, "pm25": 0.20, "o3": 0.15}
    for pollutant, weight in weights.items():
        df[f"{pollutant}_contrib"] = df[f"{pollutant}_norm"] * weight
    df["risk_score"] = (
        df["no2_contrib"] + df["so2_contrib"] + df["co_contrib"] + df["pm25_contrib"] + df["o3_contrib"]
    )
    df["risk_level"] = df["risk_score"].apply(risk_level)
    df["main_risk_type"] = df.apply(classify_risk, axis=1)
    return df


def detect_monthly_anomalies(monthly_risk: pd.DataFrame) -> pd.DataFrame:
    pollutants = ["aqi", "pm25", "pm10", "co", "no2", "so2", "o3", "risk_score"]
    baseline = monthly_risk[(monthly_risk["year"] >= 2013) & (monthly_risk["year"] <= 2022)]
    test = monthly_risk[monthly_risk["year"] >= 2023].copy()
    thresholds: dict[tuple[int, str], float] = {}
    for month_num, group in baseline.groupby("month_num"):
        for p in pollutants:
            thresholds[(month_num, p)] = float(group[p].quantile(0.9))

    rows = []
    for _, row in test.iterrows():
        exceeded = []
        max_ratio = 0.0
        for p in pollutants:
            threshold = thresholds.get((int(row["month_num"]), p))
            if threshold is None or threshold == 0 or np.isnan(threshold):
                continue
            if float(row[p]) > threshold:
                ratio = float(row[p]) / threshold
                max_ratio = max(max_ratio, ratio)
                exceeded.append(f"{p}({float(row[p]):.1f}>{threshold:.1f})")
        if exceeded:
            rows.append(
                {
                    "date": row["date"].strftime("%Y-%m"),
                    "year": int(row["year"]),
                    "month": int(row["month_num"]),
                    "quality_level": row["quality_level"],
                    "exceeded_items": "、".join(exceeded),
                    "exceeded_count": len(exceeded),
                    "max_ratio": round(max_ratio, 3),
                    "risk_score": round(float(row["risk_score"]), 1),
                    "risk_level": row["risk_level"],
                    "main_risk_type": row["main_risk_type"],
                }
            )
    return pd.DataFrame(rows).sort_values(["exceeded_count", "max_ratio"], ascending=[False, False])


def pollutant_label(key: str) -> str:
    return {
        "aqi": "AQI",
        "pm25": "PM2.5",
        "pm10": "PM10",
        "co": "CO",
        "no2": "NO2",
        "so2": "SO2",
        "o3": "O3",
        "o3_8h": "O3_8h",
        "risk_score": "风险指数",
    }.get(key, key)


def draw_base(title: str, subtitle: str, width: int = 1280, height: int = 760) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)
    draw.text((60, 32), title, fill=hex_to_rgb(PALETTE["text"]), font=font(34, True))
    draw.text((60, 78), subtitle, fill=hex_to_rgb(PALETTE["gray"]), font=font(20))
    return img, draw


def draw_legend(draw: ImageDraw.ImageDraw, items: list[tuple[str, str]], x: int, y: int) -> None:
    cursor = x
    for label, color in items:
        draw.rectangle((cursor, y + 4, cursor + 22, y + 16), fill=hex_to_rgb(color))
        draw.text((cursor + 30, y), label, fill=hex_to_rgb(PALETTE["text"]), font=font(18))
        cursor += 130 + len(label) * 5


def nice_ticks(min_v: float, max_v: float, count: int = 5) -> list[float]:
    if math.isclose(min_v, max_v):
        return [min_v]
    return [min_v + i * (max_v - min_v) / (count - 1) for i in range(count)]


def line_chart(
    path: Path,
    title: str,
    subtitle: str,
    x_labels: list[str],
    series: list[tuple[str, list[float], str]],
    y_label: str,
    y_min: float | None = None,
    y_max: float | None = None,
    bands: list[tuple[float, float, str]] | None = None,
) -> None:
    img, draw = draw_base(title, subtitle)
    left, top, right, bottom = 105, 135, 1210, 650
    all_values = [v for _, values, _ in series for v in values if not pd.isna(v)]
    min_v = min(all_values) if y_min is None else y_min
    max_v = max(all_values) if y_max is None else y_max
    pad = (max_v - min_v) * 0.08 if not math.isclose(min_v, max_v) else 1
    min_v = min_v - pad if y_min is None else y_min
    max_v = max_v + pad if y_max is None else y_max

    if bands:
        for low, high, color in bands:
            y1 = bottom - (low - min_v) / (max_v - min_v) * (bottom - top)
            y2 = bottom - (high - min_v) / (max_v - min_v) * (bottom - top)
            draw.rectangle((left, min(y1, y2), right, max(y1, y2)), fill=hex_to_rgb(color))

    draw.line((left, top, left, bottom, right, bottom), fill=hex_to_rgb(PALETTE["axis"]), width=2)
    for tick in nice_ticks(min_v, max_v, 6):
        y = bottom - (tick - min_v) / (max_v - min_v) * (bottom - top)
        draw.line((left - 6, y, right, y), fill=hex_to_rgb("#E4E7EC"), width=1)
        draw.text((20, y - 12), f"{tick:.0f}", fill=hex_to_rgb(PALETTE["gray"]), font=font(16))
    draw.text((left, bottom + 52), y_label, fill=hex_to_rgb(PALETTE["gray"]), font=font(16))

    n = len(x_labels)
    label_indices = sorted(set([0, n // 5, 2 * n // 5, 3 * n // 5, 4 * n // 5, n - 1]))
    for idx in label_indices:
        x = left + idx / (n - 1) * (right - left) if n > 1 else left
        draw.line((x, bottom, x, bottom + 6), fill=hex_to_rgb(PALETTE["axis"]), width=1)
        draw.text((x - 38, bottom + 13), x_labels[idx], fill=hex_to_rgb(PALETTE["gray"]), font=font(15))

    for label, values, color in series:
        points = []
        for i, v in enumerate(values):
            if pd.isna(v):
                continue
            x = left + i / (n - 1) * (right - left) if n > 1 else left
            y = bottom - (float(v) - min_v) / (max_v - min_v) * (bottom - top)
            points.append((x, y))
        if len(points) >= 2:
            draw.line(points, fill=hex_to_rgb(color), width=4, joint="curve")
        for x, y in points[:: max(1, len(points) // 20)]:
            draw.ellipse((x - 3, y - 3, x + 3, y + 3), fill=hex_to_rgb(color))

    draw_legend(draw, [(label, color) for label, _, color in series], left, 675)
    img.save(path)


def grouped_bar_chart(path: Path, title: str, subtitle: str, categories: list[str], series: list[tuple[str, list[float], str]], y_label: str) -> None:
    img, draw = draw_base(title, subtitle)
    left, top, right, bottom = 105, 135, 1210, 645
    max_v = max(v for _, values, _ in series for v in values) * 1.15
    draw.line((left, top, left, bottom, right, bottom), fill=hex_to_rgb(PALETTE["axis"]), width=2)
    for tick in nice_ticks(0, max_v, 6):
        y = bottom - tick / max_v * (bottom - top)
        draw.line((left - 6, y, right, y), fill=hex_to_rgb("#E4E7EC"), width=1)
        draw.text((28, y - 12), f"{tick:.0f}", fill=hex_to_rgb(PALETTE["gray"]), font=font(16))
    group_w = (right - left) / len(categories)
    bar_w = group_w / (len(series) + 1.5)
    for i, cat in enumerate(categories):
        cx = left + i * group_w + group_w / 2
        draw.text((cx - 20, bottom + 14), cat, fill=hex_to_rgb(PALETTE["gray"]), font=font(17))
        for j, (_, values, color) in enumerate(series):
            x1 = left + i * group_w + 18 + j * bar_w
            x2 = x1 + bar_w * 0.75
            y1 = bottom - values[i] / max_v * (bottom - top)
            draw.rounded_rectangle((x1, y1, x2, bottom), radius=4, fill=hex_to_rgb(color))
    draw.text((left, bottom + 55), y_label, fill=hex_to_rgb(PALETTE["gray"]), font=font(16))
    draw_legend(draw, [(label, color) for label, _, color in series], left, 675)
    img.save(path)


def stacked_bar_chart(path: Path, title: str, subtitle: str, data: pd.DataFrame, levels: list[str], colors: dict[str, str]) -> None:
    img, draw = draw_base(title, subtitle)
    left, top, right, bottom = 105, 135, 1210, 645
    years = data.index.astype(str).tolist()
    max_v = max(data[levels].sum(axis=1).max(), 1)
    draw.line((left, top, left, bottom, right, bottom), fill=hex_to_rgb(PALETTE["axis"]), width=2)
    for tick in range(0, int(max_v) + 1):
        y = bottom - tick / max_v * (bottom - top)
        draw.line((left - 6, y, right, y), fill=hex_to_rgb("#E4E7EC"), width=1)
        draw.text((55, y - 10), str(tick), fill=hex_to_rgb(PALETTE["gray"]), font=font(15))
    bar_w = (right - left) / len(years) * 0.62
    for i, year in enumerate(years):
        x1 = left + i / len(years) * (right - left) + (right - left) / len(years) * 0.18
        x2 = x1 + bar_w
        y_cursor = bottom
        for level in levels:
            value = float(data.loc[int(year), level]) if level in data.columns else 0.0
            h = value / max_v * (bottom - top)
            draw.rectangle((x1, y_cursor - h, x2, y_cursor), fill=hex_to_rgb(colors[level]))
            y_cursor -= h
        if i % 2 == 0 or len(years) <= 8:
            draw.text((x1 - 5, bottom + 12), year, fill=hex_to_rgb(PALETTE["gray"]), font=font(14))
    draw_legend(draw, [(level, colors[level]) for level in levels], left, 675)
    img.save(path)


def horizontal_bar_chart(path: Path, title: str, subtitle: str, labels: list[str], values: list[int], color: str) -> None:
    img, draw = draw_base(title, subtitle)
    left, top, right, bottom = 300, 140, 1210, 660
    max_v = max(max(values), 1)
    bar_h = min(48, (bottom - top) / max(len(labels), 1) * 0.62)
    for i, (label, value) in enumerate(zip(labels, values)):
        y = top + i * ((bottom - top) / max(len(labels), 1)) + 8
        draw.text((60, y + 7), label, fill=hex_to_rgb(PALETTE["text"]), font=font(18))
        x2 = left + value / max_v * (right - left)
        draw.rounded_rectangle((left, y, x2, y + bar_h), radius=5, fill=hex_to_rgb(color))
        draw.text((x2 + 10, y + 7), str(value), fill=hex_to_rgb(PALETTE["gray"]), font=font(18))
    img.save(path)


def table_image(path: Path, title: str, subtitle: str, rows: list[dict[str, object]]) -> None:
    width, height = 1560, 760
    img, draw = draw_base(title, subtitle, width=width, height=height)
    columns = [
        ("date", "日期", 125),
        ("aqi", "AQI", 75),
        ("quality_level", "等级", 105),
        ("risk_score", "风险", 85),
        ("main_risk_type", "类型", 180),
        ("pm25", "PM2.5", 90),
        ("no2", "NO2", 80),
        ("so2", "SO2", 80),
        ("co", "CO", 80),
        ("o3_8h", "O3_8h", 90),
        ("advice", "治理建议", 430),
    ]
    x0, y0 = 40, 140
    row_h = 78
    draw.rectangle((x0, y0, width - 40, y0 + 42), fill=hex_to_rgb("#EAF2FF"))
    x = x0
    for _, label, col_w in columns:
        draw.text((x + 8, y0 + 9), label, fill=hex_to_rgb(PALETTE["text"]), font=font(17, True))
        x += col_w
    for i, row in enumerate(rows):
        y = y0 + 42 + i * row_h
        fill = "#FFFFFF" if i % 2 == 0 else "#F8FAFC"
        draw.rectangle((x0, y, width - 40, y + row_h), fill=hex_to_rgb(fill))
        x = x0
        for key, _, col_w in columns:
            value = row.get(key, "")
            text = f"{value:.1f}" if isinstance(value, float) else str(value)
            if key == "advice":
                lines = [text[i : i + 23] for i in range(0, len(text), 23)]
                if len(lines) > 2:
                    lines = [lines[0], lines[1][:20] + "..."]
                for line_idx, line in enumerate(lines):
                    draw.text((x + 8, y + 10 + line_idx * 24), line, fill=hex_to_rgb(PALETTE["text"]), font=font(15))
            else:
                draw.text((x + 8, y + 12), text, fill=hex_to_rgb(PALETTE["text"]), font=font(15))
            x += col_w
        draw.line((x0, y + row_h, width - 40, y + row_h), fill=hex_to_rgb("#E4E7EC"), width=1)
    img.save(path)


def advice_for_type(risk_type: str) -> str:
    if "臭氧" in risk_type:
        return "加强VOCs与NOx协同控制，关注夏季高温时段臭氧预警。"
    if "交通" in risk_type:
        return "优化货运通行时段，推进新能源物流与错峰运输。"
    if "工业" in risk_type:
        return "排查燃烧源与工业炉窑，推进清洁能源替代和末端治理。"
    if "颗粒物" in risk_type:
        return "加强扬尘、燃烧源和重污染天气应急联动。"
    return "同步开展交通、工业、能源和应急管控，按主贡献污染物分级治理。"


def build_charts(monthly_risk: pd.DataFrame, daily_risk: pd.DataFrame, anomalies: pd.DataFrame) -> dict[str, Path]:
    figs: dict[str, Path] = {}
    x_months = monthly_risk["date"].dt.strftime("%Y-%m").tolist()
    figs["monthly_trend"] = FIG_DIR / "01_monthly_trend_aqi_pm25_o3.png"
    line_chart(
        figs["monthly_trend"],
        "苏州空气质量月度趋势",
        "月数据，2013-12 至 2026-07；O3 为月表字段",
        x_months,
        [
            ("AQI", monthly_risk["aqi"].tolist(), PALETTE["blue"]),
            ("PM2.5", monthly_risk["pm25"].tolist(), PALETTE["green"]),
            ("O3", monthly_risk["o3"].tolist(), PALETTE["orange"]),
        ],
        "月均值",
    )

    annual = monthly_risk.groupby("year", as_index=False)[["aqi", "pm25", "o3", "no2"]].mean()
    figs["annual_trend"] = FIG_DIR / "02_annual_pollutant_trend.png"
    line_chart(
        figs["annual_trend"],
        "年度均值变化",
        "2026 年为 1-7 月阶段值；用于观察长期改善与臭氧波动",
        annual["year"].astype(str).tolist(),
        [
            ("AQI", annual["aqi"].tolist(), PALETTE["blue"]),
            ("PM2.5", annual["pm25"].tolist(), PALETTE["green"]),
            ("O3", annual["o3"].tolist(), PALETTE["orange"]),
            ("NO2", annual["no2"].tolist(), PALETTE["purple"]),
        ],
        "年度均值",
    )

    seasonal = monthly_risk.groupby("season")[["pm25", "o3", "no2", "so2"]].mean().reindex(["春季", "夏季", "秋季", "冬季"])
    figs["seasonal_profile"] = FIG_DIR / "03_seasonal_pollution_profile.png"
    grouped_bar_chart(
        figs["seasonal_profile"],
        "季节性污染画像",
        "颗粒物、臭氧和燃烧相关污染物的季节差异",
        seasonal.index.tolist(),
        [
            ("PM2.5", seasonal["pm25"].tolist(), PALETTE["green"]),
            ("O3", seasonal["o3"].tolist(), PALETTE["orange"]),
            ("NO2", seasonal["no2"].tolist(), PALETTE["purple"]),
            ("SO2", seasonal["so2"].tolist(), PALETTE["cyan"]),
        ],
        "月均浓度/指数",
    )

    levels = ["优", "良", "轻度污染", "中度污染"]
    counts = monthly_risk.pivot_table(index="year", columns="quality_level", values="date", aggfunc="count", fill_value=0)
    for level in levels:
        if level not in counts.columns:
            counts[level] = 0
    figs["quality_distribution"] = FIG_DIR / "04_quality_level_distribution.png"
    stacked_bar_chart(
        figs["quality_distribution"],
        "月度空气质量等级分布",
        "注意：月数据只有月等级，不能解释为逐日天数",
        counts[levels],
        levels,
        {"优": "#51CF66", "良": "#74C0FC", "轻度污染": "#FFD43B", "中度污染": "#FFA94D"},
    )

    figs["risk_index"] = FIG_DIR / "05_monthly_risk_index.png"
    line_chart(
        figs["risk_index"],
        "碳污协同风险指数",
        "指数由 NO2、SO2、CO、PM2.5、O3 标准化加权构建",
        x_months,
        [("风险指数", monthly_risk["risk_score"].tolist(), PALETTE["red"])],
        "0-100 标准化评分",
        y_min=0,
        y_max=100,
        bands=[(0, 40, "#F0FFF4"), (40, 70, "#FFF9DB"), (70, 100, "#FFF0F0")],
    )

    pollutant_counts = {
        label: anomalies["exceeded_items"].str.contains(key, regex=False).sum()
        for key, label in [
            ("aqi", "AQI"),
            ("pm25", "PM2.5"),
            ("pm10", "PM10"),
            ("co", "CO"),
            ("no2", "NO2"),
            ("so2", "SO2"),
            ("o3", "O3"),
            ("risk_score", "风险指数"),
        ]
    }
    pollutant_counts = dict(sorted(pollutant_counts.items(), key=lambda item: item[1], reverse=True))
    figs["anomaly_counts"] = FIG_DIR / "06_anomaly_counts_2023_2026.png"
    horizontal_bar_chart(
        figs["anomaly_counts"],
        "2023-2026 异常月份触发项",
        "阈值为 2013-2022 同月历史 90% 分位数",
        list(pollutant_counts.keys()),
        list(pollutant_counts.values()),
        PALETTE["purple"],
    )

    top_daily = daily_risk.sort_values("risk_score", ascending=False).head(6).copy()
    top_daily["date"] = top_daily["date"].dt.strftime("%Y-%m-%d")
    top_daily["advice"] = top_daily["main_risk_type"].apply(advice_for_type)
    figs["daily_cases"] = FIG_DIR / "07_daily_high_risk_cases.png"
    table_image(
        figs["daily_cases"],
        "日级高风险日期回放",
        "清洗后的 2013-2015 日数据样例；不代表 2016-2026 日级结果",
        top_daily[
            ["date", "aqi", "quality_level", "risk_score", "main_risk_type", "pm25", "no2", "so2", "co", "o3_8h", "advice"]
        ].to_dict("records"),
    )
    return figs


def markdown_table(df: pd.DataFrame, columns: list[str], max_rows: int = 10) -> str:
    sample = df[columns].head(max_rows).copy()
    if sample.empty:
        return "无记录。"

    def fmt(value: object) -> str:
        if pd.isna(value):
            return ""
        if isinstance(value, float):
            return f"{value:.1f}" if abs(value) >= 1 else f"{value:.3f}"
        return str(value).replace("|", "\\|")

    header = "| " + " | ".join(columns) + " |"
    separator = "| " + " | ".join(["---"] * len(columns)) + " |"
    rows = ["| " + " | ".join(fmt(row[col]) for col in columns) + " |" for _, row in sample.iterrows()]
    return "\n".join([header, separator, *rows])


def format_pct_change(start: float, end: float) -> str:
    if start == 0:
        return "NA"
    change = (end - start) / start * 100
    return f"{change:+.1f}%"


def build_report(
    monthly: pd.DataFrame,
    daily: pd.DataFrame,
    cleaning_log: pd.DataFrame,
    monthly_risk: pd.DataFrame,
    daily_risk: pd.DataFrame,
    anomalies: pd.DataFrame,
    figs: dict[str, Path],
) -> None:
    monthly_start, monthly_end = parse_date_range(monthly["date"])
    daily_start, daily_end = parse_date_range(daily["date"])
    annual = monthly_risk.groupby("year")[["aqi", "pm25", "o3", "risk_score"]].mean()
    y_start, y_end = 2014, 2025
    peak_risk = monthly_risk.sort_values("risk_score", ascending=False).iloc[0]
    peak_aqi = monthly_risk.sort_values("aqi", ascending=False).iloc[0]
    non_identity = int((~cleaning_log["identity_mapping"]).sum())
    avg_mapping_error = cleaning_log["relative_error"].mean()
    anomaly_count = len(anomalies)
    top_anomaly_table = anomalies.head(8).copy()
    if not top_anomaly_table.empty:
        top_anomaly_table = top_anomaly_table[
            ["date", "quality_level", "exceeded_count", "risk_score", "risk_level", "main_risk_type", "exceeded_items"]
        ]

    high_daily = daily_risk.sort_values("risk_score", ascending=False).head(8).copy()
    high_daily["date"] = high_daily["date"].dt.strftime("%Y-%m-%d")
    high_daily["advice"] = high_daily["main_risk_type"].apply(advice_for_type)

    report = f"""# 园区碳眼：基于空气质量数据驱动的苏州工业园区减污降碳协同预警与治理决策报告

生成日期：{datetime.now().strftime("%Y-%m-%d %H:%M")}

## 1. 项目定位与比赛适配

本报告服务于“园区碳眼”第一版项目展示：基于苏州市空气质量长时间序列数据，构建面向苏州工业园区治理场景的减污降碳协同预警与决策参考。项目不把空气质量数据直接等同于碳排放数据，也不输出园区正式碳核算结果。

从参赛叙事看，项目主线更适合放在“减污降碳与循环经济”下的监测、预警、协同治理方向，并将零碳园区治理作为应用场景延展。政策背景上，苏州工业园区国家碳达峰试点建设强调产业绿色转型、能源高效利用、基础设施绿色先行和低碳生活推广，本项目的治理建议模块可以与这些方向对应。

官方背景链接：

- [中国研究生“双碳”创新与创意大赛官网]({OFFICIAL_SOURCES["双碳赛官网"]})
- [国家碳达峰试点（苏州工业园区）实施方案]({OFFICIAL_SOURCES["苏州工业园区碳达峰试点方案"]})
- [环境空气质量指数 AQI 技术规定 HJ 633-2026]({OFFICIAL_SOURCES["HJ 633-2026"]})

## 2. 数据来源与数据质量

| 数据文件 | 时间范围 | 记录数 | 用途 |
|---|---:|---:|---|
| `月数据.xlsx` | {monthly_start[:7]} 至 {monthly_end[:7]} | {len(monthly)} | 长期趋势、季节规律、月度异常预警、风险指数主证据 |
| `日数据.xlsx` | {daily_start} 至 {daily_end} | {len(daily)} | 日级高风险日期回放和方法样例 |

月数据无空值，字段包括 AQI、质量等级、PM2.5、PM10、CO、NO2、SO2、O3。日数据无空值，但 `CO/NO2/SO2` 三列存在月份级字段顺序变化。处理方式是：对每个月枚举三列的 6 种可能映射，计算映射后的日均值与月表对应月均值的相对误差，选取误差最小的映射作为该月清洗结果。

清洗结果：日表覆盖 {cleaning_log.shape[0]} 个月，其中 {non_identity} 个月需要调整字段映射；平均相对误差为 {avg_mapping_error:.4f}。完整记录见 `cleaning_log.csv`。

## 3. 苏州空气质量长期趋势

![苏州空气质量月度趋势](figures/{figs["monthly_trend"].name})

2014 至 2025 年，月均 AQI 从 {annual.loc[y_start, "aqi"]:.1f} 变化到 {annual.loc[y_end, "aqi"]:.1f}，变化幅度为 {format_pct_change(annual.loc[y_start, "aqi"], annual.loc[y_end, "aqi"])}；月均 PM2.5 从 {annual.loc[y_start, "pm25"]:.1f} 变化到 {annual.loc[y_end, "pm25"]:.1f}，变化幅度为 {format_pct_change(annual.loc[y_start, "pm25"], annual.loc[y_end, "pm25"])}。这说明颗粒物污染整体改善较明显，但 O3 的季节波动仍然突出。

![年度均值变化](figures/{figs["annual_trend"].name})

最高 AQI 月份为 {peak_aqi["date"].strftime("%Y-%m")}，AQI 为 {peak_aqi["aqi"]:.0f}，质量等级为 {peak_aqi["quality_level"]}。该月份也反映出早期冬季颗粒物污染压力较高。

## 4. 季节性污染特征

![季节性污染画像](figures/{figs["seasonal_profile"].name})

季节规律上，PM2.5 和 NO2 更容易在冬季抬升，O3 在夏季更突出。这个特征符合“冬季颗粒物与燃烧排放、静稳气象相关，夏季臭氧与光化学反应相关”的治理逻辑。对园区场景来说，冬季应强调颗粒物、燃烧源和重污染天气应急，夏季应强调 VOCs 与 NOx 协同控制。

![月度空气质量等级分布](figures/{figs["quality_distribution"].name})

注意：月表中的质量等级是月尺度等级，不等同于优良天数。若后续补齐 2016-2026 日数据，可以进一步计算年度优良天数、污染天数和重污染天数。

## 5. 碳污协同风险指数

本报告构建“碳污协同风险指数”，用于表达交通、燃烧、工业和复合污染的协同风险，不表示 CO2 排放核算值。

公式如下：

```text
风险指数 =
0.25 × NO2标准化值
+ 0.20 × SO2标准化值
+ 0.20 × CO标准化值
+ 0.20 × PM2.5标准化值
+ 0.15 × O3标准化值
```

风险等级设定为：0-40 低风险，40-70 中风险，70-100 高风险。

![碳污协同风险指数](figures/{figs["risk_index"].name})

月度风险最高的是 {peak_risk["date"].strftime("%Y-%m")}，风险指数为 {peak_risk["risk_score"]:.1f}，风险等级为 {peak_risk["risk_level"]}，主要风险类型为 {peak_risk["main_risk_type"]}。该指标的优势在于可以拆分贡献污染物，用于解释为什么某个月被识别为高风险。

## 6. 异常预警与高风险案例

月度异常识别采用 2013-2022 年同月历史 90% 分位数作为阈值，对 2023-2026 年逐月检测。共识别出 {anomaly_count} 个月份存在至少一个异常触发项。

![2023-2026 异常月份触发项](figures/{figs["anomaly_counts"].name})

异常月份样例：

{markdown_table(top_anomaly_table, top_anomaly_table.columns.tolist(), 8) if not top_anomaly_table.empty else "未识别出异常月份。"}

日级样例只使用清洗后的 2013-2015 日数据，适合展示“高风险日期回放”的产品效果，不外推到 2016-2026。

![日级高风险日期回放](figures/{figs["daily_cases"].name})

高风险日期表：

{markdown_table(high_daily[["date", "aqi", "quality_level", "risk_score", "risk_level", "main_risk_type", "pm25", "no2", "so2", "co", "o3_8h", "advice"]], ["date", "aqi", "quality_level", "risk_score", "risk_level", "main_risk_type", "pm25", "no2", "so2", "co", "o3_8h", "advice"], 8)}

## 7. 园区治理建议

本项目第一版建议采用规则解释层，把“污染物组合”转化为可答辩的治理建议：

| 风险类型 | 判断依据 | 治理建议 |
|---|---|---|
| 颗粒物污染型 | PM2.5 或 PM10 贡献较高 | 加强扬尘、燃烧源、施工和道路积尘管控，完善重污染天气应急联动 |
| 交通燃烧型 | NO2 与 CO 贡献较高 | 优化货运车辆通行时段，推进新能源物流车替代，实施重点路段错峰运输 |
| 工业燃烧型 | SO2 与 PM2.5 贡献较高 | 排查工业燃烧源和锅炉炉窑，推进清洁能源替代和末端治理设施稳定运行 |
| 臭氧污染型 | O3 贡献较高，常见于夏季 | 加强 VOCs 与 NOx 协同控制，关注高温晴热时段臭氧预警 |
| 复合污染型 | 多污染物同时处于较高水平 | 联动交通、工业、能源和应急管理，按主贡献污染物分级响应 |

这些建议应被描述为“城市背景数据下的园区治理参考”。若要升级到真正的园区精细化管控，需要进一步接入园区站点、企业能耗、排污许可、交通流量和气象数据。

## 8. 局限性与后续扩展

1. 当前空气质量数据是苏州市级，不是园区内部站点数据，因此只能支撑面向园区场景的辅助研判。
2. 当前没有 CO2 清单、企业能耗或企业排放数据，因此风险指数不能作为正式碳核算结果。
3. 当前日数据只覆盖 2013-12 至 2015-07，2016-2026 的日级预警需要补齐日表后再做。
4. 当前未接入气象数据，异常识别偏统计阈值；后续可加入温度、湿度、风速、风向、降水和气压提高解释力。
5. 后续可接入 CEADs、MEIC 或 Carbon Monitor Cities 等城市级清单，用于增强减污降碳协同分析背景。

## 附录：产物清单

- `园区碳眼_数据分析报告.md`：本报告
- `data_dictionary.md`：字段、清洗、风险指数和预警方法说明
- `cleaning_log.csv`：日表字段纠偏记录
- `figures/*.png`：报告图表
"""
    (OUT_DIR / "园区碳眼_数据分析报告.md").write_text(report, encoding="utf-8")


def build_data_dictionary() -> None:
    content = f"""# 园区碳眼数据字典与方法说明

## 原始数据

| 文件 | 关键字段 | 说明 |
|---|---|---|
| `月数据.xlsx` | 月份、AQI、范围、质量等级、PM2.5、PM10、CO、NO2、SO2、O3 | 2013-12 至 2026-07 月尺度主数据 |
| `日数据.xlsx` | 日期、AQI、质量等级、PM2.5、PM10、CO、NO2、SO2、O3_8h | 2013-12-02 至 2015-07-31 日尺度样例数据 |

## 派生字段

| 字段 | 来源 | 说明 |
|---|---|---|
| `year` | 日期字段 | 年份 |
| `month_num` | 日期字段 | 月份数字 |
| `season` | `month_num` | 春季、夏季、秋季、冬季 |
| `*_norm` | 污染物字段 | 在当前分析数据集内做 min-max 标准化到 0-100 |
| `risk_score` | 标准化污染物 | 碳污协同风险指数 |
| `risk_level` | `risk_score` | 低风险、中风险、高风险 |
| `main_risk_type` | 风险贡献项 | 颗粒物、臭氧、交通燃烧、工业燃烧或复合污染类型 |

## 日数据字段纠偏

日表中的 `CO/NO2/SO2` 三列存在月份级顺序变化。处理方法：

1. 对每个月枚举三列对应 `co/no2/so2` 的 6 种可能映射。
2. 计算每种映射下的日均值。
3. 与月表同月份的 `CO/NO2/SO2` 均值比较。
4. 选择相对误差最小的映射作为该月清洗结果。
5. 将每个月的映射和误差写入 `cleaning_log.csv`。

## 风险指数

```text
风险指数 =
0.25 × NO2标准化值
+ 0.20 × SO2标准化值
+ 0.20 × CO标准化值
+ 0.20 × PM2.5标准化值
+ 0.15 × O3标准化值
```

风险等级：

| 分数 | 等级 |
|---:|---|
| 0-40 | 低风险 |
| 40-70 | 中风险 |
| 70-100 | 高风险 |

## 异常识别

月度异常采用 2013-2022 年同月历史 90% 分位数作为阈值，对 2023-2026 年各月检测。任一污染物或风险指数超过同月阈值，即记录为异常月份。

## 项目表达边界

当前结果定位为城市背景数据下的辅助预警和治理参考，不作为园区或企业正式碳核算结果。后续可接入园区内部站点、企业能耗、排污清单、气象数据和城市级 CO2 清单增强分析。

## 官方背景来源

- 双碳赛官网：{OFFICIAL_SOURCES["双碳赛官网"]}
- 苏州工业园区碳达峰试点方案：{OFFICIAL_SOURCES["苏州工业园区碳达峰试点方案"]}
- HJ 633-2026：{OFFICIAL_SOURCES["HJ 633-2026"]}
"""
    (OUT_DIR / "data_dictionary.md").write_text(content, encoding="utf-8")


def save_validation(
    monthly: pd.DataFrame,
    daily: pd.DataFrame,
    cleaning_log: pd.DataFrame,
    figs: dict[str, Path],
    anomalies: pd.DataFrame,
) -> None:
    monthly_start, monthly_end = parse_date_range(monthly["date"])
    daily_start, daily_end = parse_date_range(daily["date"])
    fig_lines = [f"- {path.name}: {'OK' if path.exists() and path.stat().st_size > 0 else 'MISSING'}" for path in figs.values()]
    content = f"""# Validation Summary

- Monthly rows: {len(monthly)}
- Monthly date range: {monthly_start} to {monthly_end}
- Daily rows: {len(daily)}
- Daily date range: {daily_start} to {daily_end}
- Monthly null values: {int(monthly.isna().sum().sum())}
- Daily null values after cleaning: {int(daily[["aqi", "pm25", "pm10", "co", "no2", "so2", "o3_8h"]].isna().sum().sum())}
- Cleaning log rows: {len(cleaning_log)}
- Average relative mapping error: {cleaning_log["relative_error"].mean():.6f}
- Anomaly months detected: {len(anomalies)}

## Figures

{chr(10).join(fig_lines)}
"""
    (OUT_DIR / "validation_summary.md").write_text(content, encoding="utf-8")


def main() -> None:
    ensure_dirs()
    monthly, daily_raw = read_data()
    daily, cleaning_log = correct_daily_fields(daily_raw, monthly)
    monthly_risk = add_risk_index(monthly, "o3")
    daily_risk = add_risk_index(daily, "o3_8h")
    anomalies = detect_monthly_anomalies(monthly_risk)

    cleaning_log.to_csv(OUT_DIR / "cleaning_log.csv", index=False, encoding="utf-8-sig")
    monthly_risk.to_csv(OUT_DIR / "monthly_risk_index.csv", index=False, encoding="utf-8-sig")
    daily_risk.to_csv(OUT_DIR / "daily_cleaned_risk_sample.csv", index=False, encoding="utf-8-sig")
    anomalies.to_csv(OUT_DIR / "monthly_anomalies_2023_2026.csv", index=False, encoding="utf-8-sig")

    figs = build_charts(monthly_risk, daily_risk, anomalies)
    build_report(monthly, daily, cleaning_log, monthly_risk, daily_risk, anomalies, figs)
    build_data_dictionary()
    save_validation(monthly, daily, cleaning_log, figs, anomalies)

    print(f"Report written to: {OUT_DIR}")
    print(f"Figures: {len(figs)}")
    print(f"Monthly rows: {len(monthly)}, Daily rows: {len(daily)}")
    print(f"Anomaly months: {len(anomalies)}")


if __name__ == "__main__":
    main()
