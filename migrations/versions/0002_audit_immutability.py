"""Protect audit history against ordinary UPDATE/DELETE, including application credentials."""
from alembic import op

revision = '0002_audit_immutability'
down_revision = '5c3be003b479'
branch_labels = None
depends_on = None


def upgrade():
    op.create_foreign_key('lead_opportunity_fk', 'leads', 'opportunities', ['opportunity_id'], ['id'])
    op.execute("""
        CREATE FUNCTION crm_protect_audit() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN RAISE EXCEPTION 'Audit events are immutable'; END; $$;
        CREATE TRIGGER crm_audit_immutable BEFORE UPDATE OR DELETE ON audit_events
        FOR EACH ROW EXECUTE FUNCTION crm_protect_audit();
    """)


def downgrade():
    op.execute('DROP TRIGGER crm_audit_immutable ON audit_events')
    op.execute('DROP FUNCTION crm_protect_audit()')
    op.drop_constraint('lead_opportunity_fk', 'leads', type_='foreignkey')
