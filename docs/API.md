# API 参考

API 前缀：`/api/v1`。以实际 FastAPI OpenAPI Schema 为最终契约。

Phase 2 已实现牌库与牌阵的四个公开 GET 接口，以及健康检查与统一错误响应。下表认证、Reading、解读与追问接口仍为计划，尚不可调用。健康接口位于根路径，不使用 `/api/v1` 前缀。

健康时返回 `200 {"status":"ok"}`。live 不依赖数据库；ready 执行数据库连接检查，失败返回 `503 DATABASE_UNAVAILABLE`，不验证迁移和种子是否完成。模型不参与健康检查。响应带 `X-Request-ID`，错误正文中的 `request_id` 与其一致，包括未处理异常的 500 响应。参数校验错误不回显输入，5xx 不向客户端暴露内部异常信息；HTTP 异常携带的 Retry-After 等响应头会保留。

## 已实现的牌库契约

- `GET /api/v1/cards`：返回 `{items: [...], total, page, page_size}`。默认 page=1、page_size=20；page_size 范围 1–100，page 范围 1–2147483647。越界页返回空 items 并保留实际 total。
- 可选过滤：`arcana_type=major|minor`、`suit=wands|cups|swords|pentacles`，过滤组合使用 AND。`q` 最多 100 字符，去除首尾空白后按中英文名称进行不区分英文大小写的字面子串搜索，`%`、`_` 不作为通配符。
- 排序固定为大/小阿尔卡那、花色、牌序、slug，翻页不会随机重排。摘要只返回 ID、slug、中英文名、分类、花色、等级、正逆位关键词与图片路径；不返回完整牌义和内部时间字段。
- `GET /api/v1/cards/{id_or_slug}`：返回摘要字段及 `upright_meaning`、`reversed_meaning`、`content_version`、`source_reference`。来源含章节、实际 URL、版权状态、版本、获取日期与 SHA-256；圣杯二另有 `reversed_url` 指向补充章节。牌义均为英文历史原文摘录。
- `GET /api/v1/spreads`：直接返回启用牌阵数组（不是分页对象）。每项为 `id, slug, name, description, positions, version`；positions 含 `index, name, description, x, y`。不返回管理字段 is_active。
- `GET /api/v1/spreads/{id_or_slug}`：返回同结构详情；停用牌阵与不存在的牌阵均返回 404。
- 以上接口均无需登录或模型配置。非法查询返回 422，不存在的资源返回 404，数据库不可用返回脱敏 503。OpenAPI 可在 `/docs` 查看。

## 全量路线图

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
