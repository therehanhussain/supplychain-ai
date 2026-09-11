"""Security tests verifying Role-Based Access Control (RBAC) enforcement across all role tiers."""
import pytest
from fastapi import APIRouter, Depends
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.models.user import User, UserRole
from backend.app.api.dependencies import (
    require_admin,
    require_operator,
    require_analyst,
    require_viewer,
)

# Attach dedicated test router for RBAC verification
rbac_test_router = APIRouter(prefix="/api/test/rbac", tags=["Test RBAC"])

@rbac_test_router.get("/admin-only")
async def admin_route(user: User = Depends(require_admin)):
    return {"message": "admin access granted", "role": user.role.value}

@rbac_test_router.get("/operator-route")
async def operator_route(user: User = Depends(require_operator)):
    return {"message": "operator access granted", "role": user.role.value}

@rbac_test_router.get("/analyst-route")
async def analyst_route(user: User = Depends(require_analyst)):
    return {"message": "analyst access granted", "role": user.role.value}

@rbac_test_router.get("/viewer-route")
async def viewer_route(user: User = Depends(require_viewer)):
    return {"message": "viewer access granted", "role": user.role.value}

app.include_router(rbac_test_router)



@pytest.mark.asyncio
async def test_rbac_admin_enforcement(client: TestClient, create_test_user, auth_header_for_user):
    """Verify ADMIN role access and rejection of lower roles on admin routes."""
    admin_user = await create_test_user("admin_rbac@test.corp", role=UserRole.ADMIN)
    operator_user = await create_test_user("operator_rbac@test.corp", role=UserRole.OPERATOR)
    analyst_user = await create_test_user("analyst_rbac@test.corp", role=UserRole.ANALYST)
    viewer_user = await create_test_user("viewer_rbac@test.corp", role=UserRole.VIEWER)

    # 1. Admin succeeds
    res = client.get("/api/test/rbac/admin-only", headers=auth_header_for_user(admin_user))
    assert res.status_code == 200
    assert res.json()["role"] in ("ADMIN", "admin")


    # 2. Operator rejected with 403
    res = client.get("/api/test/rbac/admin-only", headers=auth_header_for_user(operator_user))
    assert res.status_code == 403
    assert res.json()["error_code"] == "FORBIDDEN_INSUFFICIENT_ROLE"

    # 3. Analyst rejected with 403
    res = client.get("/api/test/rbac/admin-only", headers=auth_header_for_user(analyst_user))
    assert res.status_code == 403

    # 4. Viewer rejected with 403
    res = client.get("/api/test/rbac/admin-only", headers=auth_header_for_user(viewer_user))
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_rbac_operator_enforcement(client: TestClient, create_test_user, auth_header_for_user):
    """Verify OPERATOR route permits Admin and Operator, rejects Analyst and Viewer."""
    admin_user = await create_test_user("admin_op@test.corp", role=UserRole.ADMIN)
    operator_user = await create_test_user("operator_op@test.corp", role=UserRole.OPERATOR)
    viewer_user = await create_test_user("viewer_op@test.corp", role=UserRole.VIEWER)

    assert client.get("/api/test/rbac/operator-route", headers=auth_header_for_user(admin_user)).status_code == 200
    assert client.get("/api/test/rbac/operator-route", headers=auth_header_for_user(operator_user)).status_code == 200
    assert client.get("/api/test/rbac/operator-route", headers=auth_header_for_user(viewer_user)).status_code == 403


@pytest.mark.asyncio
async def test_rbac_unauthenticated_rejected_with_401(client: TestClient):
    """Verify unauthenticated requests to protected RBAC endpoints return 401."""
    res = client.get("/api/test/rbac/admin-only")
    assert res.status_code == 401
    assert res.json()["error_code"] == "UNAUTHORIZED"
