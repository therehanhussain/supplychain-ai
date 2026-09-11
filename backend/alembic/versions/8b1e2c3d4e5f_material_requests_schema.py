"""material_requests_schema

Revision ID: 8b1e2c3d4e5f
Revises: 7a8e9d0c1b2f
Create Date: 2026-09-11 23:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8b1e2c3d4e5f'
down_revision: Union[str, Sequence[str], None] = '7a8e9d0c1b2f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'material_requests',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('organization_id', sa.String(length=36), nullable=False),
        sa.Column('work_order_id', sa.String(length=36), nullable=False),
        sa.Column('product_id', sa.String(length=36), nullable=False),
        sa.Column('requested_by_user_id', sa.String(length=36), nullable=False),
        sa.Column('quantity', sa.Float(), nullable=False),
        sa.Column('unit_of_measure', sa.String(length=20), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='PENDING'),
        sa.Column('reason', sa.String(length=255), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['work_order_id'], ['work_orders.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['requested_by_user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_material_requests_organization_id'), 'material_requests', ['organization_id'], unique=False)
    op.create_index(op.f('ix_material_requests_work_order_id'), 'material_requests', ['work_order_id'], unique=False)
    op.create_index(op.f('ix_material_requests_status'), 'material_requests', ['status'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_material_requests_status'), table_name='material_requests')
    op.drop_index(op.f('ix_material_requests_work_order_id'), table_name='material_requests')
    op.drop_index(op.f('ix_material_requests_organization_id'), table_name='material_requests')
    op.drop_table('material_requests')
