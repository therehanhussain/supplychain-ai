"""Shipment model tracking in-transit goods and logistics telemetry."""
from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Float, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.models.base import Base, TimestampMixin, generate_uuid

if TYPE_CHECKING:
    from backend.app.models.organization import Organization
    from backend.app.models.order import Order


class Shipment(Base, TimestampMixin):
    __tablename__ = "shipments"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=generate_uuid
    )
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    order_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True
    )
    tracking_number: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    carrier: Mapped[str] = mapped_column(String(100), default="Global Logistics", nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="in_transit", nullable=False, index=True)
    origin: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    destination: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    estimated_delivery: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    actual_delivery: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    current_lat: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    current_lng: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Relationships
    organization: Mapped["Organization"] = relationship("Organization", back_populates="shipments")
    order: Mapped["Order"] = relationship("Order", back_populates="shipments")
