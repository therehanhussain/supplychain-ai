"""MaterialLot and WorkOrderLotHolding models for lot/batch traceability."""
from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
from sqlalchemy import String, Float, Text, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.models.base import Base, TimestampMixin, generate_uuid
from backend.app.models.enums import UnitOfMeasure

if TYPE_CHECKING:
    from backend.app.models.organization import Organization
    from backend.app.models.product import Product
    from backend.app.models.warehouse import Warehouse
    from backend.app.models.supplier import Supplier
    from backend.app.models.work_order import WorkOrder
    from backend.app.models.stock_transaction import StockTransaction


class MaterialLot(Base, TimestampMixin):
    """MaterialLot model representing a discrete incoming batch of raw material or component."""
    __tablename__ = "material_lots"
    __table_args__ = (
        UniqueConstraint("organization_id", "product_id", "lot_number", name="uq_org_product_lot_number"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=generate_uuid
    )
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True
    )
    warehouse_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("warehouses.id", ondelete="SET NULL"), nullable=True, index=True
    )
    supplier_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("suppliers.id", ondelete="SET NULL"), nullable=True, index=True
    )
    lot_number: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    received_quantity: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    current_quantity: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    unit_of_measure: Mapped[str] = mapped_column(
        String(20), default=UnitOfMeasure.PIECE.value, nullable=False
    )
    status: Mapped[str] = mapped_column(String(50), default="ACTIVE", nullable=False, index=True)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    expiry_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    manufacturing_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    organization: Mapped["Organization"] = relationship("Organization")
    product: Mapped["Product"] = relationship("Product")
    warehouse: Mapped[Optional["Warehouse"]] = relationship("Warehouse")
    supplier: Mapped[Optional["Supplier"]] = relationship("Supplier")
    stock_transactions: Mapped[List["StockTransaction"]] = relationship("StockTransaction", back_populates="lot")
    holdings: Mapped[List["WorkOrderLotHolding"]] = relationship("WorkOrderLotHolding", back_populates="lot", cascade="all, delete-orphan")


class WorkOrderLotHolding(Base, TimestampMixin):
    """WorkOrderLotHolding tracks the quantity of a specific material lot currently held at a work order."""
    __tablename__ = "work_order_lot_holdings"
    __table_args__ = (
        UniqueConstraint("organization_id", "work_order_id", "lot_id", name="uq_org_wo_lot_holding"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=generate_uuid
    )
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    work_order_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("work_orders.id", ondelete="CASCADE"), nullable=False, index=True
    )
    lot_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("material_lots.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True
    )
    issued_quantity: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    consumed_quantity: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    returned_quantity: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    wastage_quantity: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    unit_of_measure: Mapped[str] = mapped_column(
        String(20), default=UnitOfMeasure.PIECE.value, nullable=False
    )

    # Relationships
    organization: Mapped["Organization"] = relationship("Organization")
    work_order: Mapped["WorkOrder"] = relationship("WorkOrder")
    lot: Mapped["MaterialLot"] = relationship("MaterialLot", back_populates="holdings")
    product: Mapped["Product"] = relationship("Product")

    @property
    def remaining_holding(self) -> float:
        """Physical quantity currently in floor holding for this specific lot."""
        return max(0.0, round(self.issued_quantity - (self.consumed_quantity + self.returned_quantity + self.wastage_quantity), 4))
