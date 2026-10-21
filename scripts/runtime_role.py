"""Provision a least-privilege SQL login. Run explicitly with migration credentials; never at startup."""
import argparse
import os
import secrets
from pathlib import Path
from sqlalchemy.engine import make_url
import psycopg
from psycopg import sql
from backend.config import settings

TABLES = ['users', 'auth_sessions', 'login_attempts', 'crm_config', 'companies', 'contacts',
          'leads', 'opportunities', 'tasks']


def configure_role(conn, role, password):
    identifier = sql.Identifier(role)
    exists = conn.execute('SELECT 1 FROM pg_roles WHERE rolname=%s', (role,)).fetchone()
    if exists:
        dangerous = conn.execute('SELECT rolsuper OR rolcreatedb OR rolcreaterole OR rolbypassrls '
                                 'FROM pg_roles WHERE rolname=%s', (role,)).fetchone()[0]
        memberships = conn.execute('SELECT 1 FROM pg_auth_members m JOIN pg_roles r ON r.oid=m.member '
                                   'WHERE r.rolname=%s LIMIT 1', (role,)).fetchone()
        owned = conn.execute('SELECT 1 FROM pg_class WHERE relowner=(SELECT oid FROM pg_roles WHERE rolname=%s) '
                             'LIMIT 1', (role,)).fetchone()
        if dangerous or memberships or owned:
            raise RuntimeError('Refusing an existing privileged role; choose a new dedicated runtime role.')
    else:
        conn.execute(sql.SQL('CREATE ROLE {} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS')
                     .format(identifier))
    conn.execute(sql.SQL('ALTER ROLE {} PASSWORD {}').format(identifier, sql.Literal(password)))
    conn.execute('REVOKE CREATE ON SCHEMA public FROM PUBLIC')
    conn.execute(sql.SQL('REVOKE ALL ON SCHEMA public FROM {}').format(identifier))
    conn.execute(sql.SQL('GRANT USAGE ON SCHEMA public TO {}').format(identifier))
    conn.execute(sql.SQL('GRANT CONNECT ON DATABASE {} TO {}')
                 .format(sql.Identifier(conn.info.dbname), identifier))
    conn.execute(sql.SQL('REVOKE ALL ON ALL TABLES IN SCHEMA public FROM {}').format(identifier))
    for table in TABLES:
        conn.execute(sql.SQL('GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.{} TO {}')
                     .format(sql.Identifier(table), identifier))
    conn.execute(sql.SQL('GRANT SELECT, INSERT ON TABLE public.audit_events TO {}').format(identifier))
    conn.execute(sql.SQL('ALTER ROLE {} SET statement_timeout = {}').format(identifier, sql.Literal('15s')))
    conn.execute(sql.SQL('ALTER ROLE {} SET idle_in_transaction_session_timeout = {}')
                 .format(identifier, sql.Literal('15s')))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default='.env.runtime.local')
    args = parser.parse_args()
    output = Path(args.output).resolve()
    root = Path.cwd().resolve()
    if output.parent != root or not output.name.startswith('.env.') or not output.name.endswith('.local'):
        raise RuntimeError('Write runtime credentials only to an ignored .env.*.local in the project root.')
    if output.exists():
        raise RuntimeError('Preserving existing runtime credentials. Reapply grants explicitly, do not rotate blindly.')
    owner_url = make_url(settings().migration_database_url or settings().database_url)
    runtime_url = make_url(settings().database_url)
    password = secrets.token_urlsafe(48)
    role = 'crm_runtime'
    with psycopg.connect(owner_url.set(drivername='postgresql').render_as_string(hide_password=False)) as conn:
        configure_role(conn, role, password)
    new_url = runtime_url.set(username=role, password=password).render_as_string(hide_password=False)
    descriptor = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, 'w', encoding='utf-8') as target:
        target.write('DATABASE_URL=' + new_url + '\n')
    print('Runtime role provisioned. Credentials saved privately; no secret values printed.')


if __name__ == '__main__':
    main()
