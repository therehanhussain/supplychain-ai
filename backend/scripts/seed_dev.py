"""Development seed script to populate sample organizations, users, and supply chain data.

Usage:
    python backend/scripts/seed_dev.py
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
root_path = Path(__file__).resolve().parents[2]
if str(root_path) not in sys.path:
    sys.path.insert(0, str(root_path))

from sqlalchemy import select
from backend.app.core.database import AsyncSessionLocal, engine
from backend.app.core.security import hash_password
from backend.app.models.base import Base
from backend.app.models.organization import Organization
from backend.app.models.user import User, UserRole
from backend.app.models.supplier import Supplier
from backend.app.models.warehouse import Warehouse
from backend.app.models.product import Product
from backend.app.models.inventory import Inventory
from backend.app.models.order import Order, OrderItem
from backend.app.models.shipment import Shipment


async def seed_development_data():
    """Populate initial development organization and realistic entities."""
    print("Beginning development database seeding...")

    async with engine.begin() as conn:
        # Ensure schema tables exist
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        # 1. Organization
        org_slug = "acme-global"
        res = await session.execute(select(Organization).where(Organization.slug == org_slug))
        org = res.scalar_one_or_none()
        if not org:
            org = Organization(
                name="Acme Global Logistics & Manufacturing",
                slug=org_slug,
                tier="enterprise",
                is_active=True,
            )
            session.add(org)
            await session.flush()
            print(f"Created Organization: {org.name} ({org.id})")
        else:
            print(f"Organization exists: {org.name}")

        # Also create Default Organization for unauthenticated development fallbacks
        def_res = await session.execute(select(Organization).where(Organization.slug == "default-org"))
        def_org = def_res.scalar_one_or_none()
        if not def_org:
            def_org = Organization(
                name="Default Organization",
                slug="default-org",
                tier="standard",
                is_active=True,
            )
            session.add(def_org)
            await session.flush()

        # 2. Users for all 4 RBAC roles
        users_data = [
            ("admin@supplychain.local", "Admin User", UserRole.ADMIN, "AdminPassword2026!"),
            ("operator@supplychain.local", "Logistics Operator", UserRole.OPERATOR, "OperatorPassword2026!"),
            ("analyst@supplychain.local", "Planning Analyst", UserRole.ANALYST, "AnalystPassword2026!"),
            ("viewer@supplychain.local", "Auditor Viewer", UserRole.VIEWER, "ViewerPassword2026!"),
        ]

        for email, name, role, plain_pwd in users_data:
            u_res = await session.execute(select(User).where(User.email == email))
            existing_user = u_res.scalar_one_or_none()
            if not existing_user:
                new_user = User(
                    organization_id=org.id,
                    email=email,
                    hashed_password=hash_password(plain_pwd),
                    full_name=name,
                    role=role,
                    is_active=True,
                )
                session.add(new_user)
                print(f"Created User: {email} [Role: {role.value}]")

        # 3. Suppliers
        suppliers_data = [
            ("Apex Silicon Foundry", 1, "Munich, DE", 0.98, 5, "active"),
            ("Shenzhen Micro Precision", 2, "Shenzhen, CN", 0.92, 10, "active"),
            ("Kyoto Lithium Systems", 1, "Kyoto, JP", 0.95, 7, "active"),
            ("Rhine Polymer Solutions", 3, "Frankfurt, DE", 0.88, 14, "active"),
        ]
        created_suppliers = []
        for s_name, tier, country, rating_ratio, lead_time, status in suppliers_data:
            s_res = await session.execute(
                select(Supplier).where(Supplier.organization_id == org.id, Supplier.name == s_name)
            )
            supplier = s_res.scalar_one_or_none()
            if not supplier:
                supplier = Supplier(
                    organization_id=org.id,
                    name=s_name,
                    tier=tier,
                    country=country,
                    rating=rating_ratio * 5.0,
                    lead_time_days=lead_time,
                    status=status,
                )
                session.add(supplier)
                await session.flush()
                print(f"Created Supplier: {s_name} (Tier {tier})")
            created_suppliers.append(supplier)

        # 4. Warehouses
        warehouses_data = [
            ("WH-EU-01", "Munich Central Hub", "Bavaria Logistics Park 1", "Munich", "Germany", 25000),
            ("WH-APAC-01", "Shenzhen Distribution Depot", "Nanshan Port Way 88", "Shenzhen", "China", 40000),
        ]
        created_warehouses = []
        for code, w_name, addr, city, country, cap in warehouses_data:
            w_res = await session.execute(
                select(Warehouse).where(Warehouse.organization_id == org.id, Warehouse.code == code)
            )
            wh = w_res.scalar_one_or_none()
            if not wh:
                wh = Warehouse(
                    organization_id=org.id,
                    code=code,
                    name=w_name,
                    address=addr,
                    city=city,
                    country=country,
                    capacity=cap,
                )
                session.add(wh)
                await session.flush()
                print(f"Created Warehouse: {code} - {w_name}")
            created_warehouses.append(wh)

        # 5. Products
        products_data = [
            ("SKU-WAFER-300", "300mm Monocrystalline Silicon Wafer", "Raw Material", 45.00, 32.00),
            ("SKU-CHIP-MC01", "ARM Microcontroller Module", "Intermediate", 18.50, 11.20),
            ("SKU-BATT-LFP", "LFP 48V Battery Cell Module", "Intermediate", 120.00, 85.00),
            ("SKU-INVERT-X1", "Industrial Hybrid Inverter 5kW", "Finished Good", 650.00, 480.00),
        ]
        created_products = []
        for sku, p_name, cat, price, cost in products_data:
            p_res = await session.execute(
                select(Product).where(Product.organization_id == org.id, Product.sku == sku)
            )
            prod = p_res.scalar_one_or_none()
            if not prod:
                prod = Product(
                    organization_id=org.id,
                    sku=sku,
                    name=p_name,
                    category=cat,
                    unit_price=price,
                    unit_cost=cost,
                )
                session.add(prod)
                await session.flush()
                print(f"Created Product: {sku} - {p_name}")
            created_products.append(prod)

        # 6. Inventory Records
        if created_warehouses and created_products:
            for i, prod in enumerate(created_products):
                target_wh = created_warehouses[i % len(created_warehouses)]
                inv_res = await session.execute(
                    select(Inventory).where(
                        Inventory.organization_id == org.id,
                        Inventory.warehouse_id == target_wh.id,
                        Inventory.product_id == prod.id,
                    )
                )
                inv = inv_res.scalar_one_or_none()
                if not inv:
                    inv = Inventory(
                        organization_id=org.id,
                        warehouse_id=target_wh.id,
                        product_id=prod.id,
                        quantity=500 * (i + 1),
                        safety_stock=100,
                        reorder_point=200,
                    )
                    session.add(inv)
                    print(f"Created Inventory: {prod.sku} @ {target_wh.code} (Qty: {inv.quantity})")

        # 7. Orders & Order Items
        if created_suppliers and created_products:
            ord_res = await session.execute(
                select(Order).where(Order.organization_id == org.id, Order.order_number == "ORD-DEV-1001")
            )
            order = ord_res.scalar_one_or_none()
            if not order:
                order = Order(
                    organization_id=org.id,
                    supplier_id=created_suppliers[0].id,
                    order_number="ORD-DEV-1001",
                    status="shipped",
                    total_amount=4500.00,
                    currency="USD",
                )
                session.add(order)
                await session.flush()

                item = OrderItem(
                    order_id=order.id,
                    product_id=created_products[0].id,
                    quantity=100,
                    unit_price=45.00,
                    total_price=4500.00,
                )
                session.add(item)
                print(f"Created Order: {order.order_number}")

                # 8. Shipment
                shipment = Shipment(
                    organization_id=org.id,
                    order_id=order.id,
                    tracking_number="TRK-DHL-984712093",
                    carrier="DHL Express",
                    origin="Munich Central Hub",
                    destination="Shenzhen Distribution Depot",
                    status="in_transit",
                    current_lat=48.1351,
                    current_lng=11.5820,
                )
                session.add(shipment)
                print(f"Created Shipment: {shipment.tracking_number}")

        await session.commit()
        print("Development database seeding complete!")


if __name__ == "__main__":
    asyncio.run(seed_development_data())
