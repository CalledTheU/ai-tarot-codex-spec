# AI Tarot

AI 塔罗牌解读与自我反思平台。当前仓库规格定义见 `SPEC.md`，Codex 工作规则见 `AGENTS.md`。

## 状态
Phase 0–2 已实现并分别验收：工程骨架、七张业务表与 Alembic 迁移、可追溯的 78 张牌、四种牌阵、幂等种子、公开牌库/牌阵 API，以及首页、牌库筛选分页、牌详情、牌阵选择与预览页面。

Phase 1 在真实 PostgreSQL 17.6 上通过独立测试；Phase 2 的 API、组件和真实浏览器联调记录见 `docs/TESTING.md`。认证、抽牌、AI、RAG、历史与生产部署尚未实现；下一步为 Phase 3。

## 本地启动
已验证环境：Python 3.11.9、Node.js 24.19.0、npm 11.17.0、PostgreSQL 17.6。后端 Python 依赖使用 `backend/requirements.lock` 锁定，前端使用 `frontend/package-lock.json`。

PowerShell 后端命令（在仓库根目录）：

```powershell
py -3.11 -m venv backend/.venv
cd backend
.venv/Scripts/python -m pip install -r requirements.lock
$env:DATABASE_URL = "postgresql+psycopg://tarot:change_me@127.0.0.1:5432/ai_tarot"
.venv/Scripts/python -m alembic upgrade head
.venv/Scripts/python -m app.scripts.seed_cards
.venv/Scripts/python -m uvicorn app.main:app --reload
```

运行以上命令前，须自行准备 PostgreSQL 数据库及有迁移权限的账户，按实际值修改示例连接串。不要对含有用户资料的数据库执行 `alembic downgrade base`，它会删除本项目业务表。启动时不会自动建表、迁移或导入种子。

后端健康检查：`http://127.0.0.1:8000/health/live` 不依赖数据库，`http://127.0.0.1:8000/health/ready` 会执行数据库连接检查，失败返回脱敏的 503。ready 检查连接可用性，不代表迁移与种子导入已经完成。模型配置使用根目录 `.env.example` 所列 `LLM_*` 环境变量；当前阶段不会调用模型，也不会自动读取 `.env` 文件。

另开终端启动前端：

```powershell
cd frontend
npm ci
npm run dev
```

打开 Vite 输出的本地地址，默认 `http://127.0.0.1:5173`。若 Windows 保留了该端口导致 EACCES，可使用 `npm run dev -- --port 15173`；本次 Docker 启动后使用 15173 验证成功。

Vite 将 `/api` 与 `/health` 代理到 `http://127.0.0.1:8000`；后端须在此端口启动。页面使用哈希路由，例如 `/#/cards`、`/#/cards/the-fool`、`/#/spreads`，详情与筛选可刷新恢复。无需配置模型即可浏览牌库与牌阵。

## 资料与数据安全

牌义为 1918 年 *The Illustrated Key to the Tarot* 的可核对英文历史摘录，逐牌提供章节定位、版本、快照与摘录哈希。详见 `data/tarot_sources.md`。中文牌名是检索标签，尚无人工审核的中文牌义译文。没有引入未经许可的牌面图片；列表使用文字占位。

种子命令可重复执行，仅插入缺失条目，不覆盖已有牌、牌阵、用户或 Reading。资料更新需要单独审核和显式迁移。Reading 及其子记录采用物理删除/数据库级联策略，当前还没有暴露私有读写接口。

## 模型接口预留

`backend/app/llm.py` 的 `ModelAdapter` 定义可替换的异步文本生成接口；配置读取位于 `backend/app/config.py`。当前仅预留接口与配置，没有模型实现、下载或连通性检查。`LLM_TIMEOUT_SECONDS` 与 `LLM_MAX_OUTPUT_TOKENS` 必须是正整数，API key 不出现在配置对象的 repr 中。

后续若本地 Qwen3-0.6B 通过 OpenAI 兼容服务提供接口，可配置 `LLM_PROVIDER=openai_compatible`、实际服务的 `LLM_BASE_URL` 和实际模型 ID `LLM_MODEL`。模型名称、端口、兼容性和硬件能力须在 Phase 4 实测；这些配置不代表本机已经安装模型。认证、CORS 和 RAG 配置项目前仅为后续阶段占位。

## 检查命令

```powershell
cd backend
.venv/Scripts/python -m ruff format --check .
.venv/Scripts/python -m ruff check .
.venv/Scripts/python -m pytest

cd ../frontend
npm run lint
npm run typecheck
npm test
npm run build
```

默认数据库测试使用临时 SQLite。真实 PostgreSQL 测试须设置专用 `TEST_DATABASE_URL`，测试自动创建/删除随机 schema，完整命令与结果见 `docs/TESTING.md`。在仓库根目录另可运行 `backend/.venv/Scripts/python -m ruff check backend scripts` 检查资料构建脚本。

## 开发流程
1. 阅读 `AGENTS.md` 和 `SPEC.md`。
2. 从 Phase 0 开始，完成一个阶段后运行测试。
3. 更新 API 文档、部署说明和阶段状态。
4. 不要把未实现功能标记为完成。

## 文档
- `SPEC.md`：完整产品和工程规格。
- `docs/IMPLEMENTATION_PLAN.md`：实施顺序和阶段验收。
- `docs/API.md`：API 契约摘要。
- `docs/AI_WORKFLOW.md`：LangGraph 与 RAG。
- `docs/TESTING.md`：测试规格。
- `docs/DEPLOYMENT.md`：部署与恢复。
