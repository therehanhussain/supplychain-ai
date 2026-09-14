"""MaterialRequest model representing floor operator material requisitions."""
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Float, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.models.base import Base, TimestampMixin, generate_uuid

if TYPE_CHECKING:
    from backend.app.models.organization import Organization
    from backend.app.models.work_order import WorkOrder
    from backend.app.models.product import Product
    from backend.app.models.user import User
    from backend.app.models.stock_transaction import StockTransaction


class MaterialRequest(Base, TimestampMixin):
    __tablename__ = "material_requests"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=generate_uuid
    )
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    work_order_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("work_orders.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True
    )
    requested_by_user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    unit_of_measure: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="PENDING", nullable=False, index=True)
    reason: Mapped[str] = mapped_column(String(255), nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reviewed_by_user_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    rejection_reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    issued_transaction_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("stock_transactions.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # Relationships
    organization: Mapped["Organization"] = relationship("Organization")
    work_order: Mapped["WorkOrder"] = relationship("WorkOrder")
    product: Mapped["Product"] = relationship("Product")
    requester: Mapped["User"] = relationship("User", foreign_keys=[requested_by_user_id])
    reviewer: Mapped[Optional["User"]] = relationship("User", foreign_keys=[reviewed_by_user_id])
    issued_transaction: Mapped[Optional["StockTransaction"]] = relationship("StockTransaction", foreign_keys=[issued_transaction_id])
