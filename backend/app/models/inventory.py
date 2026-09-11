"""Inventory model tracking SKU stock levels across warehouses."""
from typing import TYPE_CHECKING
from sqlalchemy import String, Integer, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.models.base import Base, TimestampMixin, generate_uuid

if TYPE_CHECKING:
    from backend.app.models.organization import Organization
    from backend.app.models.warehouse import Warehouse
    from backend.app.models.product import Product


class Inventory(Base, TimestampMixin):
    __tablename__ = "inventories"
    __table_args__ = (
        UniqueConstraint("organization_id", "warehouse_id", "product_id", name="uq_org_wh_product_inv"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=generate_uuid
    )
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    warehouse_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True
    )
    quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    safety_stock: Mapped[int] = mapped_column(Integer, default=50, nullable=False)
    reorder_point: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    reorder_quantity: Mapped[int] = mapped_column(Integer, default=200, nullable=False)

    # Relationships
    organization: Mapped["Organization"] = relationship("Organization")
    warehouse: Mapped["Warehouse"] = relationship("Warehouse", back_populates="inventories")
    product: Mapped["Product"] = relationship("Product", back_populates="inventories")
