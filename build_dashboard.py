#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
淘联红包核销率回补长期跟踪 dashboard。

第一版不区分会场，统一看全局红包核销率：
- 实际数据日 / 实际回补日 = 文件名日期 + 1 天
- 点击日 = 表内“日期”
- lag_days = 实际数据日 - 点击日
- 红包核销率 = 红包使用量 / 红包发放数
- 回补日强度 = 同一实际数据日对角线上的边际核销率提升
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


BASE_DIR = Path("/Users/jienmaike/点击归因跟踪淘联发酵情况")
PROCESSED_DIR = BASE_DIR / "data_processed"
DASHBOARD_DIR = BASE_DIR / "dashboard"
ASSETS_DIR = DASHBOARD_DIR / "assets"
DOCS_DIR = BASE_DIR / "docs"
# 淘联红包核销窗口按 15 个自然日展示：D0-D14。
MAX_LAG = 14


NUMERIC_COLUMNS = [
    "pv",
    "uv",
    "订单量",
    "红包量",
    "红包使用量",
    "cpa",
    "cpa收入",
    "cps收入",
    "预估总收入",
]


def clean_float(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, float) and (np.isnan(value) or np.isinf(value)):
        return None
    if isinstance(value, np.floating):
        value = float(value)
        return None if np.isnan(value) or np.isinf(value) else value
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, pd.Timestamp):
        return value.strftime("%Y-%m-%d")
    return value


def records_for_json(df: pd.DataFrame) -> list[dict[str, Any]]:
    cleaned = df.copy()
    for col in cleaned.columns:
        if pd.api.types.is_datetime64_any_dtype(cleaned[col]):
            cleaned[col] = cleaned[col].dt.strftime("%Y-%m-%d")
    return [
        {key: clean_float(value) for key, value in row.items()}
        for row in cleaned.replace({np.nan: None}).to_dict(orient="records")
    ]


def source_files() -> list[Path]:
    return sorted(BASE_DIR.glob("20*.csv"))


def build_event_calendar() -> pd.DataFrame:
    rows = [
        ("平台活动", "超级88 第一场", "2026-04-07", "2026-04-10", "S级", "官方立减商品 8.8 折起"),
        ("平台活动", "超级88 第二场", "2026-04-15", "2026-04-19", "S级", "官方立减商品 8.8 折起"),
        ("平台活动", "百亿加补周", "2026-04-23", "2026-04-30", "S级", "百亿加补周"),
        ("营销活动", "超U快抢日", "2026-04-01", "2026-04-30", "常规", "淘礼金红包至高补贴20%"),
        ("营销活动", "U享礼金", "2026-04-01", "2026-04-30", "常规", "礼金面额5%-15%"),
        ("营销活动", "品牌团 4月第一场", "2026-04-07", "2026-04-10", "重点", "天猫超市 400-80 淘客券"),
        ("营销活动", "品牌团 4月第二场", "2026-04-15", "2026-04-19", "重点", "天猫超市 400-80 淘客券"),
        ("营销活动", "品牌团 4月第三场", "2026-04-23", "2026-04-30", "重点", "天猫超市 400-80 淘客券"),
        ("推广激励", "推广激励 4/22-4/26", "2026-04-22", "2026-04-26", "重点", "主会场/营销金/千万补贴等"),
        ("推广激励", "推广激励 4/27-4/30", "2026-04-27", "2026-04-30", "重点", "主会场/营销金/千万补贴等"),
        ("平台活动", "510周年庆", "2026-05-06", "2026-05-10", "S级", "官方立减商品 8.5 折起"),
        ("平台活动", "520告白季", "2026-05-13", "2026-05-20", "S级", "官方立减商品 8.5 折起"),
        ("营销活动", "超U补贴日", "2026-05-01", "2026-06-30", "常规", "淘礼金红包至高补贴20%"),
        ("营销活动", "U享礼金", "2026-05-01", "2026-06-30", "常规", "礼金面额5%-15%"),
        ("营销活动", "天猫超秒 第一段", "2026-05-11", "2026-05-12", "重点", "每天10点 百款商品1元起购"),
        ("营销活动", "天猫超秒 第二段", "2026-05-18", "2026-05-19", "重点", "每天10点 百款商品1元起购"),
        ("营销活动", "品牌团 5月", "2026-05-13", "2026-05-30", "重点", "服饰 淘客专项加补券"),
        ("营销活动", "品牌日 快淘秒杀白马季", "2026-05-16", "2026-05-20", "重点", "价格补贴至高21%"),
        ("营销活动", "品牌日 快淘百补大牌日", "2026-05-24", "2026-05-26", "重点", "价格补贴至高21%"),
        ("营销活动", "品牌日 快淘淘金币品类日", "2026-05-27", "2026-05-29", "重点", "价格补贴至高21%"),
        ("推广激励", "推广激励 5/4-5/10", "2026-05-04", "2026-05-10", "重点", "主会场/红包会场/超级红包等"),
        ("推广激励", "推广激励 5/11-5/20", "2026-05-11", "2026-05-20", "重点", "主会场/红包会场/超级红包等"),
        ("推广激励", "推广激励 5/21-5/30", "2026-05-21", "2026-05-30", "重点", "618前置推广激励"),
        ("618节奏", "预售定金", "2026-05-21", "2026-05-26", "S级", "618前置蓄水"),
        ("618节奏", "618抢先购", "2026-05-21", "2026-05-30", "S级", "618抢先购"),
        ("618节奏", "现货售卖", "2026-05-27", "2026-06-03", "S级", "现货转化窗口"),
        ("618节奏", "618狂欢节", "2026-05-31", "2026-06-21", "S级", "大促主周期"),
        ("主题活动", "超级划算", "2026-05-06", "2026-05-30", "重点", "价佣同享"),
        ("主题活动", "跨店满减", "2026-05-01", "2026-06-30", "常规", "全行业跨店满减"),
        ("主题活动", "直播间限时秒杀", "2026-05-01", "2026-06-30", "常规", "直播限时订单补贴"),
    ]
    event = pd.DataFrame(rows, columns=["event_type", "event_name", "start_date", "end_date", "event_level", "benefit"])
    event["start_date"] = pd.to_datetime(event["start_date"])
    event["end_date"] = pd.to_datetime(event["end_date"])
    event["duration_days"] = (event["end_date"] - event["start_date"]).dt.days + 1
    return event


def load_snapshot_base() -> tuple[pd.DataFrame, pd.DataFrame]:
    frames: list[pd.DataFrame] = []
    file_rows: list[dict[str, Any]] = []
    for path in source_files():
        file_date = pd.to_datetime(path.stem, format="%Y%m%d")
        actual_snapshot_date = file_date + pd.Timedelta(days=1)
        df = pd.read_csv(path, encoding="utf-8-sig")
        df.columns = [str(col).strip().lstrip("\ufeff") for col in df.columns]
        for col in NUMERIC_COLUMNS:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        df["source_file"] = path.name
        df["file_date"] = file_date
        df["actual_snapshot_date"] = actual_snapshot_date
        df["click_date"] = pd.to_datetime(df["日期"], errors="coerce")
        df["lag_days"] = (df["actual_snapshot_date"] - df["click_date"]).dt.days
        df["is_cpa"] = (df["cpa"].fillna(0) > 0) | (df["cpa收入"].fillna(0) > 0)

        file_rows.append(
            {
                "source_file": path.name,
                "file_date": file_date,
                "actual_snapshot_date": actual_snapshot_date,
                "raw_rows": len(df),
                "click_date_min": df["click_date"].min(),
                "click_date_max": df["click_date"].max(),
            }
        )
        frames.append(df)

    if not frames:
        raise SystemExit("没有找到 YYYYMMDD.csv 源文件。")

    raw = pd.concat(frames, ignore_index=True)
    raw = raw.dropna(subset=["click_date", "编号"]).copy()
    group_cols = [
        "actual_snapshot_date",
        "file_date",
        "source_file",
        "click_date",
        "lag_days",
        "编号",
        "渠道",
        "负责人",
    ]
    agg = raw.groupby(group_cols, dropna=False, as_index=False)[NUMERIC_COLUMNS].sum(min_count=1)
    agg["redemption_rate"] = np.where(agg["红包量"] > 0, agg["红包使用量"] / agg["红包量"], np.nan)
    agg["order_rate_by_uv"] = np.where(agg["uv"] > 0, agg["订单量"] / agg["uv"], np.nan)
    agg["uv_income"] = np.where(agg["uv"] > 0, agg["预估总收入"] / agg["uv"], np.nan)
    return agg, pd.DataFrame(file_rows)


def build_day_lag_summary(base: pd.DataFrame) -> pd.DataFrame:
    valid = base[(base["lag_days"] >= 0) & (base["lag_days"] <= MAX_LAG)].copy()
    grouped = valid.groupby(["click_date", "lag_days"], as_index=False).agg(
        id_count=("编号", "nunique"),
        channel_count=("渠道", "nunique"),
        pv=("pv", "sum"),
        uv=("uv", "sum"),
        orders=("订单量", "sum"),
        red_packets=("红包量", "sum"),
        redemptions=("红包使用量", "sum"),
        cpa=("cpa", "sum"),
        cpa_income=("cpa收入", "sum"),
        cps_income=("cps收入", "sum"),
        estimated_income=("预估总收入", "sum"),
    )
    grouped["redemption_rate"] = np.where(
        grouped["red_packets"] > 0, grouped["redemptions"] / grouped["red_packets"], np.nan
    )
    grouped["order_rate_by_uv"] = np.where(grouped["uv"] > 0, grouped["orders"] / grouped["uv"], np.nan)
    grouped["uv_income"] = np.where(grouped["uv"] > 0, grouped["estimated_income"] / grouped["uv"], np.nan)
    return grouped.sort_values(["click_date", "lag_days"])


def build_maturity_matrix(day_lag: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for click_date, group in day_lag.groupby("click_date"):
        rec: dict[str, Any] = {"click_date": click_date}
        for _, row in group.iterrows():
            lag = int(row["lag_days"])
            rec[f"D{lag}_redemption_rate"] = row["redemption_rate"]
            rec[f"D{lag}_red_packets"] = row["red_packets"]
            rec[f"D{lag}_redemptions"] = row["redemptions"]
            rec[f"D{lag}_estimated_income"] = row["estimated_income"]
        available_lags = sorted(int(v) for v in group["lag_days"].dropna().unique())
        if available_lags:
            latest_lag = max(available_lags)
            rec["latest_lag"] = latest_lag
            rec["latest_lag_label"] = f"D{latest_lag}"
            rec["latest_redemption_rate"] = rec.get(f"D{latest_lag}_redemption_rate")
        d0 = rec.get("D0_redemption_rate")
        for lag in range(1, MAX_LAG + 1):
            value = rec.get(f"D{lag}_redemption_rate")
            rec[f"D{lag}_lift_pp"] = (value - d0) * 100 if pd.notna(d0) and pd.notna(value) else np.nan
        if pd.notna(d0) and pd.notna(rec.get("latest_redemption_rate")):
            rec["latest_lift_pp"] = (rec["latest_redemption_rate"] - d0) * 100
        rows.append(rec)

    matrix = pd.DataFrame(rows).sort_values("click_date")
    return matrix


def build_recovery_strength(day_lag: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    rate_lookup = {
        (row["click_date"], int(row["lag_days"])): row["redemption_rate"]
        for _, row in day_lag.iterrows()
        if pd.notna(row["redemption_rate"])
    }
    detail_rows = []
    for _, row in day_lag[day_lag["lag_days"] >= 1].iterrows():
        lag = int(row["lag_days"])
        previous = rate_lookup.get((row["click_date"], lag - 1), np.nan)
        current = row["redemption_rate"]
        if pd.isna(previous) or pd.isna(current):
            continue
        recovery_date = row["click_date"] + pd.Timedelta(days=lag)
        marginal_pp = (current - previous) * 100
        detail_rows.append(
            {
                "recovery_date": recovery_date,
                "click_date": row["click_date"],
                "lag_days": lag,
                "previous_redemption_rate": previous,
                "current_redemption_rate": current,
                "marginal_lift_pp": marginal_pp,
            }
        )

    detail = pd.DataFrame(detail_rows)
    if detail.empty:
        return pd.DataFrame(), detail

    strength = (
        detail.groupby("recovery_date", as_index=False)
        .agg(
            covered_click_days=("click_date", "nunique"),
            diagonal_marginal_sum_pp=("marginal_lift_pp", "sum"),
            diagonal_marginal_avg_pp=("marginal_lift_pp", "mean"),
            diagonal_marginal_median_pp=("marginal_lift_pp", "median"),
            max_single_day_marginal_pp=("marginal_lift_pp", "max"),
        )
        .sort_values("recovery_date")
    )
    median = strength["diagonal_marginal_avg_pp"].median()
    q75 = strength["diagonal_marginal_avg_pp"].quantile(0.75)
    q90 = strength["diagonal_marginal_avg_pp"].quantile(0.90)
    strength["strength_level"] = np.select(
        [
            strength["diagonal_marginal_avg_pp"] >= q90,
            strength["diagonal_marginal_avg_pp"] >= q75,
            strength["diagonal_marginal_avg_pp"] >= median,
        ],
        ["极强", "强", "正常偏强"],
        default="正常",
    )
    return strength, detail.sort_values(["recovery_date", "lag_days"])


def add_event_features(strength: pd.DataFrame, event: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, row in strength.iterrows():
        date = row["recovery_date"]
        active = event[(event["start_date"] <= date) & (event["end_date"] >= date)]
        rec = row.to_dict()
        rec["active_events"] = "；".join(active["event_name"].tolist())
        rec["active_event_types"] = "；".join(sorted(active["event_type"].unique().tolist()))
        rec["has_s_level_event"] = bool((active["event_level"] == "S级").any())
        rec["has_promotion_incentive"] = bool((active["event_type"] == "推广激励").any())
        rec["days_from_nearest_event_start"] = np.nan
        if not active.empty:
            rec["days_from_nearest_event_start"] = int((date - active["start_date"]).dt.days.min())
        rows.append(rec)
    return pd.DataFrame(rows)


def build_event_bands(strength: pd.DataFrame, event: pd.DataFrame) -> pd.DataFrame:
    """Build non-overlapping activity bands for the timeline chart."""
    if strength.empty:
        return pd.DataFrame(columns=["start_date", "end_date", "start_label", "end_label", "label"])

    date_rows = []
    visible_dates = sorted(pd.to_datetime(strength["recovery_date"]).dropna().unique())
    key_events = event[event["event_type"].isin(["平台活动", "推广激励", "618节奏"])].copy()

    for date in visible_dates:
        active = key_events[(key_events["start_date"] <= date) & (key_events["end_date"] >= date)]
        label = ""
        if not active.empty:
            primary = active[active["event_type"].isin(["平台活动", "618节奏"])]["event_name"].tolist()
            has_incentive = (active["event_type"] == "推广激励").any()
            parts = primary[:1]
            if has_incentive:
                parts.append("推广激励")
            if not parts:
                parts = active["event_name"].tolist()[:1]
            label = " + ".join(parts)
        date_rows.append({"date": pd.Timestamp(date), "label": label})

    bands = []
    current_label = None
    start_date = None
    previous_date = None
    for row in date_rows:
        label = row["label"]
        date = row["date"]
        if not label:
            if current_label:
                bands.append({"start_date": start_date, "end_date": previous_date, "label": current_label})
            current_label = None
            start_date = None
            previous_date = None
            continue
        if label != current_label:
            if current_label:
                bands.append({"start_date": start_date, "end_date": previous_date, "label": current_label})
            current_label = label
            start_date = date
        previous_date = date
    if current_label:
        bands.append({"start_date": start_date, "end_date": previous_date, "label": current_label})

    result = pd.DataFrame(bands)
    if result.empty:
        return pd.DataFrame(columns=["start_date", "end_date", "start_label", "end_label", "label"])
    result["start_label"] = result["start_date"].dt.strftime("%m-%d")
    result["end_label"] = result["end_date"].dt.strftime("%m-%d")
    return result


def save_processed(
    base: pd.DataFrame,
    files: pd.DataFrame,
    day_lag: pd.DataFrame,
    matrix: pd.DataFrame,
    strength: pd.DataFrame,
    detail: pd.DataFrame,
    event: pd.DataFrame,
) -> None:
    PROCESSED_DIR.mkdir(exist_ok=True)
    base.to_csv(PROCESSED_DIR / "base_snapshot_long.csv", index=False, encoding="utf-8-sig")
    files.to_csv(PROCESSED_DIR / "source_file_summary.csv", index=False, encoding="utf-8-sig")
    day_lag.to_csv(PROCESSED_DIR / "day_lag_rate_summary.csv", index=False, encoding="utf-8-sig")
    matrix.to_csv(PROCESSED_DIR / "click_day_maturity_matrix.csv", index=False, encoding="utf-8-sig")
    strength.to_csv(PROCESSED_DIR / "recovery_day_strength.csv", index=False, encoding="utf-8-sig")
    detail.to_csv(PROCESSED_DIR / "diagonal_recovery_detail.csv", index=False, encoding="utf-8-sig")
    event.to_csv(PROCESSED_DIR / "event_calendar.csv", index=False, encoding="utf-8-sig")


def build_dashboard_payload(
    files: pd.DataFrame,
    matrix: pd.DataFrame,
    strength: pd.DataFrame,
    detail: pd.DataFrame,
    event: pd.DataFrame,
) -> dict[str, Any]:
    latest_snapshot = files["actual_snapshot_date"].max()
    latest_file = files.sort_values("actual_snapshot_date").iloc[-1]["source_file"]
    strongest = strength.sort_values("diagonal_marginal_avg_pp", ascending=False).iloc[0]
    recent_strength = strength.tail(7)
    latest_strength = strength[strength["recovery_date"] == latest_snapshot]
    latest_strength_row = latest_strength.iloc[0] if not latest_strength.empty else strength.iloc[-1]

    heatmap_rows = matrix[matrix["click_date"].notna()].copy()
    heatmap_rows = heatmap_rows.tail(45)
    y_dates = [d.strftime("%m-%d") for d in heatmap_rows["click_date"]]
    x_lags = [f"D{lag}" for lag in range(0, MAX_LAG + 1)]
    heatmap_data = []
    for yi, (_, row) in enumerate(heatmap_rows.iterrows()):
        for xi, lag_label in enumerate(x_lags):
            lag = int(lag_label[1:])
            value = row.get(f"D{lag}_redemption_rate")
            if pd.notna(value):
                maturity_date = row["click_date"] + pd.Timedelta(days=lag)
                heatmap_data.append([xi, yi, round(float(value) * 100, 2), maturity_date.strftime("%m.%d")])

    strength_plot = strength.copy()
    strength_plot = strength_plot[strength_plot["recovery_date"].notna()]
    strength_plot["date_label"] = strength_plot["recovery_date"].dt.strftime("%m-%d")
    strength_plot = strength_plot.tail(60)

    event_plot = event.copy()
    event_plot["start_label"] = event_plot["start_date"].dt.strftime("%m-%d")
    event_plot["end_label"] = event_plot["end_date"].dt.strftime("%m-%d")
    event_bands = build_event_bands(strength, event)

    strongest_date = strongest["recovery_date"]
    strongest_detail = detail[detail["recovery_date"] == strongest_date].copy()
    strongest_detail["share"] = strongest_detail["marginal_lift_pp"] / strongest_detail["marginal_lift_pp"].sum()
    strongest_detail = strongest_detail.sort_values("marginal_lift_pp", ascending=False).head(12)

    payload = {
        "meta": {
            "source_count": int(len(files)),
            "latest_source_file": latest_file,
            "latest_actual_snapshot_date": latest_snapshot.strftime("%Y-%m-%d"),
            "click_date_min": files["click_date_min"].min().strftime("%Y-%m-%d"),
            "click_date_max": files["click_date_max"].max().strftime("%Y-%m-%d"),
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "strongest_recovery_date": strongest_date.strftime("%Y-%m-%d"),
            "strongest_recovery_avg_pp": round(float(strongest["diagonal_marginal_avg_pp"]), 2),
            "latest_recovery_avg_pp": round(float(latest_strength_row["diagonal_marginal_avg_pp"]), 2),
            "recent_7d_avg_pp": round(float(recent_strength["diagonal_marginal_avg_pp"].mean()), 2),
        },
        "heatmap": {"x": x_lags, "y": y_dates, "data": heatmap_data},
        "strength": records_for_json(
            strength_plot[
                [
                    "recovery_date",
                    "date_label",
                    "diagonal_marginal_avg_pp",
                    "diagonal_marginal_sum_pp",
                    "diagonal_marginal_median_pp",
                    "max_single_day_marginal_pp",
                    "strength_level",
                    "active_events",
                    "has_s_level_event",
                    "has_promotion_incentive",
                ]
            ]
        ),
        "events": records_for_json(
            event_plot[["event_type", "event_name", "start_date", "end_date", "start_label", "end_label", "event_level"]]
        ),
        "eventBands": records_for_json(event_bands[["start_date", "end_date", "start_label", "end_label", "label"]]),
        "strongestDetail": records_for_json(
            strongest_detail[
                [
                    "recovery_date",
                    "click_date",
                    "lag_days",
                    "previous_redemption_rate",
                    "current_redemption_rate",
                    "marginal_lift_pp",
                    "share",
                ]
            ]
        ),
        "topRecoveryDays": records_for_json(
            strength.sort_values("diagonal_marginal_avg_pp", ascending=False)
            .head(15)[
                [
                    "recovery_date",
                    "diagonal_marginal_avg_pp",
                    "diagonal_marginal_sum_pp",
                    "max_single_day_marginal_pp",
                    "strength_level",
                    "active_events",
                ]
            ]
        ),
    }
    return payload


def dashboard_html(payload: dict[str, Any], data_link_prefix: str = "../data_processed") -> str:
    payload_json = json.dumps(payload, ensure_ascii=False)
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>淘联红包核销率回补跟踪</title>
  <script src="https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js"></script>
  <style>
    :root {{
      --text: #172033;
      --muted: #667085;
      --line: #d9dee8;
      --bg: #f7f8fb;
      --panel: #ffffff;
      --blue: #2563eb;
      --red: #dc2626;
      --orange: #f97316;
      --green: #059669;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
      color: var(--text);
      background: var(--bg);
      letter-spacing: 0;
    }}
    header {{
      padding: 22px 28px 14px;
      background: #fff;
      border-bottom: 1px solid var(--line);
    }}
    h1 {{ margin: 0 0 8px; font-size: 24px; font-weight: 750; }}
    .sub {{ color: var(--muted); font-size: 13px; }}
    main {{ padding: 20px 28px 32px; max-width: 1680px; margin: 0 auto; }}
    .kpis {{
      display: grid;
      grid-template-columns: repeat(5, minmax(150px, 1fr));
      gap: 12px;
      margin-bottom: 18px;
    }}
    .kpi {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 14px 16px;
      min-height: 82px;
    }}
    .kpi .label {{ color: var(--muted); font-size: 12px; margin-bottom: 8px; }}
    .kpi .value {{ font-size: 24px; font-weight: 760; white-space: nowrap; }}
    .grid {{
      display: grid;
      grid-template-columns: 1.45fr 1fr;
      gap: 16px;
      align-items: start;
    }}
    section {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 14px;
      margin-bottom: 16px;
    }}
    section h2 {{
      margin: 0 0 10px;
      font-size: 16px;
      font-weight: 720;
    }}
    .chart {{ width: 100%; height: 420px; }}
    #heatmap {{ height: 600px; }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 13px;
    }}
    th, td {{
      padding: 8px 9px;
      border-bottom: 1px solid #edf0f5;
      text-align: right;
      vertical-align: top;
      white-space: nowrap;
    }}
    th:first-child, td:first-child, th:nth-child(5), td:nth-child(5) {{ text-align: left; }}
    th {{ color: #475467; font-weight: 650; background: #fbfcfe; }}
    .note {{
      color: var(--muted);
      font-size: 12px;
      line-height: 1.6;
      margin-top: 8px;
    }}
    .links a {{ color: var(--blue); text-decoration: none; margin-right: 14px; }}
    @media (max-width: 1100px) {{
      .kpis {{ grid-template-columns: repeat(2, minmax(150px, 1fr)); }}
      .grid {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <header>
    <h1>淘联红包核销率回补跟踪</h1>
    <div class="sub">实际数据日 = 文件名日期 + 1天；点击日 = 表内日期；第一版不区分会场。</div>
  </header>
  <main>
    <div class="kpis">
      <div class="kpi"><div class="label">最新实际数据日</div><div class="value" id="latestDate"></div></div>
      <div class="kpi"><div class="label">最强回补日</div><div class="value" id="strongestDate"></div></div>
      <div class="kpi"><div class="label">最强均值</div><div class="value" id="strongestAvg"></div></div>
      <div class="kpi"><div class="label">近7日均值</div><div class="value" id="recentAvg"></div></div>
      <div class="kpi"><div class="label">CSV数量</div><div class="value" id="sourceCount"></div></div>
    </div>

    <div class="grid">
      <section>
        <h2>点击日核销率成熟热力图</h2>
        <div id="heatmap" class="chart"></div>
        <div class="note">颜色表示核销率百分比。每行是点击日，每列是成熟天数 D0-D14，共 15 天核销窗口。</div>
      </section>
      <div>
        <section>
          <h2>回补日强度</h2>
          <div id="strengthBar" class="chart"></div>
        </section>
        <section>
          <h2>最强回补日拆解</h2>
          <table id="detailTable"></table>
        </section>
      </div>
    </div>

    <section>
      <h2>回补强度与活动日历</h2>
      <div id="eventTimeline" class="chart"></div>
      <div class="note">柱状为回补日对角线边际均值；背景区间标记平台活动、推广激励和重点营销活动。</div>
    </section>

    <section>
      <h2>回补强度排行</h2>
      <table id="rankTable"></table>
    </section>

    <section class="links">
      <h2>数据文件</h2>
      <a href="{data_link_prefix}/base_snapshot_long.csv">base_snapshot_long.csv</a>
      <a href="{data_link_prefix}/click_day_maturity_matrix.csv">click_day_maturity_matrix.csv</a>
      <a href="{data_link_prefix}/recovery_day_strength.csv">recovery_day_strength.csv</a>
      <a href="{data_link_prefix}/diagonal_recovery_detail.csv">diagonal_recovery_detail.csv</a>
      <a href="{data_link_prefix}/event_calendar.csv">event_calendar.csv</a>
    </section>
  </main>

  <script>
    const payload = {payload_json};
    const fmtPct = v => v == null ? "NA" : (v * 100).toFixed(1) + "%";
    const fmtPp = v => v == null ? "NA" : (Number(v).toFixed(2) + "pp");
    const shortDate = d => d ? d.slice(5) : "";

    document.getElementById("latestDate").textContent = payload.meta.latest_actual_snapshot_date;
    document.getElementById("strongestDate").textContent = payload.meta.strongest_recovery_date;
    document.getElementById("strongestAvg").textContent = fmtPp(payload.meta.strongest_recovery_avg_pp);
    document.getElementById("recentAvg").textContent = fmtPp(payload.meta.recent_7d_avg_pp);
    document.getElementById("sourceCount").textContent = payload.meta.source_count;

    const heatmap = echarts.init(document.getElementById("heatmap"));
    heatmap.setOption({{
      tooltip: {{ formatter: p => {{
        const maturityDate = p.value[3] ? `（${{p.value[3]}}）` : "";
        return `${{payload.heatmap.y[p.value[1]]}} ${{payload.heatmap.x[p.value[0]]}}${{maturityDate}}<br/>核销率 ${{p.value[2].toFixed(2)}}%`;
      }} }},
      grid: {{ left: 62, right: 20, top: 20, bottom: 88 }},
      xAxis: {{ type: "category", data: payload.heatmap.x, splitArea: {{ show: true }}, axisLabel: {{ margin: 14 }} }},
      yAxis: {{ type: "category", data: payload.heatmap.y, splitArea: {{ show: true }} }},
      visualMap: {{
        min: 0,
        max: 55,
        calculable: true,
        orient: "horizontal",
        left: "center",
        bottom: 16,
        inRange: {{ color: ["#f7fbff", "#bfdbfe", "#60a5fa", "#2563eb", "#1e3a8a"] }}
      }},
      series: [{{ type: "heatmap", data: payload.heatmap.data, label: {{ show: false }}, emphasis: {{ itemStyle: {{ shadowBlur: 4, shadowColor: "rgba(0,0,0,.25)" }} }} }}]
    }});

    const strength = payload.strength;
    const dates = strength.map(d => d.date_label);
    const avg = strength.map(d => d.diagonal_marginal_avg_pp);
    const levelColor = level => level === "极强" ? "#dc2626" : level === "强" ? "#f97316" : level === "正常偏强" ? "#2563eb" : "#98a2b3";
    const strengthBar = echarts.init(document.getElementById("strengthBar"));
    strengthBar.setOption({{
      tooltip: {{ trigger: "axis", formatter: params => {{
        const idx = params[0].dataIndex;
        const row = strength[idx];
        return `${{row.date_label}}<br/>边际均值：${{row.diagonal_marginal_avg_pp.toFixed(2)}}pp<br/>边际合计：${{row.diagonal_marginal_sum_pp.toFixed(2)}}pp<br/>活动：${{row.active_events || "无"}}`;
      }} }},
      grid: {{ left: 52, right: 18, top: 20, bottom: 46 }},
      xAxis: {{ type: "category", data: dates, axisLabel: {{ rotate: 45 }} }},
      yAxis: {{ type: "value", name: "pp" }},
      series: [{{
        type: "bar",
        data: strength.map(d => ({{ value: d.diagonal_marginal_avg_pp, itemStyle: {{ color: levelColor(d.strength_level) }} }})),
        markLine: {{ data: [{{ type: "average", name: "均值" }}], lineStyle: {{ color: "#475467" }} }}
      }}]
    }});

    const eventTimeline = echarts.init(document.getElementById("eventTimeline"));
    const eventAreas = payload.eventBands.map(e => [
      {{ name: e.label, xAxis: e.start_label }},
      {{ xAxis: e.end_label }}
    ]);
    eventTimeline.setOption({{
      tooltip: {{ trigger: "axis", formatter: params => {{
        const idx = params[0].dataIndex;
        const row = strength[idx];
        return `${{row.date_label}}<br/>回补强度：${{row.diagonal_marginal_avg_pp.toFixed(2)}}pp<br/>活动：${{row.active_events || "无"}}`;
      }} }},
      grid: {{ left: 60, right: 28, top: 64, bottom: 52 }},
      xAxis: {{ type: "category", data: dates, axisLabel: {{ rotate: 45 }} }},
      yAxis: {{ type: "value", axisLabel: {{ formatter: "{{value}}pp" }} }},
      series: [{{
        name: "回补强度",
        type: "bar",
        data: avg,
        itemStyle: {{ color: "#2563eb" }},
        markArea: {{
          silent: true,
          itemStyle: {{ color: "rgba(249,115,22,0.13)" }},
          label: {{
            position: "insideTop",
            distance: 8,
            color: "#344054",
            fontSize: 12,
            overflow: "truncate",
            width: 180
          }},
          data: eventAreas
        }}
      }}, {{
        name: "趋势",
        type: "line",
        data: avg,
        smooth: true,
        symbolSize: 5,
        lineStyle: {{ color: "#111827", width: 2 }}
      }}]
    }});

    function renderTable(id, headers, rows) {{
      const html = [`<thead><tr>${{headers.map(h => `<th>${{h}}</th>`).join("")}}</tr></thead>`];
      html.push("<tbody>");
      rows.forEach(row => {{
        html.push(`<tr>${{row.map(cell => `<td>${{cell}}</td>`).join("")}}</tr>`);
      }});
      html.push("</tbody>");
      document.getElementById(id).innerHTML = html.join("");
    }}

    renderTable("detailTable",
      ["点击日", "lag", "前档", "当前", "边际", "占比"],
      payload.strongestDetail.map(r => [
        shortDate(r.click_date),
        "D" + r.lag_days,
        fmtPct(r.previous_redemption_rate),
        fmtPct(r.current_redemption_rate),
        fmtPp(r.marginal_lift_pp),
        r.share == null ? "NA" : (r.share * 100).toFixed(1) + "%"
      ])
    );

    renderTable("rankTable",
      ["回补日", "均值", "合计", "最大单日", "等级", "活动"],
      payload.topRecoveryDays.map(r => [
        r.recovery_date,
        fmtPp(r.diagonal_marginal_avg_pp),
        fmtPp(r.diagonal_marginal_sum_pp),
        fmtPp(r.max_single_day_marginal_pp),
        r.strength_level,
        r.active_events || ""
      ])
    );

    window.addEventListener("resize", () => {{
      heatmap.resize();
      strengthBar.resize();
      eventTimeline.resize();
    }});
  </script>
</body>
</html>
"""


def write_dashboard_sites(payload: dict[str, Any]) -> None:
    DASHBOARD_DIR.mkdir(exist_ok=True)
    ASSETS_DIR.mkdir(exist_ok=True)
    (DASHBOARD_DIR / "index.html").write_text(dashboard_html(payload), encoding="utf-8")

    if DOCS_DIR.exists():
        shutil.rmtree(DOCS_DIR)
    (DOCS_DIR / "data_processed").mkdir(parents=True)
    (DOCS_DIR / ".nojekyll").write_text("", encoding="utf-8")
    (DOCS_DIR / "index.html").write_text(dashboard_html(payload, data_link_prefix="data_processed"), encoding="utf-8")
    for path in sorted(PROCESSED_DIR.glob("*.csv")):
        shutil.copy2(path, DOCS_DIR / "data_processed" / path.name)


def build_dashboard() -> None:
    base, files = load_snapshot_base()
    event = build_event_calendar()
    day_lag = build_day_lag_summary(base)
    matrix = build_maturity_matrix(day_lag)
    strength, detail = build_recovery_strength(day_lag)
    strength = add_event_features(strength, event)

    save_processed(base, files, day_lag, matrix, strength, detail, event)

    payload = build_dashboard_payload(files, matrix, strength, detail, event)
    write_dashboard_sites(payload)

    print("dashboard built")
    print(f"source_csv_count: {len(files)}")
    print(f"latest_actual_snapshot_date: {payload['meta']['latest_actual_snapshot_date']}")
    print(f"strongest_recovery_date: {payload['meta']['strongest_recovery_date']}")
    print(f"strongest_recovery_avg_pp: {payload['meta']['strongest_recovery_avg_pp']}")
    print(f"processed_dir: {PROCESSED_DIR}")
    print(f"dashboard: {DASHBOARD_DIR / 'index.html'}")
    print(f"github_pages_docs: {DOCS_DIR}")


if __name__ == "__main__":
    build_dashboard()
