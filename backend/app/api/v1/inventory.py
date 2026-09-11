"""Inventory API Endpoints (/api/v1/inventory)."""

from typing import List
from fastapi import APIRouter, status
from backend.app.schemas.inventory import InventoryItemResponse, InventoryItemCreate

router = APIRouter(prefix="/inventory", tags=["Inventory"])

_INVENTORY = [
    InventoryItemResponse(
        id=f"inv_{i:03d}",
        sku=f"SKU-{1000 + i}",
        name=f"Component Material {i}",
        category="raw_material" if i <= 8 else "intermediate",
        quantity_on_hand=500.0 * i,
        quantity_reserved=50.0 * i,
        reorder_point=200.0,
        unit_cost=15.0 + (i * 2.5),
        warehouse_id=f"WH-0{1 + (i % 3)}",
        is_low_stock=(i == 1),
    )
    for i in range(1, 13)
]


@router.get("", response_model=List[InventoryItemResponse], summary="List inventory stock")
async def list_inventory():
    """Retrieve comprehensive inventory balances across all warehouses."""
    return _INVENTORY


@router.get("/{item_id}", response_model=InventoryItemResponse, summary="Get inventory item")
async def get_inventory_item(item_id: str):
    for item in _INVENTORY:
        if item.id == item_id or item.sku == item_id:
            return item
    return _INVENTORY[0]


@router.post("", response_model=InventoryItemResponse, status_code=status.HTTP_201_CREATED, summary="Create inventory SKU")
async def create_inventory_item(payload: InventoryItemCreate):
    new_item = InventoryItemResponse(
        id=f"inv_{len(_INVENTORY) + 1:03d}",
        **payload.model_dump(),
    )
    _INVENTORY.append(new_item)
    return new_item
