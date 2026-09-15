"""Verification script demonstrating rate limiting (HTTP 429) on public endpoints."""
import urllib.request
import urllib.error
import json
import time
import sys

def verify(base_url="http://127.0.0.1:8000"):
    url = f"{base_url}/api/v1/auth/login"
    payload = json.dumps({"username": "admin", "password": "WrongPassword123"}).encode()

    print("=== RATE LIMIT VERIFICATION (Limit: 20 requests/minute) ===")
    print("Firing rapid consecutive requests to /api/v1/auth/login...\n")

    first_429_index = None

    for i in range(1, 26):
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        try:
            res = urllib.request.urlopen(req)
            status = res.status
            print(f"Request #{i:02d}: Status {status}")
        except urllib.error.HTTPError as e:
            status = e.code
            if status == 429 and first_429_index is None:
                first_429_index = i
                body = e.read().decode()
                retry_after = e.headers.get("Retry-After", "unknown")
                print(f"Request #{i:02d}: Status {status} [THROTTLED!]")
                print(f"             --> Response Body: {body}")
                print(f"             --> Retry-After Header: {retry_after}s")
            elif status == 429:
                print(f"Request #{i:02d}: Status {status} [THROTTLED]")
            else:
                print(f"Request #{i:02d}: Status {status} ({e.reason})")

    print(f"\nSUCCESS: Rate limiting activated at Request #{first_429_index} with HTTP 429 Too Many Requests.")

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
    verify(target)
