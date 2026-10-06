from logging.config import fileConfig
from alembic import context
from sqlalchemy import create_engine, pool
from backend.models import Base
from backend.config import settings
from backend.db import database_url

fileConfig(context.config.config_file_name)
target_metadata = Base.metadata
url = database_url(settings().migration_database_url or settings().database_url)

if context.is_offline_mode():
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()
else:
    engine = create_engine(url, poolclass=pool.NullPool, hide_parameters=True)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()
