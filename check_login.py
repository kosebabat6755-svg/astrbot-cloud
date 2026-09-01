#!/usr/bin/env python3
"""Verify AstrBot dashboard login via the public tunnel URL.

Usage: check_login.py <tunnel_url> <username> <password>
Exit 0 = login works, 1 = rejected, 2 = unreachable.
"""
import hashlib
import json
import sys
import urllib.error
import urllib.request

url = sys.argv[1].rstrip("/")
user, pwd = sys.argv[2], sys.argv[3]

# Server compares md5(candidate) against the stored md5 hex (v4.28 auth),
# but /api/v1/auth/login takes plaintext and hashes it server-side. We send
# plaintext; hashing here only for reference/debugging.
print(f"md5 reference: {hashlib.md5(pwd.encode()).hexdigest()[:8]}...")

for endpoint in ("/api/v1/auth/login", "/api/auth/login"):
    try:
        req = urllib.request.Request(
            f"{url}{endpoint}",
            data=json.dumps({"username": user, "password": pwd}).encode(),
            method="POST",
            headers={"Content-Type": "application/json", "User-Agent": "live-fire-check"},
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode()
            print(f"{endpoint} -> HTTP {resp.status}")
            print(body[:300])
            ok = resp.status == 200
            sys.exit(0 if ok else 1)
    except urllib.error.HTTPError as e:
        print(f"{endpoint} -> HTTP {e.code} (rejected)")
    except Exception as e:
        print(f"{endpoint} -> unreachable: {e}")
        sys.exit(2)
sys.exit(1)
