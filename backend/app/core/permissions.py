"""Manufacturing & Inventory Granular Permissions and Role Mappings."""
from typing import Set, Dict
from backend.app.models.user import UserRole


# Permission Constants
PERM_INVENTORY_RECEIVE = "inventory:receive"
PERM_INVENTORY_ISSUE = "inventory:issue"
PERM_INVENTORY_CONSUME = "inventory:consume"
PERM_INVENTORY_RETURN = "inventory:return"
PERM_INVENTORY_TRANSFER = "inventory:transfer"
PERM_INVENTORY_ADJUST = "inventory:adjust"
PERM_INVENTORY_WASTAGE = "inventory:wastage"
PERM_INVENTORY_VIEW = "inventory:view_activity"

PERM_PRODUCTION_MANAGE = "production:manage"
PERM_PRODUCTION_VIEW = "production:view"


# Role-to-Permissions Mapping
ROLE_PERMISSIONS: Dict[UserRole, Set[str]] = {
    UserRole.ADMIN: {
        PERM_INVENTORY_RECEIVE,
        PERM_INVENTORY_ISSUE,
        PERM_INVENTORY_CONSUME,
        PERM_INVENTORY_RETURN,
        PERM_INVENTORY_TRANSFER,
        PERM_INVENTORY_ADJUST,
        PERM_INVENTORY_WASTAGE,
        PERM_INVENTORY_VIEW,
        PERM_PRODUCTION_MANAGE,
        PERM_PRODUCTION_VIEW,
    },
    UserRole.OPERATOR: {
        PERM_INVENTORY_RECEIVE,
        PERM_INVENTORY_ISSUE,
        PERM_INVENTORY_CONSUME,
        PERM_INVENTORY_RETURN,
        PERM_INVENTORY_TRANSFER,
        PERM_INVENTORY_WASTAGE,
        PERM_INVENTORY_VIEW,
        PERM_PRODUCTION_VIEW,
    },
    UserRole.ANALYST: {
        PERM_INVENTORY_VIEW,
        PERM_PRODUCTION_VIEW,
    },
    UserRole.VIEWER: {
        PERM_INVENTORY_VIEW,
        PERM_PRODUCTION_VIEW,
    },
}


def user_has_permission(role: UserRole, permission: str) -> bool:
    """Check if a given user role possesses a granular permission."""
    perms = ROLE_PERMISSIONS.get(role, set())
    return permission in perms
