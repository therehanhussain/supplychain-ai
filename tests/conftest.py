"""Pytest Fixtures and Global Test Configuration for Phase 4."""

import os
import asyncio
from typing import AsyncGenerator, Generator
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

# Enforce testing environment variables prior to importing application modules
TEST_DB_FILE = "./test_phase4_suite.db"
os.environ["ENVIRONMENT"] = "testing"
os.environ["DEBUG"] = "false"
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{TEST_DB_FILE}"
os.environ["JWT_SECRET"] = "testing_secret_key_with_at_least_32_chars_long!"
os.environ["CORS_ORIGINS"] = "http://localhost:3000,http://localhost:5173,https://frontend-pi-hazel-83.vercel.app"
os.environ["OPENAI_API_KEY"] = ""
os.environ["LLM_MODE"] = "mock"

from backend.app.main import app
from backend.app.core.config import settings
from backend.app.core.database import get_db
from backend.app.models.base import Base
import backend.app.models  # Register all SQLAlchemy models
from backend.app.core.security import create_access_token, hash_password
from backend.app.models.organization import Organization
from backend.app.models.user import User, UserRole

# Create dedicated async engine for test suite
test_engine = create_async_engine(
    f"sqlite+aiosqlite:///{TEST_DB_FILE}",
    echo=False,
    future=True,
)

TestingSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """Create all schema tables before test suite and cleanup afterwards."""
    # Ensure fresh db
    if os.path.exists(TEST_DB_FILE):
        try:
            os.remove(TEST_DB_FILE)
        except OSError:
            pass

    async def init_models():
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        # Seed default test entities
        from backend.app.models.organization import Organization
        from backend.app.models.supplier import Supplier
        from backend.app.models.warehouse import Warehouse
        from backend.app.models.product import Product
        from backend.app.models.inventory import Inventory
        from backend.app.models.order import Order
        from backend.app.models.shipment import Shipment

        async with TestingSessionLocal() as session:
            # Check if default org exists
            org = Organization(
                id="default-org-id",
                name="Default Organization",
                slug="default-org",
                tier="enterprise",
            )
            session.add(org)
            await session.flush()

            sup = Supplier(
                id="sup-test-001",
                organization_id=org.id,
                name="Apex Global Supplier",
                contact_email="supply@apex.corp",
                country="USA",
                tier=1,
                rating=4.8,
            )
            wh = Warehouse(
                id="wh-test-001",
                organization_id=org.id,
                name="Central Distribution Center",
                code="CDC-01",
                city="Chicago",
                country="USA",
            )
            prod = Product(
                id="prod-test-001",
                organization_id=org.id,
                sku="SKU-CHIP-01",
                name="Semiconductor Controller",
                category="Electronics",
                unit_price=250.0,
                unit_cost=180.0,
            )
            session.add_all([sup, wh, prod])
            await session.flush()

            inv = Inventory(
                id="inv-test-001",
                organization_id=org.id,
                product_id=prod.id,
                warehouse_id=wh.id,
                quantity=500,
                safety_stock=50,
                reorder_point=100,
                reorder_quantity=200,
            )
            order = Order(
                id="ord-test-001",
                organization_id=org.id,
                supplier_id=sup.id,
                order_number="ORD-TEST-1001",
                status="pending",
                total_amount=15000.00,
                currency="USD",
            )
            session.add_all([inv, order])
            await session.flush()

            shipment = Shipment(
                id="shp-test-001",
                organization_id=org.id,
                order_id=order.id,
                tracking_number="TRK-TEST-9001",
                carrier="Apex Freight",
                origin="Chicago CDC",
                destination="Detroit Hub",
                status="in_transit",
            )
            session.add(shipment)
            await session.commit()


    asyncio.run(init_models())

    # FastAPI dependency override
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with TestingSessionLocal() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    app.dependency_overrides[get_db] = override_get_db

    yield

    app.dependency_overrides.clear()

    async def cleanup_engine():
        await test_engine.dispose()

    asyncio.run(cleanup_engine())

    if os.path.exists(TEST_DB_FILE):
        try:
            os.remove(TEST_DB_FILE)
        except OSError:
            pass


@pytest.fixture(scope="session")
def client():
    """Shared FastAPI test client instance with test database overridden."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def db_session_factory():
    """Returns factory for test async sessions."""
    return TestingSessionLocal


@pytest.fixture
def create_test_user():
    """Factory fixture to create an authenticated test user with a specific role and organization."""
    async def _create(
        email: str,
        password: str = "SecretPassword123!",
        role: UserRole = UserRole.ADMIN,
        org_id: str = "default-org-id",
        full_name: str = "Test User",
    ) -> User:
        async with TestingSessionLocal() as session:
            user = User(
                organization_id=org_id,
                email=email,
                hashed_password=hash_password(password),
                full_name=full_name,
                role=role,
                is_active=True,
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            return user
    return _create


@pytest.fixture
def auth_header_for_user():
    """Factory fixture to create Authorization Bearer headers for a given user."""
    def _header(user: User) -> dict:
        token = create_access_token(
            subject=user.id,
            claims={
                "org_id": user.organization_id,
                "role": user.role.value,
                "email": user.email,
            },
        )
        return {"Authorization": f"Bearer {token}"}
    return _header
