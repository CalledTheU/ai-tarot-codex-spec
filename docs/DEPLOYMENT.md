# 部署规格

当前完成 Phase 0–4 本地开发。PostgreSQL、Alembic 迁移与种子导入的实际命令见 README；Dockerfile、Compose、Nginx 与备份恢复仍为 Phase 8 目标，下述 Compose 命令当前不可执行。

## 开发环境
要求安装兼容版本的 Python、Node.js、Docker Engine/Desktop。具体版本由仓库依赖锁文件确定，并在 README 中写明实际验证版本。

## Docker Compose 服务
- `web`: Nginx 静态前端和 API 反向代理。
- `api`: FastAPI/Uvicorn。
- `db`: PostgreSQL；V1.1 启用 pgvector。
数据库仅加入内部网络，生产环境默认不发布数据库端口。

## 配置
`.env.example` 列出当前及后续配置。后端从进程环境变量读取，不自动加载 `.env`；PowerShell 设置方式见 README。后续部署可由容器环境注入；真实 `.env` 不得提交 Git。认证仅支持 `AUTH_MODE=bearer`，随机会话只存哈希，不使用 AUTH_SECRET/JWT；需迁移至 0003。模型服务必须由管理员实际提供，配置空缺时抽牌可用、解读返回 503。CORS/RAG 变量仍为后续占位，开发浏览器通过 Vite 同源代理访问 API。

当前使用单 API worker：认证 IP 限流和全局模型并发为进程内机制；多 worker/实例上线前须增加统一限流。用户级模型互斥与抽牌幂等使用 PostgreSQL 行锁；SQLite 仅作辅助测试。Bearer 在前端当前标签页 sessionStorage 保存，生产须 HTTPS 和 XSS 防护。临时验证容器的 trust 认证不能用于真实部署。

## 预期操作
```bash
docker compose up -d --build
docker compose exec api alembic upgrade head
docker compose exec api python -m app.scripts.seed_cards
docker compose ps
```
以上命令必须在实现后按真实入口校准并验证，不得仅复制到文档就宣称有效。

## 生产要求
- HTTPS、合理安全响应头。
- 容器非 root。
- 镜像版本固定。
- 数据库持久化卷和备份。
- 迁移作为单独步骤执行。
- 健康检查、日志轮转、限流、模型超时。
- 数据库不暴露公网。
- 备份恢复必须实际演练。
- 发布前运行数据库迁移、后端测试、前端测试和端到端测试。

## 备份
明确备份频率、保留周期、恢复点目标和负责人。至少验证一次从备份恢复到空数据库，并确认牌库、用户和历史数据可读取。
