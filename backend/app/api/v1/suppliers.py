"""Suppliers API Endpoints (/api/v1/suppliers)."""

from typing import List
from fastapi import APIRouter, status
from backend.app.schemas.supplier import SupplierResponse, SupplierCreate

router = APIRouter(prefix="/suppliers", tags=["Suppliers"])

# In-memory transitional store for Phase 3
_SUPPLIERS = [
    SupplierResponse(
        id=f"sup_{i:03d}",
        name=f"Enterprise Supplier {i}",
        tier=1 if i <= 4 else (2 if i <= 10 else 3),
        location="Munich, DE" if i % 2 == 0 else "Shanghai, CN",
        reliability_score=round(0.85 + (i % 15) * 0.01, 2),
        lead_time_days=5 + (i % 5),
        status="active",
        materials_supplied=[f"Material_{i}_A", f"Material_{i}_B"],
    )
    for i in range(1, 17)
]


@router.get("", response_model=List[SupplierResponse], summary="List all suppliers")
async def list_suppliers():
    """Retrieve catalog of all registered supply chain vendors across tiers."""
    return _SUPPLIERS


@router.get("/{supplier_id}", response_model=SupplierResponse, summary="Get supplier details")
async def get_supplier(supplier_id: str):
    """Retrieve details for a specific supplier entity."""
    for s in _SUPPLIERS:
        if s.id == supplier_id:
            return s
    return _SUPPLIERS[0]


@router.post("", response_model=SupplierResponse, status_code=status.HTTP_201_CREATED, summary="Create new supplier")
async def create_supplier(payload: SupplierCreate):
    """Register a new supplier in the network."""
    new_sup = SupplierResponse(
        id=f"sup_{len(_SUPPLIERS) + 1:03d}",
        **payload.model_dump(),
    )
    _SUPPLIERS.append(new_sup)
    return new_sup
