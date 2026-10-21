"""Start an explicitly migrated/seeded, loopback-only disposable E2E database/server."""
import os
import subprocess
import sys
from pathlib import Path
from dotenv import load_dotenv
import psycopg
from psycopg import sql
from sqlalchemy.engine import make_url

load_dotenv(Path(__file__).resolve().parents[1] / '.env')
source = make_url(os.environ['TEST_DATABASE_URL'])
if source.host not in ('localhost', '127.0.0.1') or not source.database.endswith('_test'):
    raise RuntimeError('E2E requires a disposable loopback PostgreSQL TEST_DATABASE_URL.')
target = source.set(database=source.database.removesuffix('_test') + '_e2e_test')
with psycopg.connect(source.set(drivername='postgresql').render_as_string(hide_password=False), autocommit=True) as conn:
    if not conn.execute('SELECT 1 FROM pg_database WHERE datname=%s', (target.database,)).fetchone():
        conn.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(target.database)))
url = target.render_as_string(hide_password=False)
os.environ.update(DATABASE_URL=url, MIGRATION_DATABASE_URL=url, APP_ENV='test', COOKIE_SECURE='false',
                  DEMO_MODE='true', ENABLE_DEMO_RESET='false', ALLOWED_ORIGINS='["http://127.0.0.1:8766"]')
for args in [['-m', 'alembic', 'upgrade', 'head'], ['-m', 'backend.seed']]:
    subprocess.run([sys.executable, *args], check=True)
subprocess.run([sys.executable, '-m', 'uvicorn', 'backend.main:app', '--host', '127.0.0.1', '--port', '8766'], check=True)
