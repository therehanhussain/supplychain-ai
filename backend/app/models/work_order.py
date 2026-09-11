"""WorkOrder model representing discrete manufacturing floor jobs."""
from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
from sqlalchemy import String, Float, DateTime, ForeignKey, UniqueConstraint, Text, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.models.base import Base, TimestampMixin, generate_uuid
from backend.app.models.enums import WorkOrderStatus

if TYPE_CHECKING:
    from backend.app.models.organization import Organization
    from backend.app.models.production_order import ProductionOrder
    from backend.app.models.warehouse import Warehouse
    from backend.app.models.user import User
    from backend.app.models.material_requirement import MaterialRequirement
    from backend.app.models.stock_transaction import StockTransaction


class WorkOrder(Base, TimestampMixin):
    __tablename__ = "work_orders"
    __table_args__ = (
        UniqueConstraint("organization_id", "work_order_number", name="uq_org_work_order_number"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=generate_uuid
    )
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    production_order_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("production_orders.id", ondelete="CASCADE"), nullable=False, index=True
    )
    work_order_number: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    warehouse_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("warehouses.id", ondelete="SET NULL"), nullable=True, index=True
    )
    production_area: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    assigned_user_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    planned_quantity: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    completed_quantity: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    status: Mapped[WorkOrderStatus] = mapped_column(
        SQLEnum(WorkOrderStatus, name="work_order_status_enum", values_callable=lambda x: [e.value for e in x]),
        default=WorkOrderStatus.PLANNED,
        nullable=False,
        index=True,
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    organization: Mapped["Organization"] = relationship("Organization")
    production_order: Mapped["ProductionOrder"] = relationship("ProductionOrder", back_populates="work_orders")
    warehouse: Mapped[Optional["Warehouse"]] = relationship("Warehouse")
    assigned_user: Mapped[Optional["User"]] = relationship("User")
    material_requirements: Mapped[List["MaterialRequirement"]] = relationship(
        "MaterialRequirement", back_populates="work_order", cascade="all, delete-orphan"
    )
    stock_transactions: Mapped[List["StockTransaction"]] = relationship(
        "StockTransaction", back_populates="work_order"
    )
