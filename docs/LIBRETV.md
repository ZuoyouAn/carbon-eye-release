# 左右大人服务（基于 LibreTV）

2026-10-21 更新：品牌改为「左右大人服务」，新增 `/cinema` 异地同步放映厅及 `/ai-drama` 搜索发现页面；主站入口、导航和项目卡片同步更新。保留 AGPL 上游署名、许可证、原来的收藏历史存储及配置格式。功能原理、8 人权限规则、内存房间生命周期与验收方法见 [SPACE-CINEMA.md](../apps/libretv/SPACE-CINEMA.md)。不创建新收费服务、不改主站数据库，也不发布原工作区未提交的 GhostTrack 删除。

个人网站入口 `/libretv`（别名 `/tv`），在首页、项目和「更多」菜单均可打开。

当前交付状态：用户已明确授权创建和配置独立 Render Free 服务。服务 `zuoyou-space-libretv`（`srv-dbbo178n74is73db2mk0`，My Workspace，新加坡，Free）已上线，地址 https://zuoyou-space-libretv.onrender.com 。初始发布提交 `d5086a3bd07eb9912872e00a3e944b62d5381aff`，部署 `dep-dbbo180n74is73db2ong`。公网健康、独立密码登录、Secure/HttpOnly 会话、未登录访问拦截、私网目标拒绝和退出均已验证，入口已启用。没有预置或实测私人影视源，不把页面可达等同于所有第三方视频可播。

本地生产构建、327 项单测、类型检查、运行依赖审计（当次运行依赖报告 0 个已知漏洞）及桌面/390px 手机回归已通过。生产 HTTP 回归脚本为 `scripts/check_libretv_http.ps1`；凭据路径通过参数传入，仅发送到确认的服务域名，不打印密码、Cookie 或媒体地址。

PASSWORD 和 PROXY_SECRET 通过 Render 私密环境配置保存，主站管理员账号与 Neon 配置未改变。本机凭据文件 `.env.libretv-access` 留在原主站工作目录并被 Git 忽略，不上传、不共享。以后仅改入口或文档时可使用提交标记 `[skip render]` 避免无须的影音重建；若改了影音源码，必须正常重建并复核。

LibreTV 作为独立 Next.js 应用置于 `apps/libretv`，不在原 Vue 应用中嵌入播放器、不与 FastAPI 混合运行，也不共用主站管理员密码。入口会打开新标签页；播放器可返回 Space。

部署说明、对应源码与许可见 [apps/libretv/SPACE-DEPLOYMENT.md](../apps/libretv/SPACE-DEPLOYMENT.md) 和其目录内 LICENSE。

不会复制 REA/LibreTV 的完整真实 `.env.local`、node_modules、.next 或测试缓存。初始部署没有预置源；后续按用户要求，只将非凡、暴风、魔都、量子 4 个普通影视源复制到 Render `DEFAULT_SOURCES`，不修改其他环境变量，也不向仓库提交本机环境文件。未默认加入成人内容或用途未确认的其余源；未添加直播订阅。

默认源发布记录：部署 `dep-dbbob6favr4c73898q10` 已 live，线上 `/api/status` 返回 4 个源，源接口以测试关键词探活均成功；新浏览器首次导入后自动勾选。探活仅验证接口响应，不代表所有影片可播放；已手动取消勾选的源不会在刷新时强制重选。

为保留主站工作区已有未提交改动，本次代码在 `myATS/tmp/libretv-release` 隔离 Git 工作目录中准备；不撤销或发布原工作区中的 GhostTrack 删除改动。后续编辑前应先比对线上 main 与原工作目录。

浏览器回归脚本：`python scripts/check_libretv_browser.py --driver <msedgedriver.exe> --output <本机输出目录>`。服务测试使用独立临时密码，不在脚本中写生产密码。

若 Git HTTPS 传输被网络重置，而 GitHub CLI API 正常，可在审阅单个隔离提交后运行 `scripts/publish_libretv_via_github.ps1`。它只允许本功能范围、不支持删除、不强推、更新 main 前再次核对基线。正常情况下优先使用原生 git push。
