# 版本化资料

正式牌库与牌阵 JSON 随后端包分发，位置为 `backend/app/data/cards.json` 和 `spreads.json`。
来源、许可边界、章节定位与内容加工方式见 `tarot_sources.md`。英文原始快照保存在 `sources/`。

在仓库根目录执行 `backend/.venv/Scripts/python scripts/build_catalog.py` 可离线重建 78 张牌和四种项目定义的牌阵。此命令仅重建 JSON，不修改数据库。
迁移与导入命令见根目录 README。实际数据库导入入口为 `python -m app.scripts.seed_cards`（在 backend 内运行）。
