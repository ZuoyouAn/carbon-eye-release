# personal-website

个人网站与“园区碳眼”专题演示系统。前端采用 Vue 3 + Vite，后端采用 FastAPI；原有文章、登录、留言与数据库功能保持独立，碳眼专题使用随代码发布的只读 JSON 数据，不依赖数据库即可访问。

## 园区碳眼

“园区碳眼”是面向苏州工业园区治理场景的减污降碳协同决策原型，采用“城市长期环境背景 + 园区官方短期监测快照 + 园区购电间接排放位置法代理估算”的多尺度结构。

它提供：

- 苏州市级空气质量长期趋势、相对异常与绝对污染压力；
- 六点位、七天、十四项特征因子的园区官方短期监测快照；
- 六点位 ERA5 气象空间平均与气象-污染描述性相关；
- 苏州市年度 CO2 背景；
- 园区购电间接排放位置法代理估算及宏观强度指标；
- 污染压力、能源活动和购电间接排放强度的三维协同态势；
- 实验性 CDCI 及权重敏感性结果；
- 产业画像和可追溯的规则型治理建议。

重要边界：城市空气质量用于区域环境背景，并不等同于园区内部连续监测；六点位数据是短期官方监测快照；购电结果仅覆盖购电间接排放位置法代理估算，不代表园区总排放或正式碳核算；气象模块只报告描述性相关。

## 目录

```text
backend/                       FastAPI 与专题静态数据
backend/data/carbon_eye/       Carbon Eye JSON、源数据与气象结果
frontend/                      Vue 专题页及原有网站页面
scripts/                       数据导入、构建、天气下载与质量校验
tests/                         后端与数据回归测试
docs/data_sources/             可公开分发的官方来源 PDF
```

## 本地运行

1. 安装后端依赖：`python -m pip install -r backend/requirements.txt`
2. 以专题独立模式启动后端：`$env:CARBON_EYE_STANDALONE='true'; python -m uvicorn main:app --app-dir backend --host 127.0.0.1 --port 8000`
3. 安装前端依赖并启动：`cd frontend; npm ci; npm run dev`
4. 浏览 `/projects` 后进入 `/carbon-eye`。

专题独立模式不初始化数据库；原网站完整模式沿用你本机的既有数据库配置和启动方式。

## 数据构建与校验

```powershell
python scripts/build_carbon_eye_data.py
python scripts/validate_bundle.py
python -m pytest -q
```

长期气象由 Open-Meteo ERA5 获取，使用六个园区官方点位并仅保留完整月份：

```powershell
python scripts/fetch_sip_weather.py --site-file backend/data/carbon_eye/sources/sip_monitoring_sites.csv --output-dir backend/data/carbon_eye/weather --model era5
python scripts/analyze_weather_air.py --air-json backend/data/carbon_eye/monthly_trends.json --weather-csv backend/data/carbon_eye/weather/weather_park_monthly.csv --output-dir backend/data/carbon_eye/weather
```

## 部署

`render.yaml` 部署 FastAPI，`netlify.toml` 部署 Vite 前端。生产环境需要在服务控制台配置：

- Render: `CORS_ORIGINS` 为 Netlify 网站地址；可选 `AQICN_TOKEN` 仅保存在 Render 环境变量中。
- Netlify: `VITE_API_BASE` 为 Render 后端地址。

首次完成 GitHub、Render、Netlify 的浏览器登录和环境变量设置后，推送默认发布分支即可触发持续部署。详见 `DEPLOYMENT_REPORT.md`。

## 主要数据来源

- 苏州工业园区统计开放平台；
- 苏州工业园区生态环境部门公开报告；
- 生态环境部区域电网平均二氧化碳排放因子；
- CEADs 城市年度碳排放清单；
- Open-Meteo ERA5 再分析数据。

具体 URL、时间尺度、许可和局限性见 `/api/carbon-eye/sources` 与专题页“方法、来源与边界”。
