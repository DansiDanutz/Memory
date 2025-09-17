from typing import Literal, Tuple, Optional, Dict
from .model import TENANCY

Role = Literal["owner","admin","manager","member","auditor"]
Scope = Literal["self","department","tenant"]

# allowed roles per scope
DEPT_ROLES = {"owner","admin","manager","auditor"}
TENANT_ROLES = {"owner","admin","auditor"}

# Permission matrix by role
PERMISSIONS = {
    "owner": [
        "memory.create", "memory.read", "memory.update", "memory.delete",
        "memory.search_self", "memory.search_dept", "memory.search_tenant",
        "memory.export", "memory.backup", "memory.restore",
        "audit.read", "audit.write",
        "settings.read", "settings.update",
        "admin.tenants", "admin.users", "admin.system"
    ],
    "admin": [
        "memory.create", "memory.read", "memory.update", "memory.delete",
        "memory.search_self", "memory.search_dept", "memory.search_tenant",
        "memory.export", "memory.backup", "memory.restore",
        "audit.read", "audit.write",
        "settings.read", "settings.update",
        "admin.users"
    ],
    "manager": [
        "memory.create", "memory.read", "memory.update",
        "memory.search_self", "memory.search_dept",
        "memory.export", "memory.backup",
        "audit.read",
        "settings.read"
    ],
    "member": [
        "memory.create", "memory.read",
        "memory.search_self",
        "settings.read"
    ],
    "auditor": [
        "memory.read",
        "memory.search_self", "memory.search_dept", "memory.search_tenant",
        "audit.read",
        "settings.read"
    ]
}

def whoami(phone: str) -> Optional[Dict]:
    return TENANCY.get_user(phone)

def can_search(phone: str, scope: Scope) -> Tuple[bool, str]:
    if scope == "self":
        return True, "self"
    u = TENANCY.get_user(phone)
    if not u:
        return False, "no-tenant"
    role = u.get("role","member")
    if scope == "department":
        return (role in DEPT_ROLES, role)
    if scope == "tenant":
        return (role in TENANT_ROLES, role)
    return False, "invalid-scope"

def can_perform(phone: str, permission: str) -> bool:
    """Check if user has specific permission"""
    u = TENANCY.get_user(phone)
    if not u:
        # Users without tenant can only perform basic actions
        return permission in ["memory.create", "memory.read", "memory.search_self", "settings.read"]
    
    role = u.get("role", "member")
    allowed = PERMISSIONS.get(role, [])
    return permission in allowed
