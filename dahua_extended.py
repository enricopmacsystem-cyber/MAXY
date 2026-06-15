#!/usr/bin/env python3
"""Extended Dahua firmware/SSH probe."""

import hashlib
import json
import random
import urllib.request

try:
    import paramiko
except ImportError:
    paramiko = None

HOST = "192.168.188.163"
USER = "admin"
PASSWORD = "qazwsx123!"


def rpc2(url, body, session=None):
    headers = {"Content-Type": "application/json"}
    if session:
        headers["Cookie"] = f"DWebClientSessionID={session}"
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode())


def login():
    r1 = rpc2(
        f"http://{HOST}/RPC2_Login",
        {"method": "global.login", "params": {"userName": USER, "password": "", "clientType": "Web3.0"}, "id": 1},
    )
    params = r1["params"]
    session = r1["session"]
    h1 = hashlib.md5(f"{USER}:{params['realm']}:{PASSWORD}".encode()).hexdigest().upper()
    ph = hashlib.md5(f"{USER}:{params['random']}:{h1}".encode()).hexdigest().upper()
    r2 = rpc2(
        f"http://{HOST}/RPC2_Login",
        {
            "method": "global.login",
            "params": {
                "userName": USER,
                "password": ph,
                "clientType": "Web3.0",
                "authorityType": "Default",
                "passwordType": "Default",
            },
            "id": 2,
            "session": session,
        },
    )
    if not r2.get("result"):
        raise RuntimeError(f"login failed: {r2}")
    return r2.get("session", session)


def call(session, method, params=None):
    return rpc2(
        f"http://{HOST}/RPC2",
        {"method": method, "params": params or {}, "id": random.randint(1, 9999), "session": session},
    )


def try_ssh():
    if not paramiko:
        print("paramiko not available")
        return
    print("\n=== SSH ===")
    for user in ("admin", "root"):
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            client.connect(
                HOST, 22, username=user, password=PASSWORD,
                timeout=12, allow_agent=False, look_for_keys=False,
                banner_timeout=12, auth_timeout=12,
            )
            print(f"SSH OK as {user}")
            cmds = [
                "uname -a",
                "cat /etc/version 2>/dev/null",
                "cat /mnt/mtd/Config/version 2>/dev/null",
                "ls -la /mnt/mtd/ 2>/dev/null",
                "find /mnt -maxdepth 5 -type f \\( -name '*.bin' -o -name '*firmware*' -o -name 'version*' \\) 2>/dev/null",
                "mount 2>/dev/null",
                "df -h 2>/dev/null",
            ]
            for cmd in cmds:
                _, stdout, stderr = client.exec_command(cmd, timeout=20)
                out = stdout.read().decode("utf-8", errors="replace").strip()
                err = stderr.read().decode("utf-8", errors="replace").strip()
                if out or err:
                    print(f"\n--- {cmd} ---")
                    if out:
                        print(out[:5000])
                    if err:
                        print("ERR:", err[:500])
            client.close()
            return
        except Exception as e:
            print(f"{user}: {type(e).__name__}: {e}")


def main():
    session = login()
    print("Session OK\n")

    methods = [
        ("upgrader.getStatus", {}),
        ("configManager.getConfig", {"name": "Upgrade"}),
        ("configManager.getConfig", {"name": "Maintenance"}),
        ("configManager.getConfig", {"name": "SSHD"}),
        ("magicBox.getBootParameter", {}),
        ("magicBox.getProcessInfo", {}),
        ("magicBox.getCaps", {}),
        ("IntervideoManager.getVersion", {}),
    ]
    for method, params in methods:
        try:
            resp = call(session, method, params)
            print(f"=== {method} ===")
            print(json.dumps(resp, indent=2, ensure_ascii=False)[:3000])
            print()
        except Exception as e:
            print(f"=== {method} ERROR: {e} ===\n")

    try_ssh()


if __name__ == "__main__":
    main()
