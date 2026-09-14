"""StockTransaction repository providing tenant-isolated material movement queries."""
from typing import Optional, Sequence
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.models.stock_transaction import StockTransaction
from backend.app.repositories.base import BaseRepository


class StockTransactionRepository(BaseRepository[StockTransaction]):
    def __init__(self, session: AsyncSession):
        super().__init__(StockTransaction, session)

    async def get_by_id_and_org(
        self, transaction_id: str, organization_id: str
    ) -> Optional[StockTransaction]:
        """Fetch transaction ensuring tenant isolation with loaded relations."""
        result = await self.session.execute(
            select(StockTransaction)
            .options(
                selectinload(StockTransaction.product),
                selectinload(StockTransaction.warehouse),
                selectinload(StockTransaction.work_order),
                selectinload(StockTransaction.employee),
                selectinload(StockTransaction.performed_by_user),
                selectinload(StockTransaction.lot),
            )
            .where(
                StockTransaction.id == transaction_id,
                StockTransaction.organization_id == organization_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_by_org(
        self,
        organization_id: str,
        inventory_id: Optional[str] = None,
        product_id: Optional[str] = None,
        warehouse_id: Optional[str] = None,
        work_order_id: Optional[str] = None,
        production_order_id: Optional[str] = None,
        lot_id: Optional[str] = None,
        transaction_type: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[StockTransaction]:
        """List material transactions strictly scoped to tenant organization."""
        query = (
            select(StockTransaction)
            .options(
                selectinload(StockTransaction.product),
                selectinload(StockTransaction.warehouse),
                selectinload(StockTransaction.work_order),
                selectinload(StockTransaction.employee),
                selectinload(StockTransaction.performed_by_user),
                selectinload(StockTransaction.lot),
            )
            .where(StockTransaction.organization_id == organization_id)
        )
        if inventory_id:
            query = query.where(StockTransaction.inventory_id == inventory_id)
        if product_id:
            query = query.where(StockTransaction.product_id == product_id)
        if warehouse_id:
            query = query.where(StockTransaction.warehouse_id == warehouse_id)
        if lot_id:
            query = query.where(StockTransaction.lot_id == lot_id)
        if work_order_id:
            query = query.where(StockTransaction.work_order_id == work_order_id)
        if production_order_id:
            query = query.where(StockTransaction.production_order_id == production_order_id)
        if transaction_type:
            query = query.where(StockTransaction.transaction_type == transaction_type)

        query = query.order_by(StockTransaction.created_at.desc()).offset(skip).limit(limit)
        result = await self.session.execute(query)
        return result.scalars().all()
