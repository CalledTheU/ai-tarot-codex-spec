# Author: WangLei
# Email: WangLei1578@outlook.com
# Date: 2026-10-29

import json

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from app.catalog_data import load_seed_data
from app.database import get_engine
from app.models import Spread, TarotCard


def seed_catalog(engine, directory=None):
    cards, spreads = load_seed_data(directory)
    insert = sqlite_insert if engine.dialect.name == "sqlite" else pg_insert
    counts = {}
    with engine.begin() as connection:
        for model, rows, name in ((TarotCard, cards, "cards"), (Spread, spreads, "spreads")):
            counts[name] = 0
            for row in rows:
                values = row.model_dump(mode="json")
                values["id"] = row.id
                result = connection.execute(
                    insert(model).values(**values).on_conflict_do_nothing().returning(model.id)
                )
                counts[name] += result.scalar_one_or_none() is not None
    return counts


if __name__ == "__main__":
    print(json.dumps(seed_catalog(get_engine())))
