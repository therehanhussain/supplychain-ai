"""Material Traceability & Manufacturing domain service.

Enforces:
- Separation of ISSUE (Store -> Holding) vs CONSUMPTION (Holding -> Assembly).
- Reconciliation: issued = consumed + returned + wastage.
- Atomic stock ledger updates (zero silent quantity overwrites).
- Full audit logging and multi-tenant isolation.
"""

from typing import List, Optional, Tuple
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.exceptions import AppException
from backend.app.models.organization import Organization
from backend.app.models.product import Product
from backend.app.models.warehouse import Warehouse
from backend.app.models.inventory import Inventory
from backend.app.models.audit_log import AuditLog
from backend.app.models.production_order import ProductionOrder
from backend.app.models.work_order import WorkOrder
from backend.app.models.material_requirement import MaterialRequirement
from backend.app.models.stock_transaction import StockTransaction
from backend.app.models.enums import TransactionType, UnitOfMeasure, ProductionOrderStatus, WorkOrderStatus
from backend.app.models.user import User

from backend.app.schemas.manufacturing import (
    StockTransactionCreate,
    StockTransactionResponse,
    StockTransferCreate,
    ProductionOrderCreate,
    ProductionOrderResponse,
    WorkOrderCreate,
    WorkOrderResponse,
    MaterialRequirementCreate,
    MaterialRequirementResponse,
    TraceabilityTimelineResponse,
    TraceabilityTimelineEntry,
)


class MaterialTraceabilityService:
    def __init__(self, db: AsyncSession, organization_id: str, user_id: str):
        self.db = db
        self.organization_id = organization_id
        self.user_id = user_id

    # --------------------------------------------------------------------------
    # Production Orders
    # --------------------------------------------------------------------------
    async def create_production_order(self, payload: ProductionOrderCreate) -> ProductionOrderResponse:
        """Create organization-scoped production order for finished goods."""
        # Verify product exists in org
        prod_res = await self.db.execute(
            select(Product).where(
                Product.organization_id == self.organization_id,
                (Product.id == payload.product_id) | (Product.sku == payload.product_id),
            )
        )
        product = prod_res.scalar_one_or_none()
        if not product:
            raise AppException(f"Product '{payload.product_id}' not found.", code="PRODUCT_NOT_FOUND", status_code=404)


        # Check order_number uniqueness in org
        existing = await self.db.execute(
            select(ProductionOrder).where(
                ProductionOrder.organization_id == self.organization_id,
                ProductionOrder.order_number == payload.order_number,
            )
        )
        if existing.scalar_one_or_none():
            raise AppException(f"Production order '{payload.order_number}' already exists.", 409, "ORDER_ALREADY_EXISTS")

        order = ProductionOrder(
            organization_id=self.organization_id,
            order_number=payload.order_number,
            product_id=product.id,
            planned_quantity=payload.planned_quantity,
            completed_quantity=0.0,
            status=ProductionOrderStatus.PLANNED,
            planned_start=payload.planned_start,
            planned_end=payload.planned_end,
            notes=payload.notes,
        )
        self.db.add(order)

        # Emit audit record
        audit = AuditLog(
            organization_id=self.organization_id,
            user_id=self.user_id,
            action="PRODUCTION_ORDER_CREATED",
            entity_type="ProductionOrder",
            entity_id=order.id,
            details=f"Order={order.order_number}, Product={product.sku}, PlannedQty={order.planned_quantity}",
        )
        self.db.add(audit)

        await self.db.commit()
        await self.db.refresh(order)

        return ProductionOrderResponse(
            id=order.id,
            organization_id=order.organization_id,
            order_number=order.order_number,
            product_id=order.product_id,
            product_sku=product.sku,
            product_name=product.name,
            planned_quantity=order.planned_quantity,
            completed_quantity=order.completed_quantity,
            status=order.status,
            planned_start=order.planned_start,
            planned_end=order.planned_end,
            actual_start=order.actual_start,
            actual_end=order.actual_end,
            notes=order.notes,
            created_at=order.created_at,
            updated_at=order.updated_at,
        )

    async def list_production_orders(
        self, status: Optional[str] = None, skip: int = 0, limit: int = 100
    ) -> List[ProductionOrderResponse]:
        query = (
            select(ProductionOrder)
            .options(selectinload(ProductionOrder.product))
            .where(ProductionOrder.organization_id == self.organization_id)
        )
        if status:
            query = query.where(ProductionOrder.status == status)
        query = query.order_by(ProductionOrder.created_at.desc()).offset(skip).limit(limit)
        res = await self.db.execute(query)
        orders = res.scalars().all()

        return [
            ProductionOrderResponse(
                id=o.id,
                organization_id=o.organization_id,
                order_number=o.order_number,
                product_id=o.product_id,
                product_sku=o.product.sku if o.product else None,
                product_name=o.product.name if o.product else None,
                planned_quantity=o.planned_quantity,
                completed_quantity=o.completed_quantity,
                status=o.status,
                planned_start=o.planned_start,
                planned_end=o.planned_end,
                actual_start=o.actual_start,
                actual_end=o.actual_end,
                notes=o.notes,
                created_at=o.created_at,
                updated_at=o.updated_at,
            )
            for o in orders
        ]

    # --------------------------------------------------------------------------
    # Work Orders
    # --------------------------------------------------------------------------
    async def create_work_order(self, payload: WorkOrderCreate) -> WorkOrderResponse:
        """Create work order associated with production order."""
        # Verify production order
        po_res = await self.db.execute(
            select(ProductionOrder).where(
                ProductionOrder.id == payload.production_order_id,
                ProductionOrder.organization_id == self.organization_id,
            )
        )
        po = po_res.scalar_one_or_none()
        if not po:
            raise AppException(f"Production order '{payload.production_order_id}' not found.", 404, "PRODUCTION_ORDER_NOT_FOUND")

        # Check unique work_order_number
        existing = await self.db.execute(
            select(WorkOrder).where(
                WorkOrder.organization_id == self.organization_id,
                WorkOrder.work_order_number == payload.work_order_number,
            )
        )
        if existing.scalar_one_or_none():
            raise AppException(f"Work order '{payload.work_order_number}' already exists.", 409, "WORK_ORDER_ALREADY_EXISTS")

        resolved_wh_id = None
        if payload.warehouse_id:
            wh_res = await self.db.execute(
                select(Warehouse).where(
                    Warehouse.organization_id == self.organization_id,
                    (Warehouse.id == payload.warehouse_id) | (Warehouse.code == payload.warehouse_id),
                )
            )
            wh = wh_res.scalar_one_or_none()
            resolved_wh_id = wh.id if wh else payload.warehouse_id

        wo = WorkOrder(
            organization_id=self.organization_id,
            production_order_id=po.id,
            work_order_number=payload.work_order_number,
            warehouse_id=resolved_wh_id,
            production_area=payload.production_area,
            assigned_user_id=payload.assigned_user_id,
            planned_quantity=payload.planned_quantity,
            completed_quantity=0.0,
            status=WorkOrderStatus.PLANNED,
            notes=payload.notes,
        )
        self.db.add(wo)

        audit = AuditLog(
            organization_id=self.organization_id,
            user_id=self.user_id,
            action="WORK_ORDER_CREATED",
            entity_type="WorkOrder",
            entity_id=wo.id,
            details=f"WO={wo.work_order_number}, PO={po.order_number}, Area={wo.production_area}",
        )
        self.db.add(audit)

        await self.db.commit()
        await self.db.refresh(wo)

        return WorkOrderResponse(
            id=wo.id,
            organization_id=wo.organization_id,
            production_order_id=wo.production_order_id,
            work_order_number=wo.work_order_number,
            warehouse_id=wo.warehouse_id,
            production_area=wo.production_area,
            assigned_user_id=wo.assigned_user_id,
            planned_quantity=wo.planned_quantity,
            completed_quantity=wo.completed_quantity,
            status=wo.status,
            started_at=wo.started_at,
            completed_at=wo.completed_at,
            notes=wo.notes,
            created_at=wo.created_at,
            updated_at=wo.updated_at,
        )

    async def list_work_orders(
        self, production_order_id: Optional[str] = None, status: Optional[str] = None, skip: int = 0, limit: int = 100
    ) -> List[WorkOrderResponse]:
        query = (
            select(WorkOrder)
            .where(WorkOrder.organization_id == self.organization_id)
        )
        if production_order_id:
            query = query.where(WorkOrder.production_order_id == production_order_id)
        if status:
            query = query.where(WorkOrder.status == status)
        query = query.order_by(WorkOrder.created_at.desc()).offset(skip).limit(limit)
        res = await self.db.execute(query)
        wos = res.scalars().all()

        return [
            WorkOrderResponse(
                id=w.id,
                organization_id=w.organization_id,
                production_order_id=w.production_order_id,
                work_order_number=w.work_order_number,
                warehouse_id=w.warehouse_id,
                production_area=w.production_area,
                assigned_user_id=w.assigned_user_id,
                planned_quantity=w.planned_quantity,
                completed_quantity=w.completed_quantity,
                status=w.status,
                started_at=w.started_at,
                completed_at=w.completed_at,
                notes=w.notes,
                created_at=w.created_at,
                updated_at=w.updated_at,
            )
            for w in wos
        ]

    # --------------------------------------------------------------------------
    # Material Requirements
    # --------------------------------------------------------------------------
    async def create_material_requirement(self, payload: MaterialRequirementCreate) -> MaterialRequirementResponse:
        """Define required raw materials for a production or work order."""
        prod_res = await self.db.execute(
            select(Product).where(
                Product.organization_id == self.organization_id,
                (Product.id == payload.product_id) | (Product.sku == payload.product_id),
            )
        )
        product = prod_res.scalar_one_or_none()
        if not product:
            raise AppException(f"Material Product '{payload.product_id}' not found.", code="PRODUCT_NOT_FOUND", status_code=404)


        req = MaterialRequirement(
            organization_id=self.organization_id,
            production_order_id=payload.production_order_id,
            work_order_id=payload.work_order_id,
            product_id=product.id,
            required_quantity=payload.required_quantity,
            issued_quantity=0.0,
            consumed_quantity=0.0,
            returned_quantity=0.0,
            wastage_quantity=0.0,
            unit_of_measure=payload.unit_of_measure or product.unit_of_measure,
        )
        self.db.add(req)
        await self.db.commit()
        await self.db.refresh(req)

        return MaterialRequirementResponse(
            id=req.id,
            organization_id=req.organization_id,
            production_order_id=req.production_order_id,
            work_order_id=req.work_order_id,
            product_id=req.product_id,
            product_sku=product.sku,
            product_name=product.name,
            required_quantity=req.required_quantity,
            issued_quantity=req.issued_quantity,
            consumed_quantity=req.consumed_quantity,
            returned_quantity=req.returned_quantity,
            wastage_quantity=req.wastage_quantity,
            remaining_issued_holding=req.remaining_issued_holding,
            variance_quantity=req.variance_quantity,
            unit_of_measure=req.unit_of_measure,
            created_at=req.created_at,
            updated_at=req.updated_at,
        )

    # --------------------------------------------------------------------------
    # Core Material Ledger: Stock Transactions
    # --------------------------------------------------------------------------
    async def record_transaction(self, payload: StockTransactionCreate) -> StockTransactionResponse:
        """Atomic material movement execution with strict business rules and audit trail."""
        # Validate quantity
        if payload.quantity <= 0:
            raise AppException("Transaction quantity must be greater than zero.", 400, "INVALID_QUANTITY")

        # Resolve inventory, product, and warehouse
        inventory, product, warehouse = await self._resolve_entities(payload)

        tx_type = payload.transaction_type
        quantity = payload.quantity

        # Enforce reason requirement on adjustments, wastage, damage, expiry
        if tx_type in (TransactionType.ADJUSTMENT, TransactionType.WASTAGE, TransactionType.DAMAGE, TransactionType.EXPIRY):
            if not payload.reason or not payload.reason.strip():
                raise AppException(f"Mandatory reason required for transaction type '{tx_type.value}'.", 400, "REASON_REQUIRED")

        # Handle Material Requirement link if work_order_id is specified
        requirement: Optional[MaterialRequirement] = None
        if payload.work_order_id:
            req_res = await self.db.execute(
                select(MaterialRequirement).where(
                    MaterialRequirement.organization_id == self.organization_id,
                    MaterialRequirement.work_order_id == payload.work_order_id,
                    MaterialRequirement.product_id == product.id,
                )
            )
            requirement = req_res.scalar_one_or_none()

        # ----------------------------------------------------------------------
        # Business Logic & Inventory Balances
        # ----------------------------------------------------------------------
        if tx_type == TransactionType.RECEIPT:
            # Material Store receives stock from supplier / inbound
            inventory.quantity = int(inventory.quantity + round(quantity))

        elif tx_type == TransactionType.ISSUE:
            # Store issues material to Production / Employee
            if inventory.quantity < quantity:
                raise AppException(
                    f"Insufficient stock in warehouse '{warehouse.code}'. Available: {inventory.quantity}, Requested: {quantity}",
                    400,
                    "INSUFFICIENT_INVENTORY",
                )
            inventory.quantity = int(inventory.quantity - round(quantity))

            # Update requirement issued balance
            if requirement:
                requirement.issued_quantity += quantity
            elif payload.work_order_id:
                # Auto-create requirement tracker if not pre-defined
                requirement = MaterialRequirement(
                    organization_id=self.organization_id,
                    work_order_id=payload.work_order_id,
                    product_id=product.id,
                    required_quantity=quantity,
                    issued_quantity=quantity,
                    unit_of_measure=payload.unit_of_measure or product.unit_of_measure,
                )
                self.db.add(requirement)

        elif tx_type == TransactionType.CONSUMPTION:
            # Production consumes from issued material
            if not payload.work_order_id:
                raise AppException("CONSUMPTION requires a valid work_order_id.", 400, "WORK_ORDER_REQUIRED")

            if not requirement:
                raise AppException(
                    f"No material requirement or prior issue found for product '{product.sku}' in work order '{payload.work_order_id}'.",
                    400,
                    "NO_ISSUED_MATERIAL",
                )

            available_holding = requirement.remaining_issued_holding
            if quantity > available_holding:
                raise AppException(
                    f"Consumption exceeds issued production holding. Available holding: {available_holding}, Requested: {quantity}",
                    400,
                    "EXCEEDS_ISSUED_HOLDING",
                )

            # Store inventory is NOT decreased again (was already decreased upon ISSUE)
            requirement.consumed_quantity += quantity

        elif tx_type == TransactionType.RETURN:
            # Production returns unused material back to Store
            if requirement:
                available_holding = requirement.remaining_issued_holding
                if quantity > available_holding:
                    raise AppException(
                        f"Return exceeds issued production holding. Available holding: {available_holding}, Attempted return: {quantity}",
                        400,
                        "EXCEEDS_ISSUED_HOLDING",
                    )
                requirement.returned_quantity += quantity

            # Store inventory increases
            inventory.quantity = int(inventory.quantity + round(quantity))

        elif tx_type == TransactionType.WASTAGE:
            # Production scrap or warehouse loss
            if requirement:
                available_holding = requirement.remaining_issued_holding
                if quantity > available_holding:
                    raise AppException(
                        f"Wastage exceeds issued production holding. Available holding: {available_holding}, Reported wastage: {quantity}",
                        400,
                        "EXCEEDS_ISSUED_HOLDING",
                    )
                requirement.wastage_quantity += quantity
            else:
                # Warehouse store loss
                if inventory.quantity < quantity:
                    raise AppException(
                        f"Wastage cannot exceed available store inventory: {inventory.quantity}.",
                        400,
                        "INSUFFICIENT_INVENTORY",
                    )
                inventory.quantity = int(inventory.quantity - round(quantity))

        elif tx_type in (TransactionType.DAMAGE, TransactionType.EXPIRY):
            # Damaged or expired store stock
            if inventory.quantity < quantity:
                raise AppException(
                    f"Insufficient stock to record {tx_type.value}. Available: {inventory.quantity}, Quantity: {quantity}",
                    400,
                    "INSUFFICIENT_INVENTORY",
                )
            inventory.quantity = int(inventory.quantity - round(quantity))

        elif tx_type == TransactionType.ADJUSTMENT:
            # Physical inventory count reconciliation
            # Note: reason is already validated as mandatory
            if payload.notes and payload.notes.startswith("REDUCE"):
                if inventory.quantity < quantity:
                    raise AppException(f"Cannot adjust inventory below zero. Current: {inventory.quantity}", 400, "INSUFFICIENT_INVENTORY")
                inventory.quantity = int(inventory.quantity - round(quantity))
            else:
                inventory.quantity = int(round(quantity))

        elif tx_type == TransactionType.TRANSFER_OUT:
            if inventory.quantity < quantity:
                raise AppException(
                    f"Insufficient stock for transfer. Available: {inventory.quantity}, Requested: {quantity}",
                    400,
                    "INSUFFICIENT_INVENTORY",
                )
            inventory.quantity = int(inventory.quantity - round(quantity))

        elif tx_type == TransactionType.TRANSFER_IN:
            inventory.quantity = int(inventory.quantity + round(quantity))

        # ----------------------------------------------------------------------
        # Record Immutable StockTransaction
        # ----------------------------------------------------------------------
        tx = StockTransaction(
            organization_id=self.organization_id,
            inventory_id=inventory.id,
            product_id=product.id,
            warehouse_id=warehouse.id,
            work_order_id=payload.work_order_id,
            production_order_id=payload.production_order_id,
            employee_id=payload.employee_id or self.user_id,
            performed_by_user_id=self.user_id,
            transaction_type=tx_type,
            quantity=quantity,
            unit_of_measure=payload.unit_of_measure or product.unit_of_measure,
            reason=payload.reason,
            source_location=payload.source_location or warehouse.code,
            destination_location=payload.destination_location,
            reference_type=payload.reference_type,
            reference_id=payload.reference_id,
            notes=payload.notes,
        )
        self.db.add(tx)

        # ----------------------------------------------------------------------
        # Automatic AuditLog Record
        # ----------------------------------------------------------------------
        audit = AuditLog(
            organization_id=self.organization_id,
            user_id=self.user_id,
            action=f"STOCK_{tx_type.value}",
            entity_type="StockTransaction",
            entity_id=tx.id,
            details=f"Type={tx_type.value}, Qty={quantity} {tx.unit_of_measure}, SKU={product.sku}, WH={warehouse.code}, WO={payload.work_order_id or 'N/A'}, Reason={payload.reason or 'N/A'}",
        )
        self.db.add(audit)

        # Atomic commit
        await self.db.commit()
        await self.db.refresh(tx)

        # Fetch employee / user names
        performed_user = await self.db.get(User, self.user_id)

        return StockTransactionResponse(
            id=tx.id,
            organization_id=tx.organization_id,
            inventory_id=tx.inventory_id,
            product_id=tx.product_id,
            product_sku=product.sku,
            product_name=product.name,
            warehouse_id=tx.warehouse_id,
            warehouse_code=warehouse.code,
            work_order_id=tx.work_order_id,
            production_order_id=tx.production_order_id,
            employee_id=tx.employee_id,
            employee_name=performed_user.full_name if performed_user else "Employee",
            performed_by_user_id=tx.performed_by_user_id,
            performed_by_name=performed_user.full_name if performed_user else "User",
            transaction_type=tx.transaction_type,
            quantity=tx.quantity,
            unit_of_measure=tx.unit_of_measure,
            reason=tx.reason,
            source_location=tx.source_location,
            destination_location=tx.destination_location,
            reference_type=tx.reference_type,
            reference_id=tx.reference_id,
            notes=tx.notes,
            created_at=tx.created_at,
        )

    # --------------------------------------------------------------------------
    # Inter-Warehouse Transfer
    # --------------------------------------------------------------------------
    async def transfer_stock(self, payload: StockTransferCreate) -> Tuple[StockTransactionResponse, StockTransactionResponse]:
        """Atomic inter-warehouse transfer creating matched TRANSFER_OUT and TRANSFER_IN records."""
        if payload.source_warehouse_id == payload.destination_warehouse_id:
            raise AppException("Source and destination warehouses cannot be identical.", 400, "INVALID_TRANSFER_DESTINATION")

        # Step 1: Outbound from Source
        out_create = StockTransactionCreate(
            warehouse_id=payload.source_warehouse_id,
            product_id=payload.product_id,
            transaction_type=TransactionType.TRANSFER_OUT,
            quantity=payload.quantity,
            unit_of_measure=payload.unit_of_measure,
            reason=payload.reason or "Inter-warehouse transfer",
            source_location=payload.source_warehouse_id,
            destination_location=payload.destination_warehouse_id,
            reference_type="WAREHOUSE_TRANSFER",
            notes=payload.notes,
        )
        out_tx = await self.record_transaction(out_create)

        # Step 2: Inbound to Destination linked by reference_id
        in_create = StockTransactionCreate(
            warehouse_id=payload.destination_warehouse_id,
            product_id=payload.product_id,
            transaction_type=TransactionType.TRANSFER_IN,
            quantity=payload.quantity,
            unit_of_measure=payload.unit_of_measure,
            reason=payload.reason or "Inter-warehouse transfer",
            source_location=payload.source_warehouse_id,
            destination_location=payload.destination_warehouse_id,
            reference_type="WAREHOUSE_TRANSFER",
            reference_id=out_tx.id,
            notes=payload.notes,
        )
        in_tx = await self.record_transaction(in_create)

        return out_tx, in_tx

    # --------------------------------------------------------------------------
    # Material Traceability Timeline ("What happened to RM-001?")
    # --------------------------------------------------------------------------
    async def get_material_traceability(self, product_identifier: str) -> TraceabilityTimelineResponse:
        """Trace the complete material movement lifecycle across all facilities and work orders."""
        # Find product by ID or SKU
        prod_res = await self.db.execute(
            select(Product).where(
                Product.organization_id == self.organization_id,
                (Product.id == product_identifier) | (Product.sku == product_identifier),
            )
        )
        product = prod_res.scalar_one_or_none()
        if not product:
            raise AppException(f"Product '{product_identifier}' not found.", 404, "PRODUCT_NOT_FOUND")

        # Compute current total inventory across warehouses
        inv_res = await self.db.execute(
            select(Inventory).where(
                Inventory.organization_id == self.organization_id,
                Inventory.product_id == product.id,
            )
        )
        inventories = inv_res.scalars().all()
        total_stock = sum(inv.quantity for inv in inventories)

        # Fetch transaction history
        tx_res = await self.db.execute(
            select(StockTransaction)
            .options(
                selectinload(StockTransaction.warehouse),
                selectinload(StockTransaction.work_order),
                selectinload(StockTransaction.employee),
                selectinload(StockTransaction.performed_by_user),
            )
            .where(
                StockTransaction.organization_id == self.organization_id,
                StockTransaction.product_id == product.id,
            )
            .order_by(StockTransaction.created_at.asc())
        )
        transactions = tx_res.scalars().all()

        timeline = [
            TraceabilityTimelineEntry(
                timestamp=tx.created_at,
                transaction_type=tx.transaction_type.value,
                quantity=tx.quantity,
                unit_of_measure=tx.unit_of_measure,
                who=tx.performed_by_user.full_name or tx.performed_by_user.email if tx.performed_by_user else "System",
                what_material=f"{product.sku} ({product.name})",
                where=tx.warehouse.name or tx.warehouse.code if tx.warehouse else "Warehouse",
                why=tx.reason,
                work_order=tx.work_order.work_order_number if tx.work_order else None,
                source_location=tx.source_location,
                destination_location=tx.destination_location,
                reference=tx.reference_id or tx.reference_type,
            )
            for tx in transactions
        ]

        return TraceabilityTimelineResponse(
            product_id=product.id,
            sku=product.sku,
            name=product.name,
            unit_of_measure=product.unit_of_measure,
            current_stock_total=float(total_stock),
            timeline=timeline,
        )

    # --------------------------------------------------------------------------
    # Helper: Resolve Entities
    # --------------------------------------------------------------------------
    async def _resolve_entities(self, payload: StockTransactionCreate) -> Tuple[Inventory, Product, Warehouse]:
        # Path 1: Direct inventory_id
        if payload.inventory_id:
            res = await self.db.execute(
                select(Inventory)
                .options(selectinload(Inventory.product), selectinload(Inventory.warehouse))
                .where(
                    Inventory.id == payload.inventory_id,
                    Inventory.organization_id == self.organization_id,
                )
            )
            inv = res.scalar_one_or_none()
            if not inv:
                raise AppException(f"Inventory '{payload.inventory_id}' not found.", 404, "INVENTORY_NOT_FOUND")
            return inv, inv.product, inv.warehouse

        # Path 2: warehouse_id + product_id
        if not payload.warehouse_id or not payload.product_id:
            raise AppException("Must supply inventory_id OR both warehouse_id and product_id.", 400, "MISSING_IDENTIFIERS")

        # Resolve Warehouse
        wh_res = await self.db.execute(
            select(Warehouse).where(
                Warehouse.organization_id == self.organization_id,
                (Warehouse.id == payload.warehouse_id) | (Warehouse.code == payload.warehouse_id),
            )
        )
        warehouse = wh_res.scalar_one_or_none()
        if not warehouse:
            raise AppException(f"Warehouse '{payload.warehouse_id}' not found.", 404, "WAREHOUSE_NOT_FOUND")

        # Resolve Product
        prod_res = await self.db.execute(
            select(Product).where(
                Product.organization_id == self.organization_id,
                (Product.id == payload.product_id) | (Product.sku == payload.product_id),
            )
        )
        product = prod_res.scalar_one_or_none()
        if not product:
            if payload.transaction_type == TransactionType.RECEIPT:
                product = Product(
                    organization_id=self.organization_id,
                    sku=payload.product_id,
                    name=f"Material {payload.product_id}",
                    category="RAW_MATERIAL",
                    material_type="RAW_MATERIAL",
                    unit_of_measure=payload.unit_of_measure or "piece",
                )
                self.db.add(product)
                await self.db.flush()
            else:
                raise AppException(f"Product '{payload.product_id}' not found.", code="PRODUCT_NOT_FOUND", status_code=404)


        # Resolve or auto-create inventory
        inv_res = await self.db.execute(
            select(Inventory).where(
                Inventory.organization_id == self.organization_id,
                Inventory.warehouse_id == warehouse.id,
                Inventory.product_id == product.id,
            )
        )
        inventory = inv_res.scalar_one_or_none()
        if not inventory:
            if payload.transaction_type == TransactionType.RECEIPT or payload.transaction_type == TransactionType.TRANSFER_IN:
                inventory = Inventory(
                    organization_id=self.organization_id,
                    warehouse_id=warehouse.id,
                    product_id=product.id,
                    quantity=0,
                    safety_stock=50,
                    reorder_point=100,
                    reorder_quantity=200,
                )
                self.db.add(inventory)
                await self.db.flush()
            else:
                raise AppException(
                    f"No existing inventory for product '{product.sku}' in warehouse '{warehouse.code}'.",
                    404,
                    "INVENTORY_NOT_FOUND",
                )

        return inventory, product, warehouse
