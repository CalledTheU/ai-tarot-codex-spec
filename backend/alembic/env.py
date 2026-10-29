# Author: WangLei
# Email: WangLei1578@outlook.com
# Date: 2026-10-29

from alembic import context
from app.config import settings
from app.database import create_db_engine
from app.models import Base

config = context.config
target_metadata = Base.metadata
url = config.get_main_option("sqlalchemy.url") or settings.database_url

if context.is_offline_mode():
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()
elif config.attributes.get("connection") is not None:
    context.configure(connection=config.attributes["connection"], target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()
else:
    engine = create_db_engine(url)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()
