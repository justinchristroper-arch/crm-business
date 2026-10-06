from functools import lru_cache
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from backend.config import settings


def database_url(url):
    return url.replace('postgresql://', 'postgresql+psycopg://', 1)


@lru_cache
def engine():
    return create_engine(database_url(settings().database_url), poolclass=NullPool,
                         connect_args={'connect_timeout': 10}, hide_parameters=True)


def get_db():
    with sessionmaker(engine(), expire_on_commit=False)() as db:
        try:
            yield db
        except Exception:
            db.rollback()
            raise
