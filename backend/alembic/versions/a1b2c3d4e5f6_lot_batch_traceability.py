"""lot_batch_traceability_schema

Revision ID: a1b2c3d4e5f6
Revises: 9c2d3e4f5a6b
Create Date: 2026-09-14 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '9c2d3e4f5a6b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create material_lots table
    op.create_table(
        'material_lots',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('organization_id', sa.String(length=36), nullable=False),
        sa.Column('product_id', sa.String(length=36), nullable=False),
        sa.Column('warehouse_id', sa.String(length=36), nullable=True),
        sa.Column('supplier_id', sa.String(length=36), nullable=True),
        sa.Column('lot_number', sa.String(length=100), nullable=False),
        sa.Column('received_quantity', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('current_quantity', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('unit_of_measure', sa.String(length=20), nullable=False, server_default='piece'),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='ACTIVE'),
        sa.Column('received_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('expiry_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('manufacturing_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['warehouse_id'], ['warehouses.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['supplier_id'], ['suppliers.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('organization_id', 'product_id', 'lot_number', name='uq_org_product_lot_number'),
    )
    op.create_index(op.f('ix_material_lots_organization_id'), 'material_lots', ['organization_id'], unique=False)
    op.create_index(op.f('ix_material_lots_product_id'), 'material_lots', ['product_id'], unique=False)
    op.create_index(op.f('ix_material_lots_warehouse_id'), 'material_lots', ['warehouse_id'], unique=False)
    op.create_index(op.f('ix_material_lots_supplier_id'), 'material_lots', ['supplier_id'], unique=False)
    op.create_index(op.f('ix_material_lots_lot_number'), 'material_lots', ['lot_number'], unique=False)
    op.create_index(op.f('ix_material_lots_status'), 'material_lots', ['status'], unique=False)
    op.create_index(op.f('ix_material_lots_created_at'), 'material_lots', ['created_at'], unique=False)

    # 2. Create work_order_lot_holdings table
    op.create_table(
        'work_order_lot_holdings',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('organization_id', sa.String(length=36), nullable=False),
        sa.Column('work_order_id', sa.String(length=36), nullable=False),
        sa.Column('lot_id', sa.String(length=36), nullable=False),
        sa.Column('product_id', sa.String(length=36), nullable=False),
        sa.Column('issued_quantity', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('consumed_quantity', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('returned_quantity', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('wastage_quantity', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('unit_of_measure', sa.String(length=20), nullable=False, server_default='piece'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['work_order_id'], ['work_orders.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['lot_id'], ['material_lots.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('organization_id', 'work_order_id', 'lot_id', name='uq_org_wo_lot_holding'),
    )
    op.create_index(op.f('ix_work_order_lot_holdings_organization_id'), 'work_order_lot_holdings', ['organization_id'], unique=False)
    op.create_index(op.f('ix_work_order_lot_holdings_work_order_id'), 'work_order_lot_holdings', ['work_order_id'], unique=False)
    op.create_index(op.f('ix_work_order_lot_holdings_lot_id'), 'work_order_lot_holdings', ['lot_id'], unique=False)
    op.create_index(op.f('ix_work_order_lot_holdings_product_id'), 'work_order_lot_holdings', ['product_id'], unique=False)
    op.create_index(op.f('ix_work_order_lot_holdings_created_at'), 'work_order_lot_holdings', ['created_at'], unique=False)

    # 3. Add lot_id to stock_transactions
    op.add_column('stock_transactions', sa.Column('lot_id', sa.String(length=36), nullable=True))
    op.create_foreign_key(
        'fk_stock_transactions_lot_id',
        'stock_transactions',
        'material_lots',
        ['lot_id'],
        ['id'],
        ondelete='SET NULL',
    )
    op.create_index(op.f('ix_stock_transactions_lot_id'), 'stock_transactions', ['lot_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_stock_transactions_lot_id'), table_name='stock_transactions')
    op.drop_constraint('fk_stock_transactions_lot_id', 'stock_transactions', type_='foreignkey')
    op.drop_column('stock_transactions', 'lot_id')

    op.drop_index(op.f('ix_work_order_lot_holdings_created_at'), table_name='work_order_lot_holdings')
    op.drop_index(op.f('ix_work_order_lot_holdings_product_id'), table_name='work_order_lot_holdings')
    op.drop_index(op.f('ix_work_order_lot_holdings_lot_id'), table_name='work_order_lot_holdings')
    op.drop_index(op.f('ix_work_order_lot_holdings_work_order_id'), table_name='work_order_lot_holdings')
    op.drop_index(op.f('ix_work_order_lot_holdings_organization_id'), table_name='work_order_lot_holdings')
    op.drop_table('work_order_lot_holdings')

    op.drop_index(op.f('ix_material_lots_created_at'), table_name='material_lots')
    op.drop_index(op.f('ix_material_lots_status'), table_name='material_lots')
    op.drop_index(op.f('ix_material_lots_lot_number'), table_name='material_lots')
    op.drop_index(op.f('ix_material_lots_supplier_id'), table_name='material_lots')
    op.drop_index(op.f('ix_material_lots_warehouse_id'), table_name='material_lots')
    op.drop_index(op.f('ix_material_lots_product_id'), table_name='material_lots')
    op.drop_index(op.f('ix_material_lots_organization_id'), table_name='material_lots')
    op.drop_table('material_lots')
