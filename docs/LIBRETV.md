# LibreTV 接入

个人网站入口 `/libretv`（别名 `/tv`），在首页、项目和「更多」菜单均可打开。

LibreTV 作为独立 Next.js 应用置于 `apps/libretv`，不在原 Vue 应用中嵌入播放器、不与 FastAPI 混合运行，也不共用主站管理员密码。入口会打开新标签页；播放器可返回 Space。

部署说明、对应源码与许可见 [apps/libretv/SPACE-DEPLOYMENT.md](../apps/libretv/SPACE-DEPLOYMENT.md) 和其目录内 LICENSE。

不会复制 REA/LibreTV 的真实 `.env.local`、node_modules、.next 或测试缓存。初始不预置影视/直播源。

为保留主站工作区已有未提交改动，本次代码在 `myATS/tmp/libretv-release` 隔离 Git 工作目录中准备；不撤销或发布原工作区中的 GhostTrack 删除改动。后续编辑前应先比对线上 main 与原工作目录。

浏览器回归脚本：`python scripts/check_libretv_browser.py --driver <msedgedriver.exe> --output <本机输出目录>`。服务测试使用独立临时密码，不在脚本中写生产密码。

若 Git HTTPS 传输被网络重置，而 GitHub CLI API 正常，可在审阅单个隔离提交后运行 `scripts/publish_libretv_via_github.ps1`。它只允许本功能范围、不支持删除、不强推、更新 main 前再次核对基线。正常情况下优先使用原生 git push。
