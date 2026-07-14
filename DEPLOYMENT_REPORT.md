# Carbon Eye 部署报告

- 生成日期：2026-07-14
- 分支：`feature/carbon-eye-final-data-upgrade`
- 本地服务验证：通过。
- 线上发布状态：尚未执行。

## 已完成的部署准备

- `render.yaml`：后端根目录为 `backend`，构建命令为 `pip install -r requirements.txt`，启动命令为 `uvicorn main:app --host 0.0.0.0 --port $PORT`，健康检查为 `/healthz`。
- `netlify.toml`：前端根目录为 `frontend`，构建命令为 `npm ci && npm run build`，发布目录为 `dist`，已包含 SPA 路由重定向。
- 后端从 `CORS_ORIGINS` 读取跨域来源；前端从 `VITE_API_BASE` 读取 API 地址。
- 碳眼静态接口不依赖数据库；数据文件缺失时返回可读 503。

## 首次发布的控制台配置

1. Render 创建 Blueprint/Web Service 后，填写：
   - `CORS_ORIGINS=https://你的-Netlify-站点.netlify.app`
   - 可选 `CARBON_EYE_STANDALONE=true`，用于不连接数据库的专题独立演示。
   - 可选 `AQICN_TOKEN`，仅在 Render 环境变量中设置。
2. Netlify 创建站点后，填写：
   - `VITE_API_BASE=https://你的-Render-服务.onrender.com`
3. 再次触发两端部署，依次检查：
   - Render `/healthz`
   - Render `/api/carbon-eye/overview`
   - Netlify `/carbon-eye`
   - 浏览器刷新 `/carbon-eye`。

## 当前阻塞项

本机未检测到已认证的 `gh`、`netlify` 或 `render` CLI，且当前本地仓库未配置远程地址。因此本轮没有上传、创建服务或伪造线上 URL。

## 回滚

首次发布后可在 Render 或 Netlify 的 Deploys 页面选择上一个成功版本回滚。Git 侧可使用新的修复提交后重新推送；不建议对公开发布分支执行强制推送。
