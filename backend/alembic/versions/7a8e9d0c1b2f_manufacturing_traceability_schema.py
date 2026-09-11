"""manufacturing_traceability_schema

Revision ID: 7a8e9d0c1b2f
Revises: 49f3694a035f
Create Date: 2026-09-11 22:40:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7a8e9d0c1b2f'
down_revision: Union[str, Sequence[str], None] = '49f3694a035f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Extend products table with manufacturing metadata
    op.add_column('products', sa.Column('material_type', sa.String(length=50), nullable=False, server_default='RAW_MATERIAL'))
    op.add_column('products', sa.Column('unit_of_measure', sa.String(length=20), nullable=False, server_default='piece'))
    op.add_column('products', sa.Column('preferred_supplier_id', sa.String(length=36), nullable=True))
    op.create_foreign_key('fk_products_preferred_supplier_id', 'products', 'suppliers', ['preferred_supplier_id'], ['id'], ondelete='SET NULL')
    op.create_index(op.f('ix_products_material_type'), 'products', ['material_type'], unique=False)
    op.create_index(op.f('ix_products_preferred_supplier_id'), 'products', ['preferred_supplier_id'], unique=False)

    # 2. Extend inventories table with reorder foundation
    op.add_column('inventories', sa.Column('minimum_stock', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('inventories', sa.Column('average_daily_consumption', sa.Float(), nullable=False, server_default='0.0'))

    # 3. Create production_orders table
    op.create_table(
        'production_orders',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('organization_id', sa.String(length=36), nullable=False),
        sa.Column('order_number', sa.String(length=100), nullable=False),
        sa.Column('product_id', sa.String(length=36), nullable=False),
        sa.Column('planned_quantity', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('completed_quantity', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='PLANNED'),
        sa.Column('planned_start', sa.DateTime(timezone=True), nullable=True),
        sa.Column('planned_end', sa.DateTime(timezone=True), nullable=True),
        sa.Column('actual_start', sa.DateTime(timezone=True), nullable=True),
        sa.Column('actual_end', sa.DateTime(timezone=True), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('organization_id', 'order_number', name='uq_org_prod_order_number'),
    )
    op.create_index(op.f('ix_production_orders_created_at'), 'production_orders', ['created_at'], unique=False)
    op.create_index(op.f('ix_production_orders_organization_id'), 'production_orders', ['organization_id'], unique=False)
    op.create_index(op.f('ix_production_orders_order_number'), 'production_orders', ['order_number'], unique=False)
    op.create_index(op.f('ix_production_orders_product_id'), 'production_orders', ['product_id'], unique=False)
    op.create_index(op.f('ix_production_orders_status'), 'production_orders', ['status'], unique=False)

    # 4. Create work_orders table
    op.create_table(
        'work_orders',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('organization_id', sa.String(length=36), nullable=False),
        sa.Column('production_order_id', sa.String(length=36), nullable=False),
        sa.Column('work_order_number', sa.String(length=100), nullable=False),
        sa.Column('warehouse_id', sa.String(length=36), nullable=True),
        sa.Column('production_area', sa.String(length=100), nullable=True),
        sa.Column('assigned_user_id', sa.String(length=36), nullable=True),
        sa.Column('planned_quantity', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('completed_quantity', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='PLANNED'),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['assigned_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['production_order_id'], ['production_orders.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['warehouse_id'], ['warehouses.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('organization_id', 'work_order_number', name='uq_org_work_order_number'),
    )
    op.create_index(op.f('ix_work_orders_created_at'), 'work_orders', ['created_at'], unique=False)
    op.create_index(op.f('ix_work_orders_organization_id'), 'work_orders', ['organization_id'], unique=False)
    op.create_index(op.f('ix_work_orders_production_order_id'), 'work_orders', ['production_order_id'], unique=False)
    op.create_index(op.f('ix_work_orders_work_order_number'), 'work_orders', ['work_order_number'], unique=False)
    op.create_index(op.f('ix_work_orders_warehouse_id'), 'work_orders', ['warehouse_id'], unique=False)
    op.create_index(op.f('ix_work_orders_assigned_user_id'), 'work_orders', ['assigned_user_id'], unique=False)
    op.create_index(op.f('ix_work_orders_status'), 'work_orders', ['status'], unique=False)

    # 5. Create material_requirements table
    op.create_table(
        'material_requirements',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('organization_id', sa.String(length=36), nullable=False),
        sa.Column('production_order_id', sa.String(length=36), nullable=True),
        sa.Column('work_order_id', sa.String(length=36), nullable=True),
        sa.Column('product_id', sa.String(length=36), nullable=False),
        sa.Column('required_quantity', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('issued_quantity', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('consumed_quantity', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('returned_quantity', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('wastage_quantity', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('unit_of_measure', sa.String(length=20), nullable=False, server_default='piece'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['production_order_id'], ['production_orders.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['work_order_id'], ['work_orders.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_material_requirements_created_at'), 'material_requirements', ['created_at'], unique=False)
    op.create_index(op.f('ix_material_requirements_organization_id'), 'material_requirements', ['organization_id'], unique=False)
    op.create_index(op.f('ix_material_requirements_production_order_id'), 'material_requirements', ['production_order_id'], unique=False)
    op.create_index(op.f('ix_material_requirements_work_order_id'), 'material_requirements', ['work_order_id'], unique=False)
    op.create_index(op.f('ix_material_requirements_product_id'), 'material_requirements', ['product_id'], unique=False)

    # 6. Create stock_transactions table
    op.create_table(
        'stock_transactions',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('organization_id', sa.String(length=36), nullable=False),
        sa.Column('inventory_id', sa.String(length=36), nullable=False),
        sa.Column('product_id', sa.String(length=36), nullable=False),
        sa.Column('warehouse_id', sa.String(length=36), nullable=False),
        sa.Column('work_order_id', sa.String(length=36), nullable=True),
        sa.Column('production_order_id', sa.String(length=36), nullable=True),
        sa.Column('employee_id', sa.String(length=36), nullable=True),
        sa.Column('performed_by_user_id', sa.String(length=36), nullable=False),
        sa.Column('transaction_type', sa.String(length=50), nullable=False),
        sa.Column('quantity', sa.Float(), nullable=False),
        sa.Column('unit_of_measure', sa.String(length=20), nullable=False, server_default='piece'),
        sa.Column('reason', sa.String(length=255), nullable=True),
        sa.Column('source_location', sa.String(length=100), nullable=True),
        sa.Column('destination_location', sa.String(length=100), nullable=True),
        sa.Column('reference_type', sa.String(length=50), nullable=True),
        sa.Column('reference_id', sa.String(length=100), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['employee_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['inventory_id'], ['inventories.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['performed_by_user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['production_order_id'], ['production_orders.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['warehouse_id'], ['warehouses.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['work_order_id'], ['work_orders.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_stock_transactions_created_at'), 'stock_transactions', ['created_at'], unique=False)
    op.create_index(op.f('ix_stock_transactions_organization_id'), 'stock_transactions', ['organization_id'], unique=False)
    op.create_index(op.f('ix_stock_transactions_inventory_id'), 'stock_transactions', ['inventory_id'], unique=False)
    op.create_index(op.f('ix_stock_transactions_product_id'), 'stock_transactions', ['product_id'], unique=False)
    op.create_index(op.f('ix_stock_transactions_warehouse_id'), 'stock_transactions', ['warehouse_id'], unique=False)
    op.create_index(op.f('ix_stock_transactions_work_order_id'), 'stock_transactions', ['work_order_id'], unique=False)
    op.create_index(op.f('ix_stock_transactions_production_order_id'), 'stock_transactions', ['production_order_id'], unique=False)
    op.create_index(op.f('ix_stock_transactions_transaction_type'), 'stock_transactions', ['transaction_type'], unique=False)


def downgrade() -> None:
    op.drop_table('stock_transactions')
    op.drop_table('material_requirements')
    op.drop_table('work_orders')
    op.drop_table('production_orders')
    op.drop_column('inventories', 'average_daily_consumption')
    op.drop_column('inventories', 'minimum_stock')
    op.drop_constraint('fk_products_preferred_supplier_id', 'products', type_='foreignkey')
    op.drop_index(op.f('ix_products_preferred_supplier_id'), table_name='products')
    op.drop_index(op.f('ix_products_material_type'), table_name='products')
    op.drop_column('products', 'preferred_supplier_id')
    op.drop_column('products', 'unit_of_measure')
    op.drop_column('products', 'material_type')
