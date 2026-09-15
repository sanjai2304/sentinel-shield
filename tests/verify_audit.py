"""Verification script to inspect real logged audit entries."""
import urllib.request
import json

def verify():
    # 1. Login as admin
    login_payload = json.dumps({"username": "admin", "password": "AdminSecret123!"}).encode()
    req = urllib.request.Request("http://127.0.0.1:8000/api/v1/auth/login", data=login_payload, headers={"Content-Type": "application/json"})
    res = urllib.request.urlopen(req)
    admin_token = json.loads(res.read().decode())["access_token"]

    # 2. Query audit logs
    audit_req = urllib.request.Request("http://127.0.0.1:8000/api/v1/audit-logs/?limit=10", headers={"Authorization": f"Bearer {admin_token}"})
    audit_res = urllib.request.urlopen(audit_req)
    logs = json.loads(audit_res.read().decode())

    print(f"=== AUDIT LOGS VERIFICATION ({len(logs)} entries retrieved) ===")
    for i, log in enumerate(logs, 1):
        print(f"\n[Entry #{i}]")
        print(f"  Timestamp (WHEN)    : {log['timestamp']}")
        print(f"  Actor (WHO)         : {log['actor_username']} (Role: {log['actor_role']})")
        print(f"  Target (WHAT)       : {log['target_resource']} (Classification: {log['resource_classification']})")
        print(f"  Action / Route      : {log['action']} {log['http_method']} {log['route_path']}")
        print(f"  Client IP           : {log['client_ip']}")
        print(f"  Response Status     : {log['response_status']}")

if __name__ == "__main__":
    verify()
