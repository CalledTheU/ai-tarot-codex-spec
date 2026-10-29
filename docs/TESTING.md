# 测试规格

## Phase 2 验收与联调

API 测试覆盖分页/越界页、UUID 与 slug 详情、分类/花色、中英文搜索、字面通配符与 SQL 输入、非法参数、404、停用牌阵隐藏、公共字段裁剪及无模型配置访问。组件测试使用 React Testing Library、user-event 与 jsdom，覆盖首页入口、筛选分页、加载/错误/重试/空结果、正逆位和实际来源链接、牌阵选择及配置牌位、详情直达、过期请求取消、网络失败及空牌阵。

真实联调使用 Uvicorn → PostgreSQL 17.6，Vite `/api` 代理，以及 Edge（playwright-cli 0.1.21）。检查首页至牌库、20 项分页、中文搜索、正逆位详情与来源、详情刷新恢复、五张牌阵选择、五个配置牌位、牌阵详情刷新、花色过滤、空搜索和 390px 窄屏无页面横向溢出；联调脚本全部通过，未捕获 JavaScript pageerror。牌阵在窄屏内部横向滚动，完整牌位说明仍可阅读。

Windows 在 Docker 启动后拒绝绑定 5173（EACCES），因此实际前端联调使用 `npm run dev -- --port 15173 --strictPort`；不是将启动失败计为通过。最初 PostgreSQL 种子统计使用 rowcount 返回 -1 导致一项失败，修复为 RETURNING 后独立 Phase 1 测试全数通过。

以下为本次阶段验收命令（backend 内的 Python 命令使用 `.venv/Scripts/python`）：

| 阶段 | 命令 / 检查 | 结果 |
|---|---|---|
| Phase 1 | `pytest tests/test_config.py tests/test_health.py tests/test_database.py -q`，设置专用 TEST_DATABASE_URL | PostgreSQL 17.6：22 passed |
| Phase 1 | 同范围默认临时 SQLite | 22 passed |
| Phase 1 CLI | `alembic upgrade head`、`python -m app.scripts.seed_cards` 连续两次 | 迁移成功；首次 78/4，第二次 0/0 |
| Phase 2 | `pytest -q`，设置专用 TEST_DATABASE_URL | PostgreSQL 17.6：48 passed；默认临时 SQLite：48 passed |
| Phase 2 前端 | `npm test`、`npm run lint`、`npm run typecheck`、`npm run build` | 10 passed；lint、typecheck、build 全部通过 |
| 依赖与格式 | `pip install -r requirements.lock`、`pip check`、`npm ci`、Ruff format/check | 安装、依赖一致性及格式/lint 全部通过 |
| Phase 2 浏览器 | playwright-cli 驱动真实 Edge 与前后端 | 上述只读浏览流程通过 |

测试镜像为 `postgres:17.6`，获取摘要 `sha256:00bc86618629af00d2937fdc5a5d63db3ff8450acf52f0636ec813c7f4902929`。实例仅绑定本机临时端口，不使用已有数据库/卷；各测试使用随机 schema 隔离。联调用的 public schema 也仅存在于本次临时容器。验证后关闭临时服务和容器，不保留测试数据库。

仍未实现或未验证：注册/登录、抽牌、真实模型、RAG、私有 Reading API、完整业务 E2E、生产 Compose、备份恢复、其他浏览器与 Python 3.14。历史英文摘录已进行程序化来源比对，尚无人工审核的中文释义。既有 Starlette/AnyIO 弃用警告不影响本次测试通过；npm 仍提示 esbuild 安装脚本授权及 jsdom 的间接依赖弃用，未更改用户全局脚本授权设置。第一次最终 npm ci 因本次 Vite 验证进程占用 esbuild 而发生 EPERM；停止该进程后 npm ci 与全部前端检查重新运行并通过。

## Phase 1 验收范围

- 使用实际 Alembic 迁移创建七张业务表，重复 upgrade、downgrade/upgrade 往返及 ORM 元数据一致性测试。
- 78 张唯一牌、22/56 分类、每花色 14 个完整等级；四种牌阵的 1/3/3/5 连续牌位。全量数据与保存的历史来源快照重建结果比对，包括圣杯二的补充章节逆位定位。
- 重复 seed 返回零插入，保留数据库中修改过的牌名、牌阵启用状态与用户；无效牌库、摘录哈希或牌位在任何数据库写入前拒绝。
- 外键、重复牌与重复牌位、合法正逆位、规范化邮箱约束及 Reading 子记录级联删除。
- ready 检查数据库，故障返回脱敏 503；live 保持独立。

默认 `.venv/Scripts/python -m pytest` 使用临时 SQLite 文件验证通用逻辑，不代表 PostgreSQL 验收。提供独立测试数据库连接串后，可对真实 PostgreSQL 运行同一套测试：

```powershell
# 在 backend 目录，使用专用测试实例；账户必须可创建 schema。
$env:TEST_DATABASE_URL = "postgresql+psycopg://test_user:test_password@127.0.0.1:5432/test_tarot"
.venv/Scripts/python -m pytest
Remove-Item Env:TEST_DATABASE_URL
```

每项数据库测试创建随机独立 schema 并在结束时删除，不清理或修改 public schema。不要使用生产账户或生产实例进行测试。PostgreSQL 离线 SQL 编译测试仅验证 DDL 生成，不能替代真实实例的迁移、约束与幂等验证。

## Phase 0 历史验收记录（后续结果见本文开头）
- 后端：live/ready 返回、404/422/429/500/503 错误结构、request_id 一致性、错误信息脱敏及 Retry-After 保留；模型环境配置、可选模型配置、密钥 repr 隐藏、超时与输出上限校验。
- 前端：启动页静态渲染。
- 后续阶段再添加数据库、业务规则、AI 与端到端测试。

### 2026-10-29 实际验证

环境：Python 3.11.9、Node.js 24.19.0、npm 11.17.0。下列命令分别在 `backend`、`frontend` 目录执行：

| 范围 | 命令 | 结果 |
|---|---|---|
| 后端依赖 | `.venv/Scripts/python -m pip install -r requirements.lock` | 成功（复用已有虚拟环境，非全新环境验证） |
| 依赖一致性 | `.venv/Scripts/python -m pip check` | 无依赖冲突 |
| 后端格式 | `.venv/Scripts/python -m ruff format --check .` | 通过 |
| 后端 lint | `.venv/Scripts/python -m ruff check .` | 通过 |
| 后端测试 | `.venv/Scripts/python -m pytest` | 13 passed，1 项第三方弃用警告 |
| 前端依赖 | `npm ci` | 成功 |
| 前端格式和类型 | `npm run lint`、`npm run typecheck` | 通过 |
| 前端测试 | `npm test` | 1 passed |
| 前端构建 | `npm run build` | 通过 |
| HTTP 启动检查 | 临时端口启动真实 Uvicorn 和 Vite，检查 live/ready、首页与转换后的 React 模块 | 全部 200；完成后停止验证进程 |

已知警告：Starlette TestClient 使用 AnyIO 即将弃用的 `BlockingPortal` 别名。npm ci 提示 esbuild 安装脚本尚未授权；本机安装、Vite 启动和构建均成功，未更改用户 npm 脚本授权设置。

未运行：浏览器交互/视觉验收、Python 3.14 兼容性、数据库、真实模型、完整 E2E、Docker 和备份恢复。前端现有测试为服务端静态渲染，不能证明浏览器交互行为。Phase 0 ready 不检查数据库或模型，不能作为后续生产环境的完整就绪判断。

## 后端
- 单元：78 张牌完整性、抽牌数量、无重复、正逆位合法、牌阵配置校验。
- 数据库：唯一约束、外键、事务、迁移、幂等种子。
- API：参数边界、认证、权限、分页、统一错误格式。
- Agent：成功、超时、无效 JSON、缺字段、伪造牌面、伪造来源、修复失败。
- RAG：正逆位过滤、来源可追溯、重复内容去重、空结果处理。

## 前端
- 表单必填和长度限制。
- 请求加载、错误和重试状态。
- 防止重复提交。
- 牌位/正逆位显示。
- 历史记录刷新恢复。
- 认证过期行为。

## E2E
1. 注册/登录。
2. 选择牌阵并提交问题。
3. 后端创建 Reading。
4. 展示正确牌数和牌位。
5. 请求解读并显示结构化结果。
6. 追问。
7. 刷新后恢复记录。
8. 删除记录。
9. 验证其他用户不能访问该记录。

## 质量门槛
- 核心规则和权限测试必须通过。
- 牌位一致率、引用 ID 有效率目标为 100%。
- 至少 30 条人工审核的 AI 评估用例。
- 不报告未实际运行的测试为通过。
