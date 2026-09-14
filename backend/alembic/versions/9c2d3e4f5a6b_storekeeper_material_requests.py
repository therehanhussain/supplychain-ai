"""storekeeper_material_requests_schema

Revision ID: 9c2d3e4f5a6b
Revises: 8b1e2c3d4e5f
Create Date: 2026-09-14 10:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9c2d3e4f5a6b'
down_revision: Union[str, Sequence[str], None] = '8b1e2c3d4e5f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('material_requests', sa.Column('reviewed_by_user_id', sa.String(length=36), nullable=True))
    op.add_column('material_requests', sa.Column('rejection_reason', sa.String(length=255), nullable=True))
    op.add_column('material_requests', sa.Column('issued_transaction_id', sa.String(length=36), nullable=True))
    op.create_foreign_key(
        'fk_material_requests_reviewed_by_user_id',
        'material_requests',
        'users',
        ['reviewed_by_user_id'],
        ['id'],
        ondelete='SET NULL',
    )
    op.create_foreign_key(
        'fk_material_requests_issued_transaction_id',
        'material_requests',
        'stock_transactions',
        ['issued_transaction_id'],
        ['id'],
        ondelete='SET NULL',
    )
    op.create_index(
        op.f('ix_material_requests_reviewed_by_user_id'),
        'material_requests',
        ['reviewed_by_user_id'],
        unique=False,
    )
    op.create_index(
        op.f('ix_material_requests_issued_transaction_id'),
        'material_requests',
        ['issued_transaction_id'],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f('ix_material_requests_issued_transaction_id'), table_name='material_requests')
    op.drop_index(op.f('ix_material_requests_reviewed_by_user_id'), table_name='material_requests')
    op.drop_constraint('fk_material_requests_issued_transaction_id', 'material_requests', type_='foreignkey')
    op.drop_constraint('fk_material_requests_reviewed_by_user_id', 'material_requests', type_='foreignkey')
    op.drop_column('material_requests', 'issued_transaction_id')
    op.drop_column('material_requests', 'rejection_reason')
    op.drop_column('material_requests', 'reviewed_by_user_id')
