# 部署规格

当前完成 Phase 0–2 本地开发。PostgreSQL、Alembic 迁移与种子导入的实际命令见 README；Dockerfile、Compose、Nginx 与备份恢复仍为 Phase 8 目标，下述 Compose 命令当前不可执行。

## 开发环境
要求安装兼容版本的 Python、Node.js、Docker Engine/Desktop。具体版本由仓库依赖锁文件确定，并在 README 中写明实际验证版本。

## Docker Compose 服务
- `web`: Nginx 静态前端和 API 反向代理。
- `api`: FastAPI/Uvicorn。
- `db`: PostgreSQL；V1.1 启用 pgvector。
数据库仅加入内部网络，生产环境默认不发布数据库端口。

## 配置
`.env.example` 列出当前及后续配置。当前应用从进程环境变量读取配置，不自动加载 `.env`；PowerShell 设置方式见 README。后续部署可由容器环境注入；真实 `.env` 不得提交 Git。AUTH_SECRET、认证、CORS 与模型尚未实现，不能将这些占位值当成生产安全配置。

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
