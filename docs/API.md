# API 参考

API 前缀：`/api/v1`。以实际 FastAPI OpenAPI Schema 为最终契约。

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
