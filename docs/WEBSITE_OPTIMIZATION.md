# 页面优化与下一阶段

本次沿用 Vue 3 / FastAPI / Neon / Netlify / Render，不新增付费资源。

## 已实现

- 页面按路由加载；Element Plus 组件按需导入，不在首页加载图表与后台组件。
- 首页使用单次计数查询 `/api/site-summary`，不为统计下载小说正文或私密草稿。
- 移动导航折叠、键盘焦点、跳至正文、404、浏览器返回滚动位置、失败重试提示。
- `/store` 数字商品规划页：支持类型筛选与展开说明，没有价格、库存、收款、订单或兑换能力。
- HUMAN 3.0 区分尝试/持续性、压力差异与参照方式；追加按回答选择的追问。未知不算低分，不宣称临床有效或等同完整适应性访谈。

## 可选 AI：默认关闭

配置只能放 Render 后端私密环境变量，不能放 `VITE_*` 或 Git：

```dotenv
HUMAN3_AI_ENABLED=false
HUMAN3_AI_PROVIDER=doubao
HUMAN3_AI_MODEL=
HUMAN3_AI_API_KEY=
HUMAN3_AI_USER_DAILY_LIMIT=2
HUMAN3_AI_GLOBAL_DAILY_LIMIT=20
```

提供密钥后，确认供应商账户费用限制与隐私政策，再设置模型 ID 并显式启用。DeepSeek 模型 ID 以其控制台当前可用列表为准；豆包使用已开通模型的 Model ID / Endpoint ID。两者直接通过 FastAPI 兼容 Chat Completions 接口调用，不通过不支持这些供应商的 Netlify AI Gateway。

`GET /api/human3/ai-status` 不暴露密钥；`POST /api/human3/reflect` 要求登录、明确上传同意及完整合法的24个选项。仅发送选择和最多1600字补充，不上传浏览器生成的分类。AI文本以纯文本显示，不渲染HTML；不替代规则报告。

调用前数据库原子预占个人/全站 UTC 日额度，失败也扣次数，服务重启不会清空。只保存日期、配额范围和次数，不保存答案、提示词或AI回复。不重试，固定供应商URL、禁重定向、连接/读取超时、限制返回大小、错误脱敏。此次数限制是成本护栏，不等同人民币预算或供应商免费额度；启用前还应在供应商设置预算/免费额度用尽停服。单次900个输出token上限，默认显式关闭深度思考，避免思考占满短输出预算；豆包使用 `max_completion_tokens`，DeepSeek使用 `max_tokens`。需要选择支持这些参数的当前模型，提供密钥后再用所选真实模型验收。

建议先考察豆包试用额度，并在方舟确认“安心体验模式”及适用范围，用完即停。DeepSeek 官方 API 按 token 计费；聊天产品免费不等于 API 免费。本版本零模型调用费用来自规则版，而非虚构的永久免费模型。

官方资料：
- https://docs.volcengine.com/docs/ark/activation-management
- https://docs.volcengine.com/docs/ark/text-generation?lang=zh
- https://api-docs.deepseek.com/quick_start/pricing

## 卡密商业化下一阶段（本次未接入）

先确认商品正规授权、支付渠道、退款条款。后端需要商品/库存/订单/交付表，金额由后端计算、支付回调验签与幂等、支付完成再锁定库存扣减、卡密加密和唯一订单绑定、仅订单所有者可查看、日志脱敏及备份恢复。付费权益不得映射为网站管理员角色。当前规划页不收款、不收集购买信息。

## 验收

先运行 pytest、Node规则测试、前端生产构建、安全审计与隔离数据库的桌面/手机浏览器检查，通过后才发布现有 main 部署流水线。AI只使用模拟服务测试，本次不配置真实密钥、不产生推理费用。
