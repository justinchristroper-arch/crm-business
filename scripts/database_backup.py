"""Offline pg_dump backup and guarded restore drill; no paid storage or scheduler."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
from sqlalchemy.engine import make_url
import psycopg
from backend.config import settings


def executable(name):
    configured = os.environ.get('CRM_POSTGRES_BIN')
    if configured:
        candidate = Path(configured) / (name + ('.exe' if os.name == 'nt' else ''))
        if not candidate.is_file():
            raise RuntimeError('CRM_POSTGRES_BIN does not contain the requested PostgreSQL client.')
        return str(candidate)
    found = shutil.which(name)
    if not found and os.name == 'nt':
        candidate = Path(r'C:\Program Files\PostgreSQL\17\bin') / (name + '.exe')
        found = str(candidate) if candidate.exists() else None
    if not found:
        raise RuntimeError('Install PostgreSQL client tools matching your server version.')
    return found


def pg_environment(url):
    env = os.environ.copy()
    env.update(PGHOST=url.host or 'localhost', PGPORT=str(url.port or 5432),
               PGDATABASE=url.database, PGUSER=url.username or '', PGPASSWORD=url.password or '')
    for key, value in url.query.items():
        if key == 'sslmode':
            env['PGSSLMODE'] = value
    return env


def run(args, url):
    result = subprocess.run(args, env=pg_environment(url), capture_output=True)
    if result.returncode:
        Path('artifacts/pg-client-diagnostic.log').write_bytes(result.stderr)
        raise RuntimeError('PostgreSQL client operation failed; credentials/raw diagnostics withheld.')


def backup(output):
    url = make_url(settings().migration_database_url or settings().database_url).set(drivername='postgresql')
    root = (Path.cwd() / 'artifacts').resolve()
    output = Path(output).resolve()
    if not output.is_relative_to(root) or output.exists():
        raise RuntimeError('Choose a new backup file inside ignored artifacts/. Existing backups are preserved.')
    output.parent.mkdir(parents=True, exist_ok=True)
    with psycopg.connect(url.render_as_string(hide_password=False)) as conn:
        conn.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
        snapshot = conn.execute('SELECT pg_export_snapshot()').fetchone()[0]
        run([executable('pg_dump'), '--format=custom', '--snapshot=' + snapshot, '--file=' + str(output)], url)
        revision = conn.execute('SELECT version_num FROM alembic_version').fetchone()[0]
    manifest = {'sha256': hashlib.sha256(output.read_bytes()).hexdigest(), 'revision': revision,
                'format': 'pg_dump_custom', 'credentials_in_manifest': False}
    output.with_suffix(output.suffix + '.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print('Database backup and checksum manifest created in ignored artifacts/. Protect this file as sensitive data.')


def restore(archive, target_url):
    target = make_url(target_url).set(drivername='postgresql')
    if target.host not in ('localhost', '127.0.0.1') or not target.database.endswith('_restore_test'):
        raise RuntimeError('Restore is restricted to an empty loopback database ending _restore_test.')
    archive = Path(archive).resolve()
    manifest = json.loads(archive.with_suffix(archive.suffix + '.json').read_text(encoding='utf-8'))
    if hashlib.sha256(archive.read_bytes()).hexdigest() != manifest['sha256']:
        raise RuntimeError('Archive checksum mismatch.')
    with psycopg.connect(target.render_as_string(hide_password=False)) as conn:
        if conn.execute("SELECT 1 FROM information_schema.tables WHERE table_schema='public' LIMIT 1").fetchone():
            raise RuntimeError('Restore target is not empty; refusing to overwrite any data.')
    run([executable('pg_restore'), '--no-owner', '--no-privileges', '--exit-on-error', '--single-transaction',
         '--dbname=' + target.database, str(archive)], target)
    with psycopg.connect(target.render_as_string(hide_password=False)) as conn:
        revision = conn.execute('SELECT version_num FROM alembic_version').fetchone()[0]
        assert revision == manifest['revision']
        print('Restore drill verified:', revision, '; audit rows:', conn.execute('SELECT count(*) FROM audit_events').fetchone()[0])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    create = commands.add_parser('backup')
    create.add_argument('--output', required=True)
    drill = commands.add_parser('restore-drill')
    drill.add_argument('--archive', required=True)
    args = parser.parse_args()
    if args.command == 'backup':
        backup(args.output)
    else:
        restore(args.archive, os.environ['RESTORE_TEST_DATABASE_URL'])
