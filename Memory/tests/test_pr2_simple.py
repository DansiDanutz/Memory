#!/usr/bin/env python3
"""
PR-2 Feature Test Suite - Simple HTTP-based tests
"""

import requests
import json
import os

BASE_URL = "http://localhost:5000"

def test_admin_endpoints():
    print("Testing Admin Endpoints...")
    
    # Test GET /admin/tenants
    resp = requests.get(f"{BASE_URL}/admin/tenants")
    assert resp.status_code == 200
    tenants = resp.json()["tenants"]
    assert "acme" in tenants
    assert "globex" in tenants
    assert "techstart" in tenants
    print("✓ GET /admin/tenants returns all 3 tenants")
    
    # Test GET /admin/whoami for different users
    test_cases = [
        ("+15551230001", "acme", "owner", "sales"),  # John Smith - Acme owner
        ("+15551230003", "acme", "manager", "sales"),  # Mike Davis - Acme manager
        ("+15551230005", "acme", "auditor", "finance"),  # Robert Wilson - Acme auditor
        ("+15552340001", "globex", "owner", "operations"),  # James Anderson - Globex owner
        ("+15553450003", "techstart", "manager", "qa"),  # Casey Miller - TechStart manager
    ]
    
    for phone, expected_tenant, expected_role, expected_dept in test_cases:
        resp = requests.get(f"{BASE_URL}/admin/whoami", params={"phone": phone})
        assert resp.status_code == 200
        whoami = resp.json()["whoami"]
        assert whoami["tenant_id"] == expected_tenant
        assert whoami["role"] == expected_role
        assert whoami["department"] == expected_dept
        print(f"✓ Whoami for {phone}: {expected_role} in {expected_tenant}/{expected_dept}")
    
    # Test reload endpoint
    resp = requests.post(f"{BASE_URL}/admin/tenants/reload")
    assert resp.status_code == 200
    assert resp.json()["reloaded"] == True
    print("✓ POST /admin/tenants/reload works")
    
    # Test whoami for non-existent user
    resp = requests.get(f"{BASE_URL}/admin/whoami", params={"phone": "+19999999999"})
    assert resp.status_code == 200
    assert resp.json()["whoami"] is None
    print("✓ Whoami returns None for non-existent user")
    
    print("\nAll admin endpoints tested successfully!\n")

def test_file_structure():
    print("Testing File Structure...")
    
    # Check audit directory
    assert os.path.exists("data/audit")
    print("✓ Audit directory exists")
    
    # Check tenants.yaml
    assert os.path.exists("data/tenants/tenants.yaml")
    with open("data/tenants/tenants.yaml", "r") as f:
        content = f.read()
        assert "acme" in content
        assert "globex" in content
        assert "techstart" in content
    print("✓ tenants.yaml contains all 3 organizations")
    
    # Check tenancy module files
    assert os.path.exists("app/tenancy/__init__.py")
    assert os.path.exists("app/tenancy/model.py")
    assert os.path.exists("app/tenancy/rbac.py")
    print("✓ Tenancy module files exist")
    
    # Check memory search module
    assert os.path.exists("app/memory/search_multi.py")
    print("✓ Multi-search module exists")
    
    # Check audit module
    assert os.path.exists("app/audit.py")
    print("✓ Audit module exists")
    
    print("\nFile structure verified successfully!\n")

def test_health_endpoints():
    print("Testing Health Endpoints...")
    
    # Test root endpoint
    resp = requests.get(f"{BASE_URL}/")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
    print("✓ Root endpoint returns ok")
    
    # Test health endpoint
    resp = requests.get(f"{BASE_URL}/health")
    assert resp.status_code == 200
    health = resp.json()
    assert health["status"] == "healthy"
    assert health["service"] == "whatsapp-memory-bot"
    print("✓ Health endpoint returns healthy status")
    
    # Test admin status endpoint
    resp = requests.get(f"{BASE_URL}/admin/status")
    assert resp.status_code == 200
    status = resp.json()
    assert "cpu_percent" in status
    assert "mem" in status
    assert "pid" in status
    print("✓ Admin status endpoint returns system metrics")
    
    print("\nHealth endpoints tested successfully!\n")

def main():
    print("=" * 60)
    print("PR-2 Feature Test Suite (Simple)")
    print("=" * 60)
    
    try:
        # Test each feature
        test_health_endpoints()
        test_admin_endpoints()
        test_file_structure()
        
        print("=" * 60)
        print("✓ ALL PR-2 FEATURES TESTED SUCCESSFULLY!")
        print("=" * 60)
        print("\nFeatures verified:")
        print("• Multi-tenancy with 3 organizations (acme, globex, techstart)")
        print("• Admin endpoints for tenant management")
        print("• Tenant configuration with departments and roles")
        print("• Audit logging infrastructure")
        print("• RBAC module structure")
        print("• Cross-scope search module")
        print("\nPR-2 Overlay Integration Complete!")
        print("\nKey Commands Available:")
        print("• whoami - Check user's tenant and role")
        print("• search dept: <query> - Search within department (requires proper role)")
        print("• search tenant: <query> - Search within tenant (requires admin/owner/auditor)")
        print("• search: <query> - Self-scope search")
        print("• enroll: <passphrase> - Set voice authentication")
        print("• verify: <passphrase> - Unlock secret tiers")
        
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        return 1
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())