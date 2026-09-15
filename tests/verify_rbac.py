"""Verification script for non-admin RBAC enforcement."""
import urllib.request
import urllib.error
import json

def verify():
    # 1. Login as analyst_bob
    login_payload = json.dumps({"username": "analyst_bob", "password": "AnalystBob123!"}).encode()
    req = urllib.request.Request("http://127.0.0.1:8000/api/v1/auth/login", data=login_payload, headers={"Content-Type": "application/json"})
    res = urllib.request.urlopen(req)
    analyst_data = json.loads(res.read().decode())
    token = analyst_data["access_token"]
    role = analyst_data["role"]
    username = analyst_data["username"]
    print("=== STEP 1: AUTHENTICATED AS NON-ADMIN ROLE ===")
    print(f"User: {username} | Role: {role} | Department: {analyst_data.get('department')}")

    # 2. Attempt to access admin-only Audit Logs as Analyst
    print("\n=== STEP 2: ANALYST ATTEMPTS ACCESS TO ADMIN AUDIT LOGS (/api/v1/audit-logs/) ===")
    audit_req = urllib.request.Request("http://127.0.0.1:8000/api/v1/audit-logs/", headers={"Authorization": f"Bearer {token}"})
    try:
        urllib.request.urlopen(audit_req)
        print("FAIL: Request succeeded unexpectedly!")
    except urllib.error.HTTPError as e:
        print(f"Status Code: {e.code} ({e.reason})")
        print(f"Response: {e.read().decode()}")

    # 3. Attempt to create resource as Analyst (Admin-only POST /api/v1/resources/)
    print("\n=== STEP 3: ANALYST ATTEMPTS ADMIN ACTION (POST /api/v1/resources/) ===")
    create_payload = json.dumps({"resource_key": "ROGUE_DB", "name": "Rogue Database", "resource_type": "DATABASE", "sensitivity_level": "RESTRICTED"}).encode()
    create_req = urllib.request.Request("http://127.0.0.1:8000/api/v1/resources/", data=create_payload, headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    try:
        urllib.request.urlopen(create_req)
        print("FAIL: Request succeeded unexpectedly!")
    except urllib.error.HTTPError as e:
        print(f"Status Code: {e.code} ({e.reason})")
        print(f"Response: {e.read().decode()}")

    # 4. Unauthenticated request (no token)
    print("\n=== STEP 4: UNAUTHENTICATED REQUEST (GET /api/v1/resources/) ===")
    unauth_req = urllib.request.Request("http://127.0.0.1:8000/api/v1/resources/")
    try:
        urllib.request.urlopen(unauth_req)
        print("FAIL: Request succeeded unexpectedly!")
    except urllib.error.HTTPError as e:
        print(f"Status Code: {e.code} ({e.reason})")
        print(f"Response: {e.read().decode()}")

if __name__ == "__main__":
    verify()
