# AI Tarot

AI 塔罗牌解读与自我反思平台。当前仓库规格定义见 `SPEC.md`，Codex 工作规则见 `AGENTS.md`。

## 状态
Phase 0–4 已实现：工程骨架、数据库迁移、可追溯的 78 张牌与四种牌阵、公开牌库 API、认证与服务端抽牌、不可变快照、可替换模型适配器、结构化解读和前端页面。

Phase 3、4 分别执行测试，记录见 `docs/TESTING.md`。AI 验收使用 mock，不代表本机模型已安装或生成质量达标。LangGraph、RAG、历史列表/删除、多轮追问与生产部署尚未实现；下一步为 Phase 5。

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

后端健康检查：`http://127.0.0.1:8000/health/live` 不依赖数据库，`http://127.0.0.1:8000/health/ready` 检查连接，失败返回脱敏 503；不验证迁移和种子。后端只读取进程环境变量，不自动读取 `.env`。升级已有安装须重新安装 `requirements.lock`，并运行 `alembic upgrade head` 到 `0003`；不会删除现有记录。

另开终端启动前端：

```powershell
cd frontend
npm ci
npm run dev
```

打开 Vite 输出的本地地址，默认 `http://127.0.0.1:5173`。若 Windows 保留了该端口导致 EACCES，可使用 `npm run dev -- --port 15173`；本次 Docker 启动后使用 15173 验证成功。

Vite 默认将 `/api` 与 `/health` 代理到 `http://127.0.0.1:8000`。Windows 如保留了 8000 端口，后端改用 `--port 18000`；前端启动前设置 `$env:API_PROXY_TARGET='http://127.0.0.1:18000'`。本次浏览器联调用 18000/15173。页面采用哈希路由：`/#/account` 注册登录、`/#/new` 提交问题抽牌、`/#/readings/{id}` 恢复快照与解读。保存详情地址即可回看；历史列表留待 Phase 7。

## 资料与数据安全

牌义为 1918 年 *The Illustrated Key to the Tarot* 的可核对英文历史摘录，逐牌提供章节定位、版本、快照与摘录哈希。详见 `data/tarot_sources.md`。中文牌名是检索标签，尚无人工审核的中文牌义译文。没有引入未经许可的牌面图片；列表使用文字占位。

种子命令可重复执行，仅插入缺失条目，不覆盖已有数据。资料更新需要单独审核和显式迁移。Reading 创建在同一事务保存牌阵、牌义、来源版本、方向、牌位和抽牌算法时间；牌库更新不改变历史快照。未来删除沿用物理删除/子记录级联策略。

## 认证和抽牌

统一采用 `AUTH_MODE=bearer`；不接受 Cookie 认证。密码 12–128 字符，支持长口令，不强制字符组合，不裁剪密码；Argon2id 哈希。邮箱去空白/小写。登录返回随机 256-bit opaque token，数据库仅保存其 SHA-256，默认 30 分钟失效，退出即时撤销当前会话。前端将 token 存在当前标签页 sessionStorage，刷新可恢复，关闭标签页清除；需使用 HTTPS、防范 XSS，不要把 token 放在 URL。没有 JWT 签名密钥或跨域 Cookie/CSRF 混用。

创建 Reading 必须带 `Idempotency-Key`（1–128 位字母数字、下划线或连字符）。同用户同键同参数返回原记录；不同参数返回 409；重新抽牌须使用新键创建新记录。服务端使用 `secrets` 无放回抽牌，独立随机正逆位；客户端无法指定牌面、方向或 user_id。详情和 interpret 均按所有者校验，他人记录返回 404。

## 基础 AI 解读

`backend/app/llm.py` 的异步 `ModelAdapter` 可替换。内置适配器通过 HTTPX 调用 OpenAI 兼容的 `/chat/completions`，无自动下载、无内置生产 mock。按实际服务设置 `LLM_PROVIDER=openai_compatible`、`LLM_BASE_URL`（通常含 `/v1`）、`LLM_MODEL` 及可选 `LLM_API_KEY`。Qwen3-0.6B 可由兼容服务提供，但其安装、JSON 格式支持、上下文容量和质量尚未实测。

仅用户点击生成时发送问题、背景、牌面和对应方向的历史摘录，页面事先告知数据处理范围。系统提示词独立于不可信资料。输出经 Pydantic 与牌位/方向/来源一致性校验，历史牌义须逐字保留来源摘录；背景解释标为 AI 生成。没有模型配置时 interpret 返回 503，浏览、抽牌和快照仍可用。

一次请求只调用模型一次，不自动收费重试。失败状态允许显式重试原记录；已成功结果直接复用（风格修改不触发重新生成）。处理超时、无效 JSON、伪造引用；失败不改变快照。运行记录保存模型名、提示版本、耗时、安全错误码与可用 token 计数，不保存提示词、密码、密钥或原始错误。进程崩溃后，超过 `LLM_TIMEOUT_SECONDS + 30` 秒的运行可由原接口恢复；旧响应不能覆盖新运行。

默认每分钟限制：每 IP 认证 20 次、每用户新抽牌 10 次、每用户模型调用 5 次；同用户同时最多一个解读，每 API worker 全局最多两个模型调用，均可配置。认证 IP 限流与全局模型并发是进程内机制，目前按单 worker 使用；多实例统一限流与生产安全加固留在 Phase 8。RAG 与 LangGraph 尚未接入，来源来自本次快照中的结构化牌义。

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
