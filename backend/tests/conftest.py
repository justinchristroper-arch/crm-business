import os
from pathlib import Path
import pytest
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker
from alembic.config import Config as AlembicConfig
from alembic import command
from fastapi.testclient import TestClient

load_dotenv(Path(__file__).resolve().parents[2] / '.env')
test_url = os.environ.get('TEST_DATABASE_URL', '')
if not test_url or not make_url(test_url).database.endswith('_test'):
    raise RuntimeError('Set TEST_DATABASE_URL to a separate disposable PostgreSQL database ending in _test.')
os.environ['DATABASE_URL'] = test_url
os.environ['MIGRATION_DATABASE_URL'] = test_url
os.environ['APP_ENV'] = 'test'
os.environ['ALLOWED_ORIGINS'] = '["http://testserver"]'
os.environ['COOKIE_SECURE'] = 'false'
os.environ['DEMO_MODE'] = 'true'
os.environ['ENABLE_DEMO_RESET'] = 'true'

from backend.config import settings  # noqa: E402
settings.cache_clear()
from backend.auth import hasher  # noqa: E402
from backend.models import User, Config, Base  # noqa: E402
from backend.db import get_db, database_url  # noqa: E402
from backend.main import app  # noqa: E402

PASSWORD = 'PortfolioTest!2026'
HASH = hasher.hash(PASSWORD)
test_engine = create_engine(database_url(test_url), hide_parameters=True)
Factory = sessionmaker(test_engine, expire_on_commit=False)


@pytest.fixture(scope='session', autouse=True)
def migrated():
    command.upgrade(AlembicConfig('alembic.ini'), 'head')
    yield
    test_engine.dispose()


@pytest.fixture
def db(migrated):
    with test_engine.begin() as connection:
        names = ','.join('"'+table.name+'"' for table in Base.metadata.tables.values())
        connection.execute(text(f'TRUNCATE {names} RESTART IDENTITY CASCADE'))
    with Factory() as session:
        session.add(Config(id=1, risk_days=14))
        users = [('r1','Rep One','sales','Nusantara'), ('r2','Rep Two','sales','Nusantara'),
                 ('m1','Manager','manager','Nusantara'), ('a1','Admin','admin','Nusantara'),
                 ('r3','Outside Rep','sales','Bandung')]
        for id, name, role, team in users:
            session.add(User(id=id, email=f'{id}@example.com', name=name, role=role, team=team,
                             password_hash=HASH, demo=True))
        session.commit()
        yield session


@pytest.fixture
def clients(db):
    def dependency():
        with Factory() as session:
            try:
                yield session
            except Exception:
                session.rollback()
                raise
    app.dependency_overrides[get_db] = dependency
    opened = []
    def make(id='r1'):
        client = TestClient(app)
        response = client.post('/api/auth/login', json={'email': f'{id}@example.com', 'password': PASSWORD})
        assert response.status_code == 200, response.text
        client.headers['X-CSRF-Token'] = response.json()['csrf']
        opened.append(client)
        return client
    yield make
    for client in opened:
        client.close()
    app.dependency_overrides.clear()
