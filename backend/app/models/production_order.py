"""ProductionOrder model representing manufacturing production batches."""
from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
from sqlalchemy import String, Float, DateTime, ForeignKey, UniqueConstraint, Text, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.models.base import Base, TimestampMixin, generate_uuid
from backend.app.models.enums import ProductionOrderStatus

if TYPE_CHECKING:
    from backend.app.models.organization import Organization
    from backend.app.models.product import Product
    from backend.app.models.work_order import WorkOrder
    from backend.app.models.material_requirement import MaterialRequirement
    from backend.app.models.stock_transaction import StockTransaction


class ProductionOrder(Base, TimestampMixin):
    __tablename__ = "production_orders"
    __table_args__ = (
        UniqueConstraint("organization_id", "order_number", name="uq_org_prod_order_number"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=generate_uuid
    )
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    order_number: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    product_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True
    )
    planned_quantity: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    completed_quantity: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    status: Mapped[ProductionOrderStatus] = mapped_column(
        SQLEnum(ProductionOrderStatus, name="production_order_status_enum", values_callable=lambda x: [e.value for e in x]),
        default=ProductionOrderStatus.PLANNED,
        nullable=False,
        index=True,
    )
    planned_start: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    planned_end: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    actual_start: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    actual_end: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    organization: Mapped["Organization"] = relationship("Organization")
    product: Mapped["Product"] = relationship("Product", back_populates="production_orders")
    work_orders: Mapped[List["WorkOrder"]] = relationship(
        "WorkOrder", back_populates="production_order", cascade="all, delete-orphan"
    )
    material_requirements: Mapped[List["MaterialRequirement"]] = relationship(
        "MaterialRequirement", back_populates="production_order", cascade="all, delete-orphan"
    )
    stock_transactions: Mapped[List["StockTransaction"]] = relationship(
        "StockTransaction", back_populates="production_order"
    )
