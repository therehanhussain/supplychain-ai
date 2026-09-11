"""Organization model representing tenant boundaries."""
from typing import List, TYPE_CHECKING
from sqlalchemy import String, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.models.base import Base, TimestampMixin, generate_uuid

if TYPE_CHECKING:
    from backend.app.models.user import User
    from backend.app.models.supplier import Supplier
    from backend.app.models.warehouse import Warehouse
    from backend.app.models.product import Product
    from backend.app.models.order import Order
    from backend.app.models.shipment import Shipment
    from backend.app.models.audit_log import AuditLog


class Organization(Base, TimestampMixin):
    __tablename__ = "organizations"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=generate_uuid
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    tier: Mapped[str] = mapped_column(String(50), default="enterprise", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    users: Mapped[List["User"]] = relationship("User", back_populates="organization", cascade="all, delete-orphan")
    suppliers: Mapped[List["Supplier"]] = relationship("Supplier", back_populates="organization", cascade="all, delete-orphan")
    warehouses: Mapped[List["Warehouse"]] = relationship("Warehouse", back_populates="organization", cascade="all, delete-orphan")
    products: Mapped[List["Product"]] = relationship("Product", back_populates="organization", cascade="all, delete-orphan")
    orders: Mapped[List["Order"]] = relationship("Order", back_populates="organization", cascade="all, delete-orphan")
    shipments: Mapped[List["Shipment"]] = relationship("Shipment", back_populates="organization", cascade="all, delete-orphan")
    audit_logs: Mapped[List["AuditLog"]] = relationship("AuditLog", back_populates="organization", cascade="all, delete-orphan")
