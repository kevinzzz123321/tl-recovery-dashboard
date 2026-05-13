# 淘联红包核销率回补跟踪

这个项目用于长期跟踪淘联点击日后续红包核销率回补，并把主站活动日历和真实回补强度放在同一套视图里。

## 核心口径

- 原始文件：根目录下所有 `YYYYMMDD.csv`
- 实际数据日 / 实际回补日：文件名日期 + 1 天
- 点击日：表内 `日期`
- 成熟天数：`lag_days = 实际数据日 - 点击日`
- 红包核销率：`红包使用量 / 红包量`
- 点击日成熟：横向看同一点击日的 `D0, D1, D2...`
- 淘联核销窗口：按 `D0-D14` 展示，共 15 个自然日
- 回补日强度：同一实际回补日的当天新增核销率，`Dk核销率 - D(k-1)核销率`

第一版先不区分会场，统一看全局核销率。

## 运行

```bash
/Users/jienmaike/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 build_dashboard.py
```

每日新增 CSV 后，重新执行上面的命令即可刷新 `data_processed/` 和 `dashboard/index.html`。

## 主要产物

- `data_processed/base_snapshot_long.csv`：清洗后的快照长表
- `data_processed/day_lag_rate_summary.csv`：点击日 x D天数的核销率汇总
- `data_processed/click_day_maturity_matrix.csv`：点击日成熟矩阵
- `data_processed/diagonal_recovery_detail.csv`：每天新增核销率来源明细
- `data_processed/recovery_day_strength.csv`：实际回补日强度排行
- `data_processed/event_calendar.csv`：活动日历结构化表
- `data_processed/main_site_calendar.csv`：5-6月主站重点活动日历，来自人工标注截图整理
- `dashboard/index.html`：本地可视化面板
- `docs/index.html`：GitHub Pages 发布页面
