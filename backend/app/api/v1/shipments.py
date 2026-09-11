"""Shipments & Logistics API Endpoints (/api/v1/shipments)."""

from typing import List
from fastapi import APIRouter, status
from backend.app.schemas.shipment import ShipmentResponse, ShipmentCreate

router = APIRouter(prefix="/shipments", tags=["Shipments"])

_SHIPMENTS = [
    ShipmentResponse(
        id=f"shp_{i:03d}",
        order_id=f"ord_{i:03d}",
        carrier="DHL Supply Chain" if i % 2 == 0 else "Maersk Logistics",
        tracking_number=f"TRK-90812{i}",
        origin="Shanghai Port Warehouse",
        destination="Frankfurt Fulfillment Hub",
        status="in_transit" if i % 2 == 0 else "delivered",
    )
    for i in range(1, 7)
]


@router.get("", response_model=List[ShipmentResponse], summary="List active shipments")
async def list_shipments():
    return _SHIPMENTS


@router.get("/{shipment_id}", response_model=ShipmentResponse, summary="Get shipment details")
async def get_shipment(shipment_id: str):
    for s in _SHIPMENTS:
        if s.id == shipment_id or s.tracking_number == shipment_id:
            return s
    return _SHIPMENTS[0]


@router.post("", response_model=ShipmentResponse, status_code=status.HTTP_201_CREATED, summary="Create shipment record")
async def create_shipment(payload: ShipmentCreate):
    new_shipment = ShipmentResponse(
        id=f"shp_{len(_SHIPMENTS) + 1:03d}",
        **payload.model_dump(),
    )
    _SHIPMENTS.append(new_shipment)
    return new_shipment
