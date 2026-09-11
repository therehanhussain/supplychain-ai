"""StockTransaction model representing the immutable material movement ledger."""
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Float, Text, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.models.base import Base, TimestampMixin, generate_uuid
from backend.app.models.enums import TransactionType, UnitOfMeasure

if TYPE_CHECKING:
    from backend.app.models.organization import Organization
    from backend.app.models.inventory import Inventory
    from backend.app.models.product import Product
    from backend.app.models.warehouse import Warehouse
    from backend.app.models.work_order import WorkOrder
    from backend.app.models.production_order import ProductionOrder
    from backend.app.models.user import User


class StockTransaction(Base, TimestampMixin):
    __tablename__ = "stock_transactions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=generate_uuid
    )
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    inventory_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("inventories.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True
    )
    warehouse_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    work_order_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("work_orders.id", ondelete="SET NULL"), nullable=True, index=True
    )
    production_order_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("production_orders.id", ondelete="SET NULL"), nullable=True, index=True
    )
    employee_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    performed_by_user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    transaction_type: Mapped[TransactionType] = mapped_column(
        SQLEnum(TransactionType, name="stock_transaction_type_enum", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        index=True,
    )
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    unit_of_measure: Mapped[str] = mapped_column(
        String(20), default=UnitOfMeasure.PIECE.value, nullable=False
    )
    reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    source_location: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    destination_location: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    reference_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    reference_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    organization: Mapped["Organization"] = relationship("Organization")
    inventory: Mapped["Inventory"] = relationship("Inventory", back_populates="stock_transactions")
    product: Mapped["Product"] = relationship("Product", back_populates="stock_transactions")
    warehouse: Mapped["Warehouse"] = relationship("Warehouse")
    work_order: Mapped[Optional["WorkOrder"]] = relationship("WorkOrder", back_populates="stock_transactions")
    production_order: Mapped[Optional["ProductionOrder"]] = relationship("ProductionOrder", back_populates="stock_transactions")
    employee: Mapped[Optional["User"]] = relationship("User", foreign_keys=[employee_id])
    performed_by_user: Mapped["User"] = relationship("User", foreign_keys=[performed_by_user_id])
