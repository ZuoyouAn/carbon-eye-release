# 完整个人网站部署：Netlify + Render + Neon

## 架构与边界

- Netlify 继续发布 `frontend/dist`，包含个人主页、文章、小说、帖子、留言、用户界面、所有项目和 HUMAN 3.0 测评。
- Render 继续运行 FastAPI。完整模式使用 `CARBON_EYE_STANDALONE=false`，不更换现有 API 地址。
- Neon 托管 PostgreSQL；网站写入的数据不依赖 Render 临时文件系统。
- HUMAN 3.0 当前是浏览器问卷与规则报告，不需要大模型 API，也不会将问卷答案上传到数据库。
- 不创建收费服务。免费服务有用量限制、冷启动和政策变更风险，不承诺永久免费或生产级可用性。

## 私密配置

复制仓库根目录 `.env.deploy.example` 为 `.env.deploy` 后填写 Neon 的 `DATABASE_URL`。真实配置被 Git 忽略，不要放进源码、前端变量、截图、日志或聊天。

Render 的现有后端服务需要设置：

| 环境变量 | 值 |
| --- | --- |
| `DATABASE_URL` | 从私密 `.env.deploy` 复制，不写入此文档 |
| `CARBON_EYE_STANDALONE` | `false` |
| `CORS_ORIGINS` | `https://carbon-eye-sip.netlify.app` |
| `SEED_DEMO_DATA` | `false` |

初次迁移保留原有密码哈希；三档权限版本通过用户明确配置的私密 `ADMIN_SETUP_PASSWORD` 一次性把旧 root 管理员改为 admin 并设置新密码，保留 ID 与内容。后续重启不重置现有 admin 密码，也不会自动提权普通账号。只有没有管理员时才可使用 `INITIAL_ADMIN_USERNAME` / `INITIAL_ADMIN_PASSWORD` 引导创建管理员。管理员新密码至少 12 位，详见 [权限说明](ROLE_PERMISSIONS.md)。对已经公开到聊天的 Neon 密码应立即轮换，然后同步更新私密配置和 Render 环境变量。

Netlify 的 `VITE_API_BASE` 保持 `https://personal-website-carbon-eye-api.onrender.com`。数据库密码绝不能以 `VITE_` 前缀注入前端。

## 数据迁移

```powershell
python scripts/migrate_website_database.py --source-env <本机后端.env> --target-env .env.deploy
python scripts/migrate_website_database.py --source-env <本机后端.env> --target-env .env.deploy --apply
```

- 默认只做只读预检；只有 `--apply` 才写目标库。
- 拒绝相同源/目标和任何非空目标，不提供清空或覆盖选项。
- 原 MySQL 保留，源只执行 SELECT。
- 迁移所有应用表和旧 `novel` 表，包括文章草稿、软删除记录及互动记录。
- 保留账号密码哈希，不复制 `auth_tokens`，上线后用户需要重新登录。
- PostgreSQL 事务内校验每张表的行数和完整内容哈希，再提交；重置自增序列，防止后续注册、发帖时主键冲突。
- 首次迁移前应暂停本机写入；迁移完成后以 Neon 为正式写入源。旧 MySQL 只用作回退，不能双向同时写入。
- 后续不要重复运行 `--apply`：目标库已经非空会拒绝执行。迁移回退不等于删除云端新产生的数据。

## 本次迁移校验（2026-10-04）

Neon 数据已复制并校验通过；此记录只表示数据层，不代表 Render 已完成切换。

| 表 | 源行数 | 目标行数 |
| --- | ---: | ---: |
| profile | 1 | 1 |
| articles | 2 | 2 |
| novel1 | 8 | 8 |
| novel（旧表） | 3850 | 3850 |
| users | 3 | 3 |
| yulu | 13 | 13 |
| messages | 3 | 3 |
| posts | 1 | 1 |
| article_comments | 3 | 3 |
| post_comments | 1 | 1 |
| article_likes / article_favorites / post_likes | 各 1 | 各 1 |
| novel_favorites / reading_progress | 各 1 | 各 1 |
| auth_tokens | 9 | 0（不迁移） |

连接 Neon 的本地 FastAPI 已验证 `/readyz`、资料、小说、文章、帖子、留言、语录均 HTTP 200；未登录管理员访问 HTTP 401。

## 发布与验收

1. 测试后推送 GitHub `main`，Render/Netlify 使用已有自动部署流程。
2. Render 配置上述环境变量并重新部署；保持现有免费实例，不创建 Render 的 30 天临时免费数据库。
3. 使用 Netlify 非生产预览核对新页面，再发布正式前端。
4. 线上 `GET /readyz` 必须返回 200；`/healthz` 必须显示 `website_mode=full`。
5. 验证所有只读内容、注册/登录、普通用户与管理员权限、发帖/留言、收藏/阅读进度；使用专用测试账号并清理测试记录，勿修改真实内容。
6. 重启后端后验证内容仍在，深链接刷新仍有效；检查真实浏览器的 CORS 和手机布局。

`/healthz` 是不查询数据库的存活检测，避免平台不断轮询让免费数据库无法休眠。`/readyz` 是按需查询数据库与资料的完整网站就绪检查，不能仅凭首页或专题 HTTP 200 宣称完整上线。

## 维护

- 在 Neon 控制台检查数据库与计算用量；保持 Free，不启用未批准的付费选项。
- 原本 MySQL 不是云端新增数据的备份。需要定期在可信设备用 `pg_dump` 备份 Neon，备份文件和密码同样禁止进入公开 Git。
- Render 空闲休眠后首次访问可能较慢。不要通过无意义定时访问绕过免费服务限制。
- 原线上版本可以从 Netlify/Render 部署历史回退；回退代码不会自动撤销数据库迁移或云端新增数据。
- 参考：[Neon 免费方案](https://neon.com/pricing)、[Neon SQLAlchemy](https://neon.com/docs/guides/sqlalchemy)、[Render 免费限制](https://render.com/docs/free)。
