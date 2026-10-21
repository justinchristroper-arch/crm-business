import psycopg
import pytest
from scripts.runtime_role import configure_role


def test_runtime_has_no_owner_ddl_or_audit_mutation_permissions(db):
    owner = db.get_bind().url.set(drivername='postgresql')
    role = 'crm_runtime_permission_test'
    password = 'LocalDisposableRole!2026'
    with psycopg.connect(owner.render_as_string(hide_password=False)) as conn:
        configure_role(conn, role, password)
    runtime = owner.set(username=role, password=password)
    with psycopg.connect(runtime.render_as_string(hide_password=False)) as conn:
        flags = conn.execute("""SELECT
            has_schema_privilege(current_user,'public','CREATE'),
            has_table_privilege(current_user,'audit_events','UPDATE'),
            has_table_privilege(current_user,'audit_events','DELETE'),
            has_table_privilege(current_user,'audit_events','TRUNCATE'),
            has_table_privilege(current_user,'audit_events','SELECT'),
            has_table_privilege(current_user,'audit_events','INSERT')""").fetchone()
        assert flags == (False, False, False, False, True, True)
    for statement in ['TRUNCATE audit_events', 'ALTER TABLE audit_events DISABLE TRIGGER crm_audit_immutable',
                      'CREATE TABLE public.forbidden_runtime_table (id int)']:
        with psycopg.connect(runtime.render_as_string(hide_password=False)) as conn:
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                conn.execute(statement)
            conn.rollback()
