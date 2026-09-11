"""Product model representing catalog items and bill-of-materials SKUs."""
from typing import Optional, List, TYPE_CHECKING
from sqlalchemy import String, Integer, Float, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.models.base import Base, TimestampMixin, generate_uuid

if TYPE_CHECKING:
    from backend.app.models.organization import Organization
    from backend.app.models.inventory import Inventory
    from backend.app.models.order import OrderItem
    from backend.app.models.supplier import Supplier
    from backend.app.models.production_order import ProductionOrder
    from backend.app.models.material_requirement import MaterialRequirement
    from backend.app.models.stock_transaction import StockTransaction


class Product(Base, TimestampMixin):
    __tablename__ = "products"
    __table_args__ = (
        UniqueConstraint("organization_id", "sku", name="uq_org_product_sku"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=generate_uuid
    )
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sku: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    category: Mapped[str] = mapped_column(String(100), default="General", nullable=False, index=True)
    material_type: Mapped[str] = mapped_column(String(50), default="RAW_MATERIAL", nullable=False, index=True)
    unit_of_measure: Mapped[str] = mapped_column(String(20), default="piece", nullable=False)
    unit_price: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    unit_cost: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    lead_time_days: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    preferred_supplier_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("suppliers.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # Relationships
    organization: Mapped["Organization"] = relationship("Organization", back_populates="products")
    preferred_supplier: Mapped[Optional["Supplier"]] = relationship("Supplier")
    inventories: Mapped[List["Inventory"]] = relationship("Inventory", back_populates="product", cascade="all, delete-orphan")
    order_items: Mapped[List["OrderItem"]] = relationship("OrderItem", back_populates="product")
    production_orders: Mapped[List["ProductionOrder"]] = relationship("ProductionOrder", back_populates="product")
    material_requirements: Mapped[List["MaterialRequirement"]] = relationship("MaterialRequirement", back_populates="product")
    stock_transactions: Mapped[List["StockTransaction"]] = relationship("StockTransaction", back_populates="product")
