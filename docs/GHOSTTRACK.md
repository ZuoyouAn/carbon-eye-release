# GhostTrack 网站查询工作台

入口：网站“更多 → GhostTrack 查询”、首页快速入口、项目页，路由 `/ghosttrack`。
本次复核日期：2026-10-14。前端沿用 Vue/Vite，后端沿用 FastAPI；不创建额外数据库或付费服务。

## 原项目四项功能与原理

| 功能 | 实现 | 不能推断的内容 |
| --- | --- | --- |
| IP 归属 | 验证公网 IPv4/IPv6，后端以 HTTPS 查询 ipwho.is，显示地区、网络组织、ASN、时区和估计坐标 | 不是 GPS，不确认个人住址或实时位置 |
| 我的出口 IP | 用户主动点击后，浏览器请求 api.ipify.org，再填入 IP 输入框 | 只能看到当前网络公网出口，代理/VPN 会影响结果 |
| 号码规则解析 | 后端 phonenumbers/libphonenumber 离线号段元数据，解析国家码、格式、类型、可能地区和原始运营商 | 不查机主、开通状态、通讯记录或当前位置；携号转网可能改变运营商 |
| 公开用户名核对 | 用户名代入 19 个固定公开平台 URL，最多 6 个并发 GET，只读取 HTTP 状态，不跟随任意跳转 | 200 不等于真实账号存在，同名不代表同一个人；网络失败不等于不存在 |

原 CLI 的退出选项不需要作为网站功能。网页保留原理说明、来源链接、人工核对提示、结果清空及主动 JSON 下载。
不接入诱导定位链接、秘密定位、跨平台身份归并或私密资料抓取。

## 隐私与费用

号码会发送到本网站后端，但不会发送给外部号码数据商；“离线解析”不等于号码不经过网站服务器。
IP 会发送给 ipwho.is，用户名会发送给所列平台。外部服务及托管基础设施可能记录请求。
应用代码不保存查询值或结果到数据库、浏览器存储或应用日志；仅保留当前页面内存结果。
导出 JSON 是用户主动下载，可能包含查询值，需要自行保管。

ipwho.is 当前免费规则为每个客户端 IP 每日 1,000 次，无 SLA，网站后端出口可能共享额度。
额度超限明确返回 429，不自动切换付费服务；未来规则以官方文档为准。
后端入口每个直接访问端每分钟 8 次，全进程同时最多 3 个查询。
多实例/多 worker 不共享限流计数；扩容前应接入统一限流与可信代理身份规则。

来源：[GhostTrack](https://github.com/HunxByts/GhostTrack)、[号码解析](https://github.com/daviddrysdale/python-phonenumbers)、[IP 接口](https://ipwhois.io/documentation)。

## 运行和验收

前端：在 `frontend` 中 `npm run dev -- --host 127.0.0.1 --port 5178`。
后端：保留既有完整网站数据库配置，使用现有 Python 环境 `python -m uvicorn main:app --app-dir backend --host 127.0.0.1 --port 8000`。
只做隔离演示时才使用 `CARBON_EYE_STANDALONE=true` 与 `DATABASE_URL=sqlite:///:memory:`；不要替换生产配置。

首次连接免费 Render 后端可能较慢，页面允许最多 60 秒等待，并提供“重新连接”按钮。
健康状态成功不能证明所有外部平台可访问。每条用户名结果单独注明响应状态。

测试：`python -m pytest -q tests/test_ghosttrack.py tests/test_website_deployment.py tests/test_read_optimization.py`。
测试时在进程内明确设置内存 SQLite、独立模式、关闭演示数据，避免访问真实数据库。
后端的单元测试使用模拟外部响应和公开保留号码；真实服务验证仅使用公共 DNS IP 和公开示例用户名。
