from logging.config import fileConfig

from alembic import context

from score_system.infrastructure.db import database_url, make_engine
from score_system.infrastructure.orm import Base

if context.config.config_file_name is not None:
    fileConfig(context.config.config_file_name, disable_existing_loggers=False)

# Tests pass their own URL through the config; everything else uses DATABASE_URL.
url = context.config.get_main_option("sqlalchemy.url") or database_url()

if context.is_offline_mode():
    context.configure(url=url, target_metadata=Base.metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()
else:
    with make_engine(url).connect() as connection:
        context.configure(connection=connection, target_metadata=Base.metadata)
        with context.begin_transaction():
            context.run_migrations()
