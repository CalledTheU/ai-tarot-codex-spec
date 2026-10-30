# API 参考

API 前缀：`/api/v1`。以实际 FastAPI OpenAPI Schema 为最终契约。

Phase 0–4 已实现公开牌库、认证、Reading 创建/详情和基础解读。历史列表、删除与 chat 尚未实现。健康接口位于根路径，不使用 `/api/v1` 前缀。

健康时返回 `200 {"status":"ok"}`。live 不依赖数据库；ready 执行数据库连接检查，失败返回 `503 DATABASE_UNAVAILABLE`，不验证迁移和种子是否完成。模型不参与健康检查。响应带 `X-Request-ID`，错误正文中的 `request_id` 与其一致，包括未处理异常的 500 响应。参数校验错误不回显输入，5xx 不向客户端暴露内部异常信息；HTTP 异常携带的 Retry-After 等响应头会保留。

## 已实现的牌库契约

- `GET /api/v1/cards`：返回 `{items: [...], total, page, page_size}`。默认 page=1、page_size=20；page_size 范围 1–100，page 范围 1–2147483647。越界页返回空 items 并保留实际 total。
- 可选过滤：`arcana_type=major|minor`、`suit=wands|cups|swords|pentacles`，过滤组合使用 AND。`q` 最多 100 字符，去除首尾空白后按中英文名称进行不区分英文大小写的字面子串搜索，`%`、`_` 不作为通配符。
- 排序固定为大/小阿尔卡那、花色、牌序、slug，翻页不会随机重排。摘要只返回 ID、slug、中英文名、分类、花色、等级、正逆位关键词与图片路径；不返回完整牌义和内部时间字段。
- `GET /api/v1/cards/{id_or_slug}`：返回摘要字段及 `upright_meaning`、`reversed_meaning`、`content_version`、`source_reference`。来源含章节、实际 URL、版权状态、版本、获取日期与 SHA-256；圣杯二另有 `reversed_url` 指向补充章节。牌义均为英文历史原文摘录。
- `GET /api/v1/spreads`：直接返回启用牌阵数组（不是分页对象）。每项为 `id, slug, name, description, positions, version`；positions 含 `index, name, description, x, y`。不返回管理字段 is_active。
- `GET /api/v1/spreads/{id_or_slug}`：返回同结构详情；停用牌阵与不存在的牌阵均返回 404。
- 以上接口均无需登录或模型配置。非法查询返回 422，不存在的资源返回 404，数据库不可用返回脱敏 503。OpenAPI 可在 `/docs` 查看。

## 认证（已实现）

`POST /auth/register` 接收 `{email,password}`，成功 201 只返回 `{id,email}`。邮箱规范化，密码 12–128 字符（不裁剪、不强制字符组合），采用 Argon2id。注册失败返回通用 400；登录失败统一 401，不区分邮箱不存在、停用或密码错误。多余字段被拒绝。

`POST /auth/login` 接收相同凭证，返回 `{access_token,token_type:"bearer",expires_in:1800}`（有效期可配置）。其他私有请求必须携带 `Authorization: Bearer <token>`。服务器只保存随机 token 的哈希，可即时撤销，不支持 Cookie。`GET /auth/me` 返回 `{id,email}`；`POST /auth/logout` 返回 204，撤销当前 token，重复退出同样为 204。

## Reading（已实现）

`POST /readings` 必须携带 `Idempotency-Key`，正文为 `{question,category,background?,spread_id}`，拒绝额外字段。question 去空白后 1–1000 字符，background 最多 5000；category 为 love/relationship/career/study/growth/other，spread_id 接受启用牌阵的 UUID 或 slug。幂等键为 1–128 个字母数字、下划线或连字符。同用户同键同参数返回相同结果，不同参数 409；相同键可用于不同用户。缺少键为 422。重放不会因牌阵后续停用而失败。

成功 201 返回 `{id,status,question,category,background,spread,cards,draw_metadata,interpretation,created_at}`。spread 是创建时配置与版本；cards 每项含 `card_id,name,position_index,position_name,orientation,card_snapshot`，card_snapshot 包含完整牌义、版本和来源。draw_metadata 包含 `algorithm=secrets-sample-v1` 和 UTC `drawn_at`，不含随机源状态。新记录 status 为 pending_interpretation、interpretation 为 null。

`GET /readings/{uuid}` 返回同结构，仅读取所有者记录；不存在和其他用户的记录均为 404，未登录/过期为 401。刷新详情可以恢复快照和已保存解读。私有响应禁止缓存。

## Interpret（已实现）

`POST /readings/{uuid}/interpret` 接收 `{style:"concise"|"detailed",include_sources:true|false}`，默认 detailed/true，可提交 `{}`。拒绝客户端牌面覆盖及其他字段。成功返回 `{reading_id,status:"completed",interpretation,sources,run_id}`，interpretation 结构见 SPEC §9。来源直接读取本记录快照，尚无额外 RAG 检索。每个来源编号由原来源 ID、牌 ID、方向和版本组成；sources 包含对应摘录、reference 与版本。`include_sources=false` 只隐藏响应 sources，不免除内部来源校验；快照仍保留来源。逆位单独来源 URL 会被正确使用。

Pydantic 通过后还须检查每牌恰好一次、ID/牌位/名称/方向不变、逐牌来源编号匹配，traditional_meaning 须与该方向的历史摘录逐字一致。缺字段、重复牌位、额外字段与伪造来源均失败。完成结果直接复用，修改 style 不会重新调用模型；没有开放重新生成语义。

状态：pending_interpretation/failed → processing → completed/failed。503 MODEL_UNAVAILABLE 表示无模型配置、超时、供应商或输出错误；失败保留原快照，显式重新 POST 即可重试。正在处理同记录返回 409；同用户其他运行、全局容量或频率限制为 429。超过模型超时加 30 秒的旧运行可恢复，迟到结果被 run_id 拦截。每请求最多一次模型调用，无隐式自动重试。事务在外部模型调用前提交。

默认频率：认证每 IP 每分钟 20；新抽牌每用户每分钟 10（幂等重放不计）；模型调用每用户每分钟 5（成功结果复用不计），同用户并发 1，全局每 worker 并发 2。配置见 `.env.example`。认证限流/全局并发为进程内机制，暂限单 worker；数据库里的用户互斥和频率计数使用 PostgreSQL 行锁。SQLite 仅作辅助测试。

## 全量路线图（历史列表、删除、chat 待实现）

| Method | Path | 说明 |
|---|---|---|
| POST | `/auth/register` | 注册 |
| POST | `/auth/login` | 登录 |
| POST | `/auth/logout` | 退出 |
| GET | `/auth/me` | 当前用户 |
| GET | `/cards` | 牌库分页与过滤 |
| GET | `/cards/{card_id_or_slug}` | 牌详情 |
| GET | `/spreads` | 牌阵列表 |
| GET | `/spreads/{spread_id_or_slug}` | 牌阵详情 |
| POST | `/readings` | 创建记录并抽牌 |
| GET | `/readings` | 当前用户历史 |
| GET | `/readings/{id}` | 详情 |
| POST | `/readings/{id}/interpret` | 生成/重试解读 |
| POST | `/readings/{id}/chat` | 追问 |
| DELETE | `/readings/{id}` | 删除 |
| GET | `/health/live` | 存活探针 |
| GET | `/health/ready` | 就绪探针 |

私有资源按当前身份校验所有权。错误统一返回 `{ "error": { "code": "...", "message": "...", "request_id": "..." } }`。分页默认 20，最大 100。创建 Reading 的 user_id 必须从认证上下文获取。
