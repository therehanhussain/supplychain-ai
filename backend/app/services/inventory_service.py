"""Inventory domain service executing real persistence and tenant isolation."""
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.models.inventory import Inventory
from backend.app.models.product import Product
from backend.app.models.warehouse import Warehouse
from backend.app.repositories.inventory import InventoryRepository
from backend.app.schemas.inventory import InventoryItemCreate, InventoryItemResponse
from backend.app.core.exceptions import AppException


class InventoryService:
    def __init__(self, db: AsyncSession, organization_id: str):
        self.db = db
        self.organization_id = organization_id
        self.repo = InventoryRepository(db)

    async def list_inventory(
        self,
        warehouse_id: Optional[str] = None,
        low_stock_only: bool = False,
        skip: int = 0,
        limit: int = 100,
    ) -> List[InventoryItemResponse]:
        """List tenant-owned inventory records."""
        items = await self.repo.list_by_org(
            organization_id=self.organization_id,
            warehouse_id=warehouse_id,
            low_stock_only=low_stock_only,
            skip=skip,
            limit=limit,
        )
        return [
            InventoryItemResponse(
                id=item.id,
                sku=item.product.sku if item.product else "UNKNOWN-SKU",
                name=item.product.name if item.product else "Item",
                category=item.product.category if item.product else "General",
                quantity_on_hand=float(item.quantity),
                quantity_reserved=0.0,
                reorder_point=float(item.reorder_point),
                unit_cost=float(item.product.unit_cost) if item.product else 0.0,
                warehouse_id=item.warehouse.code if item.warehouse else item.warehouse_id,
                is_low_stock=item.quantity <= item.safety_stock,
                updated_at=item.updated_at,
            )
            for item in items
        ]

    async def get_inventory(self, inventory_id: str) -> InventoryItemResponse:
        """Fetch inventory record ensuring tenant ownership."""
        item = await self.repo.get_by_id_and_org(inventory_id, self.organization_id)
        if not item:
            raise AppException(
                message=f"Inventory item '{inventory_id}' not found.",
                status_code=404,
                error_code="INVENTORY_NOT_FOUND",
            )
        return InventoryItemResponse(
            id=item.id,
            sku=item.product.sku if item.product else "UNKNOWN-SKU",
            name=item.product.name if item.product else "Item",
            category=item.product.category if item.product else "General",
            quantity_on_hand=float(item.quantity),
            quantity_reserved=0.0,
            reorder_point=float(item.reorder_point),
            unit_cost=float(item.product.unit_cost) if item.product else 0.0,
            warehouse_id=item.warehouse.code if item.warehouse else item.warehouse_id,
            is_low_stock=item.quantity <= item.safety_stock,
            updated_at=item.updated_at,
        )

    async def create_inventory(self, payload: InventoryItemCreate) -> InventoryItemResponse:
        """Create or register new inventory item under tenant."""
        # Find or create warehouse
        wh_result = await self.db.execute(
            select(Warehouse).where(
                Warehouse.organization_id == self.organization_id,
                Warehouse.code == payload.warehouse_id,
            )
        )
        warehouse = wh_result.scalar_one_or_none()
        if not warehouse:
            warehouse = Warehouse(
                organization_id=self.organization_id,
                code=payload.warehouse_id,
                name=f"Warehouse {payload.warehouse_id}",
                capacity=10000,
            )
            self.db.add(warehouse)
            await self.db.flush()

        # Find or create product
        prod_result = await self.db.execute(
            select(Product).where(
                Product.organization_id == self.organization_id,
                Product.sku == payload.sku,
            )
        )
        product = prod_result.scalar_one_or_none()
        if not product:
            product = Product(
                organization_id=self.organization_id,
                sku=payload.sku,
                name=payload.name,
                category=payload.category,
                unit_price=payload.unit_cost * 1.3,
                unit_cost=payload.unit_cost,
            )
            self.db.add(product)
            await self.db.flush()

        # Find or create inventory entry
        inv_check = await self.db.execute(
            select(Inventory).where(
                Inventory.organization_id == self.organization_id,
                Inventory.warehouse_id == warehouse.id,
                Inventory.product_id == product.id,
            )
        )
        existing_inv = inv_check.scalar_one_or_none()
        if existing_inv:
            existing_inv.quantity = int(payload.quantity_on_hand)
            existing_inv.reorder_point = int(payload.reorder_point)
            existing_inv.safety_stock = int(payload.reorder_point / 2)
            await self.db.commit()
            created = existing_inv
        else:
            inventory = Inventory(
                organization_id=self.organization_id,
                warehouse_id=warehouse.id,
                product_id=product.id,
                quantity=int(payload.quantity_on_hand),
                safety_stock=int(payload.reorder_point / 2),
                reorder_point=int(payload.reorder_point),
            )
            created = await self.repo.create(inventory)
        loaded = await self.repo.get_by_id_and_org(created.id, self.organization_id)


        return InventoryItemResponse(
            id=loaded.id,
            sku=loaded.product.sku,
            name=loaded.product.name,
            category=loaded.product.category,
            quantity_on_hand=float(loaded.quantity),
            quantity_reserved=0.0,
            reorder_point=float(loaded.reorder_point),
            unit_cost=float(loaded.product.unit_cost),
            warehouse_id=loaded.warehouse.code,
            is_low_stock=loaded.quantity <= loaded.safety_stock,
            updated_at=loaded.updated_at,
        )

    async def delete_inventory(self, inventory_id: str) -> bool:
        """Delete inventory record ensuring tenant ownership."""
        deleted = await self.repo.delete_by_id_and_org(inventory_id, self.organization_id)
        if not deleted:
            raise AppException(
                message=f"Inventory item '{inventory_id}' not found.",
                status_code=404,
                error_code="INVENTORY_NOT_FOUND",
            )
        return True
