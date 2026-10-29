# Scripts

- `build_catalog.py`：从已保存的英文来源快照重建 78 张牌及四种牌阵 JSON；不访问网络或数据库。来源说明见 `data/tarot_sources.md`。
- 数据库种子入口：在 `backend` 内执行 `.venv/Scripts/python -m app.scripts.seed_cards`。先配置 `DATABASE_URL` 并运行 Alembic migration；导入在单个事务中执行，只插入缺失条目，不覆盖已有牌库、牌阵或用户数据。
