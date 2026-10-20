# Space 独立影音应用

来源：用户本机 REA/LibreTV，package.json 版本 2.16.12。保留上游 README 与完整 AGPL-3.0-or-later LICENSE，包含该本机副本已有的改动；未将它宣称为原封不动的官方发行版。

完整对应源码：https://github.com/ZuoyouAn/carbon-eye-release/tree/main/apps/libretv

本部署改动：浅色默认主题、Space 返回入口、对应源码链接、健康检查、损坏 Cookie 安全处理、收窄私网地址判断、单核构建，以及 Next.js 15.5.28 / PostCSS / source-map-js / sharp 安全补丁。它与 Vue 主站为独立程序，通过链接接入，不合并主站账号或数据库。

## 运行

要求 Node.js 22。执行 `npm ci`、`npm run typecheck`、`npm test`、`npm run build`。

Render：单独 Free Web Service，同一仓库 main 分支。

- Build：`cd apps/libretv && npm ci --include=dev && npm run build`
- Start：`cd apps/libretv && exec node --max-old-space-size=384 node_modules/next/dist/bin/next start --hostname 0.0.0.0 --port $PORT`
- 运行变量：PASSWORD（独立强密码）、PROXY_SECRET（独立随机密钥）、COOKIE_SECURE=true、NODE_VERSION=22、NEXT_TELEMETRY_DISABLED=1、LIVE_ALLOW_PRIVATE=0。
- 健康路径 `/healthz`，不请求外部视频源。不能开启生产自动登录。

不要复制 `.env.local`，不要提交密码或私密源。首次部署不预置任何影视/IPTV源；需要用户添加有权使用的接口。账号验证仅沿用 LibreTV 的独立共享访问密码，不是主站管理员密码。

## 免费与隐私边界

Free 实例会休眠；同工作区服务共享每月运行小时，带宽、构建与出网也有限额。已绑定付款方式时，额外带宽/构建可能产生费用，因此不要把此部署当作免费公共流媒体中转站。关注 Render Usage 与支出限制；不添加付费实例、数据库、磁盘或保活任务。

直播长连接和下载仍受资源、流量及上游可用性限制。不承诺所有数据源或所有视频可以播放，不绕过 DRM 或付费认证。

历史、收藏、配置和进度存于应用独立域名的本机 IndexedDB。服务重启不删除浏览器数据，但不会在设备或主站账号间云同步。搜索和部分代理播放会经过服务端；直连资源可能向第三方暴露 IP。发布源列表是公开上传，不要上传私密地址。

## 验收

本地测试覆盖类型检查、已有核心单元测试、新增部署回归、生产构建、密码验证及 Cookie、未登录 API、私网目标、主页与移动布局；上线后核对提交、状态接口与有效会话。以本次交付记录为准，不将未实测的第三方源报告为可用。
