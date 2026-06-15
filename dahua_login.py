#!/usr/bin/env python3
"""Dahua RPC2 login + firmware info extraction."""

import hashlib
import json
import random
import socket
import urllib.request
import urllib.error

HOST = "192.168.188.163"

PASSWORDS = ["qazwsx123!"]


def rpc2(body: dict, session=None):
    data = json.dumps(body).encode()
    headers = {"Content-Type": "application/json"}
    if session:
        headers["Cookie"] = f"DWebClientSessionID={session}"
    req = urllib.request.Request(
        f"http://{HOST}/RPC2_Login" if body.get("method") == "global.login" else f"http://{HOST}/RPC2",
        data=data,
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        try:
            return e.code, json.loads(raw)
        except json.JSONDecodeError:
            return e.code, {"raw": raw}
    except Exception as e:
        return None, {"error": str(e)}


def dahua_login(user: str, password: str):
    # Step 1: get challenge
    status, r1 = rpc2({
        "method": "global.login",
        "params": {
            "userName": user,
            "password": "",
            "clientType": "Web3.0",
        },
        "id": 1,
    })
    if status != 200 or "params" not in r1:
        return None, f"challenge failed: {r1}"

    params = r1["params"]
    realm = params.get("realm", "")
    random_val = params.get("random", "")
    session = params.get("session", r1.get("session", ""))
    encryption = params.get("encryption", "Default")

    if encryption == "Default":
        # MD5(user:realm:pass) then MD5(user:random:hash1)
        h1 = hashlib.md5(f"{user}:{realm}:{password}".encode()).hexdigest().upper()
        pass_hash = hashlib.md5(f"{user}:{random_val}:{h1}".encode()).hexdigest().upper()
    else:
        pass_hash = hashlib.md5(password.encode()).hexdigest().upper()

    status, r2 = rpc2({
        "method": "global.login",
        "params": {
            "userName": user,
            "password": pass_hash,
            "clientType": "Web3.0",
            "authorityType": "Default",
            "passwordType": "Default",
        },
        "id": 2,
        "session": session,
    })
    if status == 200 and r2.get("result") is True:
        return r2.get("session", session), r2
    return None, r2


def get_info(session, method, params=None):
    status, resp = rpc2({"method": method, "params": params or {}, "id": random.randint(100, 9999), "session": session})
    return status, resp


def main():
    print(f"Target: {HOST}\n")

    for pwd in PASSWORDS:
        print(f"Login admin / {pwd!r}...", end=" ")
        session, result = dahua_login("admin", pwd)
        if session:
            print("OK")
            print(f"Session: {session}\n")

            methods = [
                ("magicBox.getSoftwareVersion", None),
                ("magicBox.getDeviceType", None),
                ("magicBox.getHardwareVersion", None),
                ("magicBox.getSerialNo", None),
                ("magicBox.getMachineName", None),
                ("magicBox.getSystemInfo", None),
                ("magicBox.getProductDefinition", {"name": "MaxExtraStream"}),
                ("configManager.getConfig", {"name": "General"}),
                ("configManager.getConfig", {"name": "Network"}),
                ("system.info", None),
            ]
            for method, params in methods:
                status, resp = get_info(session, method, params)
                if status == 200:
                    print(f"=== {method} ===")
                    print(json.dumps(resp, indent=2, ensure_ascii=False)[:2000])
                    print()
            return
        else:
            err = result.get("error", result) if isinstance(result, dict) else result
            print(f"fail: {err}")

    print("\nNo working password found among defaults.")


if __name__ == "__main__":
    main()
