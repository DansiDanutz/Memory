import os, yaml
from typing import Dict, List, Optional

TENANTS_FILE = os.getenv("TENANTS_FILE", "data/tenants/tenants.yaml")

class TenancyState:
    def __init__(self):
        self.tenants: Dict[str, Dict] = {}
        self.phone_index: Dict[str, Dict] = {}
        self.load()

    def load(self):
        self.tenants = {}
        self.phone_index = {}
        try:
            if os.path.exists(TENANTS_FILE):
                data = yaml.safe_load(open(TENANTS_FILE, "r", encoding="utf-8")) or {}
                for t in data.get("tenants", []):
                    tid = t.get("id")
                    if not tid: 
                        continue
                    self.tenants[tid] = t
                    for u in t.get("users", []):
                        phone = u.get("phone")
                        if not phone: 
                            continue
                        self.phone_index[phone] = {
                            "tenant_id": tid,
                            "role": u.get("role", "member"),
                            "department": u.get("department")
                        }
        except Exception:
            # swallow errors to avoid breaking webhook
            self.tenants = {}
            self.phone_index = {}

    def get_user(self, phone: str) -> Optional[Dict]:
        return self.phone_index.get(phone)

    def phones_in_department(self, phone: str) -> List[str]:
        u = self.get_user(phone)
        if not u: return []
        tid = u["tenant_id"]; dep = u.get("department")
        if not dep: return []
        t = self.tenants.get(tid) or {}
        return [x.get("phone") for x in t.get("users", []) if x.get("department")==dep and x.get("phone")]

    def phones_in_tenant(self, phone: str) -> List[str]:
        u = self.get_user(phone)
        if not u: return []
        tid = u["tenant_id"]
        t = self.tenants.get(tid) or {}
        return [x.get("phone") for x in t.get("users", []) if x.get("phone")]

TENANCY = TenancyState()

def reload_tenancy():
    TENANCY.load()
    return True
