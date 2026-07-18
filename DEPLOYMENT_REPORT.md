# Carbon Eye 线上部署与验证报告

- 更新日期：2026-07-18
- 应用分支：`main`
- 数据专业升级提交：`ccb44d8 feat: strengthen carbon eye data provenance`
- 源码仓库：[ZuoyouAn/carbon-eye-release](https://github.com/ZuoyouAn/carbon-eye-release)

## 已上线服务

| 服务 | 平台 | 地址 | 职责 |
| --- | --- | --- | --- |
| 前端 | Netlify | [carbon-eye-sip.netlify.app/carbon-eye](https://carbon-eye-sip.netlify.app/carbon-eye) | Vue 专题页面与静态资源 |
| 后端 | Render | [personal-website-carbon-eye-api.onrender.com](https://personal-website-carbon-eye-api.onrender.com) | FastAPI 只读接口与 Carbon Eye JSON 数据 |

Render 的 `rootDir` 为 `backend`，使用 `uvicorn main:app --host 0.0.0.0 --port $PORT` 启动；Netlify 的 `base` 为 `frontend`，构建命令为 `npm ci && npm run build`，并通过 SPA 重定向支持刷新 `/carbon-eye`。

## 2026-07-18 生产烟雾测试

| 检查项 | 结果 |
| --- | --- |
| Render `/healthz` | HTTP 200 |
| Render `/api/carbon-eye/overview` | HTTP 200 |
| Render `/api/carbon-eye/park-electricity-emissions` | HTTP 200；7 个年度槽位、3 个显式缺口 |
| Render `/api/carbon-eye/sources` | HTTP 200；12 项来源，S08 为已校验长期气象 |
| Netlify `/carbon-eye` | HTTP 200 |
| 本地 `python -m pytest tests/test_carbon_eye.py -q` | 6 通过 |
| 本地 `python -m py_compile backend/main.py` | 通过 |
| 本地 `frontend/npm.cmd run build` | 通过 |

## 部署逻辑和边界

两端均监听 GitHub `main` 分支。以后每次经过本地测试后推送 `main`，Render 与 Netlify 会各自自动构建并发布。Carbon Eye 静态接口不依赖 MySQL；个人网站的文章、登录、留言数据库能力没有作为本次专题独立部署的生产承诺。

免费 Render 实例会在无访问后休眠，首次访问可能出现约数十秒冷启动。比赛现场应提前访问健康检查，并准备离线录屏、PDF 和关键截图。Netlify 静态前端可持续提供服务，但平台的免费额度、域名和账户政策可能变化；本报告不承诺永久可用期。

## 环境变量和安全

- Netlify 使用 `VITE_API_BASE` 指向 Render 公网地址。
- Render 使用 `CORS_ORIGINS` 限制前端来源；`CARBON_EYE_STANDALONE` 允许专题静态接口独立运行。
- 可选 `AQICN_TOKEN` 只能在 Render 环境变量中配置，未写入源码、JSON、报告或 Git 历史。

## 回滚

1. 在 Netlify 或 Render 的 Deploys 页面选择上一条成功部署并执行回滚。
2. 如需代码级回滚，创建新的修复提交并推送 `main`；避免对已发布分支使用强制推送。
