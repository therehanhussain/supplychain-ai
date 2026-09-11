"""Orders API Endpoints (/api/v1/orders)."""

from typing import List
from fastapi import APIRouter, status
from backend.app.schemas.order import OrderResponse, OrderCreate, OrderItem

router = APIRouter(prefix="/orders", tags=["Orders"])

_ORDERS = [
    OrderResponse(
        id=f"ord_{i:03d}",
        customer_name=f"Enterprise Client {i}",
        supplier_id=f"sup_{1 + (i % 4):03d}",
        items=[
            OrderItem(product_id=f"prod_{i}", product_name=f"Assembly Module {i}", quantity=100.0, unit_price=45.0)
        ],
        total_amount=4500.0,
        status="confirmed" if i % 2 == 0 else "pending",
    )
    for i in range(1, 9)
]


@router.get("", response_model=List[OrderResponse], summary="List purchase & sales orders")
async def list_orders():
    return _ORDERS


@router.get("/{order_id}", response_model=OrderResponse, summary="Get order details")
async def get_order(order_id: str):
    for o in _ORDERS:
        if o.id == order_id:
            return o
    return _ORDERS[0]


@router.post("", response_model=OrderResponse, status_code=status.HTTP_201_CREATED, summary="Create order")
async def create_order(payload: OrderCreate):
    new_order = OrderResponse(
        id=f"ord_{len(_ORDERS) + 1:03d}",
        **payload.model_dump(),
    )
    _ORDERS.append(new_order)
    return new_order
