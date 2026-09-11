"""MaterialRequirement model representing planned vs actual raw material usage."""
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Float, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.models.base import Base, TimestampMixin, generate_uuid
from backend.app.models.enums import UnitOfMeasure

if TYPE_CHECKING:
    from backend.app.models.organization import Organization
    from backend.app.models.production_order import ProductionOrder
    from backend.app.models.work_order import WorkOrder
    from backend.app.models.product import Product


class MaterialRequirement(Base, TimestampMixin):
    __tablename__ = "material_requirements"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=generate_uuid
    )
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    production_order_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("production_orders.id", ondelete="CASCADE"), nullable=True, index=True
    )
    work_order_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("work_orders.id", ondelete="CASCADE"), nullable=True, index=True
    )
    product_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True
    )
    required_quantity: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    issued_quantity: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    consumed_quantity: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    returned_quantity: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    wastage_quantity: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    unit_of_measure: Mapped[str] = mapped_column(
        String(20), default=UnitOfMeasure.PIECE.value, nullable=False
    )

    # Relationships
    organization: Mapped["Organization"] = relationship("Organization")
    production_order: Mapped[Optional["ProductionOrder"]] = relationship(
        "ProductionOrder", back_populates="material_requirements"
    )
    work_order: Mapped[Optional["WorkOrder"]] = relationship(
        "WorkOrder", back_populates="material_requirements"
    )
    product: Mapped["Product"] = relationship("Product", back_populates="material_requirements")

    @property
    def remaining_issued_holding(self) -> float:
        """Calculate quantity currently in production holding (issued minus consumed/returned/wasted)."""
        return max(0.0, round(self.issued_quantity - (self.consumed_quantity + self.returned_quantity + self.wastage_quantity), 4))

    @property
    def variance_quantity(self) -> float:
        """Variance between actual consumption + wastage vs expected required quantity."""
        return round((self.consumed_quantity + self.wastage_quantity) - self.required_quantity, 4)
