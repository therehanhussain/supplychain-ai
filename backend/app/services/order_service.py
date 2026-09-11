"""Order domain service executing business transactions and tenant isolation."""
import uuid
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.models.order import Order, OrderItem
from backend.app.models.product import Product
from backend.app.models.supplier import Supplier
from backend.app.repositories.orders import OrderRepository
from backend.app.schemas.order import OrderCreate, OrderResponse, OrderItem as OrderItemSchema
from backend.app.core.exceptions import AppException


class OrderService:
    def __init__(self, db: AsyncSession, organization_id: str):
        self.db = db
        self.organization_id = organization_id
        self.repo = OrderRepository(db)

    async def list_orders(
        self,
        status: Optional[str] = None,
        supplier_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[OrderResponse]:
        """List tenant-owned orders."""
        orders = await self.repo.list_by_org(
            organization_id=self.organization_id,
            status=status,
            supplier_id=supplier_id,
            skip=skip,
            limit=limit,
        )
        return [
            OrderResponse(
                id=o.id,
                customer_name=o.order_number,
                supplier_id=o.supplier.name if o.supplier else o.supplier_id,
                items=[
                    OrderItemSchema(
                        product_id=item.product.sku if item.product else item.product_id,
                        product_name=item.product.name if item.product else "Item",
                        quantity=float(item.quantity),
                        unit_price=float(item.unit_price),
                    )
                    for item in o.items
                ],
                total_amount=float(o.total_amount),
                status=o.status,
                created_at=o.created_at,
            )
            for o in orders
        ]

    async def get_order(self, order_id: str) -> OrderResponse:
        """Fetch order record ensuring tenant ownership."""
        o = await self.repo.get_by_id_and_org(order_id, self.organization_id)
        if not o:
            raise AppException(
                message=f"Order '{order_id}' not found in current organization.",
                status_code=404,
                error_code="ORDER_NOT_FOUND",
            )
        return OrderResponse(
            id=o.id,
            customer_name=o.order_number,
            supplier_id=o.supplier.name if o.supplier else o.supplier_id,
            items=[
                OrderItemSchema(
                    product_id=item.product.sku if item.product else item.product_id,
                    product_name=item.product.name if item.product else "Item",
                    quantity=float(item.quantity),
                    unit_price=float(item.unit_price),
                )
                for item in o.items
            ],
            total_amount=float(o.total_amount),
            status=o.status,
            created_at=o.created_at,
        )

    async def create_order(self, payload: OrderCreate) -> OrderResponse:
        """Create new purchase order with line items."""
        # Find or create supplier
        supp_res = await self.db.execute(
            select(Supplier).where(
                Supplier.organization_id == self.organization_id,
                Supplier.id == payload.supplier_id,
            )
        )
        supplier = supp_res.scalar_one_or_none()
        if not supplier:
            # Check by name or create
            supp_name_res = await self.db.execute(
                select(Supplier).where(
                    Supplier.organization_id == self.organization_id,
                    Supplier.name == payload.supplier_id,
                )
            )
            supplier = supp_name_res.scalar_one_or_none()
            if not supplier:
                supplier = Supplier(
                    organization_id=self.organization_id,
                    name=payload.supplier_id,
                    tier=1,
                    status="active",
                )
                self.db.add(supplier)
                await self.db.flush()

        order_num = f"ORD-{uuid.uuid4().hex[:8].upper()}"
        total_amount = payload.total_amount
        if not total_amount and payload.items:
            total_amount = sum(item.quantity * item.unit_price for item in payload.items)

        order = Order(
            organization_id=self.organization_id,
            supplier_id=supplier.id,
            order_number=order_num,
            status=payload.status,
            total_amount=total_amount,
            currency="USD",
        )
        self.db.add(order)
        await self.db.flush()

        # Add line items
        for item_data in payload.items:
            # Check or create product
            p_res = await self.db.execute(
                select(Product).where(
                    Product.organization_id == self.organization_id,
                    Product.sku == item_data.product_id,
                )
            )
            product = p_res.scalar_one_or_none()
            if not product:
                product = Product(
                    organization_id=self.organization_id,
                    sku=item_data.product_id,
                    name=item_data.product_name,
                    unit_price=item_data.unit_price,
                    unit_cost=item_data.unit_price * 0.8,
                )
                self.db.add(product)
                await self.db.flush()

            order_item = OrderItem(
                order_id=order.id,
                product_id=product.id,
                quantity=int(item_data.quantity),
                unit_price=item_data.unit_price,
                total_price=item_data.quantity * item_data.unit_price,
            )
            self.db.add(order_item)

        await self.db.commit()

        loaded = await self.repo.get_by_id_and_org(order.id, self.organization_id)
        return OrderResponse(
            id=loaded.id,
            customer_name=loaded.order_number,
            supplier_id=loaded.supplier.name,
            items=[
                OrderItemSchema(
                    product_id=item.product.sku,
                    product_name=item.product.name,
                    quantity=float(item.quantity),
                    unit_price=float(item.unit_price),
                )
                for item in loaded.items
            ],
            total_amount=float(loaded.total_amount),
            status=loaded.status,
            created_at=loaded.created_at,
        )

    async def delete_order(self, order_id: str) -> bool:
        """Delete order ensuring tenant ownership."""
        deleted = await self.repo.delete_by_id_and_org(order_id, self.organization_id)
        if not deleted:
            raise AppException(
                message=f"Order '{order_id}' not found.",
                status_code=404,
                error_code="ORDER_NOT_FOUND",
            )
        return True
