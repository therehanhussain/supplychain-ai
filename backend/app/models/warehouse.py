"""Warehouse model representing inventory storage locations."""
from typing import Optional, List, TYPE_CHECKING
from sqlalchemy import String, Integer, Float, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.models.base import Base, TimestampMixin, generate_uuid

if TYPE_CHECKING:
    from backend.app.models.organization import Organization
    from backend.app.models.inventory import Inventory


class Warehouse(Base, TimestampMixin):
    __tablename__ = "warehouses"
    __table_args__ = (
        UniqueConstraint("organization_id", "code", name="uq_org_warehouse_code"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=generate_uuid
    )
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    address: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    country: Mapped[str] = mapped_column(String(100), default="Global", nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, default=10000, nullable=False)
    current_utilization: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # Relationships
    organization: Mapped["Organization"] = relationship("Organization", back_populates="warehouses")
    inventories: Mapped[List["Inventory"]] = relationship("Inventory", back_populates="warehouse", cascade="all, delete-orphan")
