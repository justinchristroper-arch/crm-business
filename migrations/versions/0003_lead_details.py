"""Preserve lead contact details through conversion."""
from alembic import op
import sqlalchemy as sa

revision = '0003_lead_details'
down_revision = '0002_audit_immutability'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('leads', sa.Column('phone', sa.String(80), nullable=False, server_default=''))
    op.add_column('leads', sa.Column('role', sa.String(120), nullable=False, server_default=''))


def downgrade():
    op.drop_column('leads', 'role')
    op.drop_column('leads', 'phone')
