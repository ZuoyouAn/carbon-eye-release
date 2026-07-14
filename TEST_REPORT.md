# Carbon Eye 测试报告

- 测试日期：2026-07-14
- 测试分支：`feature/carbon-eye-final-data-upgrade`

## 数据与质量

- `python scripts/build_carbon_eye_data.py`：通过。
  - 月度空气质量 152 条；2026-07 已标记为部分月。
  - 长期气象 151 个完整月；六点位日记录 27,570 条。
  - 园区用电官方记录 4 条，2020-2022 保持缺口。
  - 园区快照 6 点位、14 项因子、84 条记录。
  - 实验性 CDCI 记录 48 条，仅覆盖有年度能碳背景的 2019、2023、2024、2025。
- `python scripts/analyze_weather_air.py ...`：通过，输出 151 个重叠月份和 49 组相关性；包含 Pearson、Spearman、去季节 Pearson、样本量与“相关不等于因果”提示。
- `python scripts/validate_bundle.py`：通过，30 项质量检查全部通过。

## 后端

- `python -m py_compile ...`：通过。
- `python -m pytest -q`：5 通过，0 失败。
- FastAPI 本地烟雾测试：`/healthz` 及 9 个关键 Carbon Eye 静态接口全部返回 200。
- `realtime-aqi` 在未配置运行环境令牌时返回可读的 `unavailable` 状态，未导致 500。
- 缺失静态 JSON 的回归测试确认返回可读 503 和数据构建命令。
- 已知非阻塞警告：FastAPI 的 `on_event` 生命周期 API 已被标记为弃用；当前行为正确，后续可迁移到 lifespan。

## 前端

- `npm ci --cache ../.npm-cache`：通过。
- `npm run build`：通过。
- 无头浏览器检查：桌面端趋势图、长期气象图与相关矩阵均绘制成功；移动端标题和指标卡无重叠，宽表采用横向滚动。
- 构建警告：主 JavaScript 压缩后约 2.28 MB，比赛版可正常使用；后续可按路由拆分 ECharts 以进一步优化首屏体积。

## 内容边界

发布范围已搜索四类越界表述（过度碳核算、实时 CO2、确定交通来源、确定企业来源），均未发现。

安全审计结果见 `SECURITY_AUDIT.md`，科学边界见 `SCIENTIFIC_BOUNDARY_REPORT.md`。
