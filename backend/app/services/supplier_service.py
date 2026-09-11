"""Supplier domain service executing business logic and tenant isolation."""
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.models.supplier import Supplier
from backend.app.repositories.suppliers import SupplierRepository
from backend.app.schemas.supplier import SupplierCreate, SupplierResponse
from backend.app.core.exceptions import AppException


class SupplierService:
    def __init__(self, db: AsyncSession, organization_id: str):
        self.db = db
        self.organization_id = organization_id
        self.repo = SupplierRepository(db)

    async def list_suppliers(
        self,
        tier: Optional[int] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[SupplierResponse]:
        """List organization-owned suppliers."""
        models = await self.repo.list_by_org(
            organization_id=self.organization_id,
            tier=tier,
            status=status,
            skip=skip,
            limit=limit,
        )
        return [
            SupplierResponse(
                id=m.id,
                name=m.name,
                tier=m.tier,
                contact_email=m.contact_email,
                location=m.country,
                country=m.country,
                reliability_score=m.rating / 5.0 if m.rating else 0.95,
                rating=m.rating,
                lead_time_days=m.lead_time_days,
                status=m.status,
                created_at=m.created_at,
                materials_supplied=[],
            )
            for m in models
        ]

    async def get_supplier(self, supplier_id: str) -> SupplierResponse:
        """Fetch a specific supplier with tenant validation."""
        m = await self.repo.get_by_id_and_org(supplier_id, self.organization_id)
        if not m:
            raise AppException(
                message=f"Supplier '{supplier_id}' not found in current organization.",
                status_code=404,
                error_code="SUPPLIER_NOT_FOUND",
            )
        return SupplierResponse(
            id=m.id,
            name=m.name,
            tier=m.tier,
            contact_email=m.contact_email,
            location=m.country,
            country=m.country,
            reliability_score=m.rating / 5.0 if m.rating else 0.95,
            rating=m.rating,

            lead_time_days=m.lead_time_days,
            status=m.status,
            created_at=m.created_at,
            materials_supplied=[],
        )

    async def create_supplier(self, payload: SupplierCreate) -> SupplierResponse:
        """Create a new supplier associated with the current organization."""
        supplier = Supplier(
            organization_id=self.organization_id,
            name=payload.name,
            tier=payload.tier,
            contact_email=payload.contact_email,
            country=payload.country or payload.location or "Global",
            rating=payload.reliability_score * 5.0 if payload.reliability_score else 5.0,
            lead_time_days=payload.lead_time_days,
            status=payload.status,
            is_active=True,
        )
        m = await self.repo.create(supplier)
        return SupplierResponse(
            id=m.id,
            name=m.name,
            tier=m.tier,
            contact_email=m.contact_email,
            location=m.country,
            country=m.country,
            reliability_score=payload.reliability_score,
            rating=m.rating,
            lead_time_days=m.lead_time_days,
            status=m.status,
            created_at=m.created_at,
            materials_supplied=[],
        )

    async def update_supplier(self, supplier_id: str, payload) -> SupplierResponse:
        """Update supplier fields with tenant isolation."""
        m = await self.repo.get_by_id_and_org(supplier_id, self.organization_id)
        if not m:
            raise AppException(
                message=f"Supplier '{supplier_id}' not found.",
                status_code=404,
                error_code="SUPPLIER_NOT_FOUND",
            )
        values = {}
        if getattr(payload, "name", None) is not None:
            values["name"] = payload.name
        if getattr(payload, "tier", None) is not None:
            values["tier"] = payload.tier
        if getattr(payload, "contact_email", None) is not None:
            values["contact_email"] = payload.contact_email
        if getattr(payload, "country", None) is not None:
            values["country"] = payload.country
        elif getattr(payload, "location", None) is not None:
            values["country"] = payload.location
        if getattr(payload, "lead_time_days", None) is not None:
            values["lead_time_days"] = payload.lead_time_days
        if getattr(payload, "status", None) is not None:
            values["status"] = payload.status
        if getattr(payload, "rating", None) is not None:
            values["rating"] = payload.rating
        elif getattr(payload, "reliability_score", None) is not None:
            values["rating"] = payload.reliability_score * 5.0

        updated_m = await self.repo.update(m, values)
        return SupplierResponse(
            id=updated_m.id,
            name=updated_m.name,
            tier=updated_m.tier,
            contact_email=updated_m.contact_email,
            location=updated_m.country,
            country=updated_m.country,
            reliability_score=updated_m.rating / 5.0 if updated_m.rating else 0.95,
            rating=updated_m.rating,
            lead_time_days=updated_m.lead_time_days,
            status=updated_m.status,
            created_at=updated_m.created_at,
            materials_supplied=[],
        )


    async def delete_supplier(self, supplier_id: str) -> bool:
        """Delete supplier ensuring organization ownership."""
        deleted = await self.repo.delete_by_id_and_org(supplier_id, self.organization_id)
        if not deleted:
            raise AppException(
                message=f"Supplier '{supplier_id}' not found.",
                status_code=404,
                error_code="SUPPLIER_NOT_FOUND",
            )
        return True

