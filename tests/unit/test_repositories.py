"""Unit tests for SQLAlchemy 2.0 async repository operations."""
import pytest
from backend.app.models.organization import Organization
from backend.app.models.user import User, UserRole
from backend.app.models.supplier import Supplier
from backend.app.models.warehouse import Warehouse
from backend.app.models.product import Product
from backend.app.models.inventory import Inventory
from backend.app.models.order import Order
from backend.app.models.shipment import Shipment
from backend.app.repositories.organizations import OrganizationRepository
from backend.app.repositories.users import UserRepository
from backend.app.repositories.suppliers import SupplierRepository
from backend.app.repositories.inventory import InventoryRepository
from backend.app.repositories.orders import OrderRepository
from backend.app.repositories.shipments import ShipmentRepository


@pytest.mark.asyncio
async def test_organization_and_user_repository(db_session_factory):
    """Verify Organization and User CRUD via repositories."""
    async with db_session_factory() as session:
        org_repo = OrganizationRepository(session)
        user_repo = UserRepository(session)

        # Create org
        org = Organization(name="Repo Test Corp", slug="repo-test-corp", tier="pro")
        created_org = await org_repo.create(org)
        assert created_org.id is not None
        assert created_org.slug == "repo-test-corp"

        # Lookup org by slug
        found_org = await org_repo.get_by_slug("repo-test-corp")
        assert found_org is not None
        assert found_org.id == created_org.id

        # Create user
        user = User(
            organization_id=created_org.id,
            email="repo_user@test.corp",
            hashed_password="fake_hashed_pwd",
            full_name="Repo User",
            role=UserRole.OPERATOR,
        )
        created_user = await user_repo.create(user)
        assert created_user.id is not None

        # Lookup user by email
        found_user = await user_repo.get_by_email("repo_user@test.corp")
        assert found_user is not None
        assert found_user.id == created_user.id
        assert found_user.role == UserRole.OPERATOR


@pytest.mark.asyncio
async def test_supplier_repository_crud(db_session_factory):
    """Verify Supplier repository CRUD with tenant scoping."""
    async with db_session_factory() as session:
        supplier_repo = SupplierRepository(session)

        # Create supplier
        supplier = Supplier(
            organization_id="default-org-id",
            name="Quantum Logistics Ltd",
            contact_email="quantum@logistics.corp",
            country="Germany",
            tier=2,
            rating=4.5,
        )
        created_sup = await supplier_repo.create(supplier)
        assert created_sup.id is not None
        assert created_sup.name == "Quantum Logistics Ltd"

        # List by tenant
        tenant_suppliers = await supplier_repo.list_by_tenant("default-org-id")
        assert any(s.id == created_sup.id for s in tenant_suppliers)

        # Update
        updated_sup = await supplier_repo.update(created_sup, {"rating": 4.9})
        assert updated_sup.rating == 4.9

        # Delete
        await supplier_repo.delete(created_sup)
        deleted = await supplier_repo.get_by_id(created_sup.id)
        assert deleted is None


@pytest.mark.asyncio
async def test_inventory_and_orders_repositories(db_session_factory):
    """Verify Inventory, Order, and Shipment repositories."""
    async with db_session_factory() as session:
        inv_repo = InventoryRepository(session)
        order_repo = OrderRepository(session)
        shipment_repo = ShipmentRepository(session)

        # Inventory retrieval
        inventories = await inv_repo.list_by_tenant("default-org-id")
        assert len(inventories) > 0
        assert inventories[0].product is not None

        # Order retrieval
        orders = await order_repo.list_by_tenant("default-org-id")
        assert len(orders) > 0
        assert orders[0].order_number == "ORD-TEST-1001"

        # Shipment retrieval
        shipments = await shipment_repo.list_by_tenant("default-org-id")
        assert len(shipments) > 0
        assert shipments[0].tracking_number == "TRK-TEST-9001"
