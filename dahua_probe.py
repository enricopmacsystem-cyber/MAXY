#!/usr/bin/env python3
"""Probe Dahua videophone for firmware info via SSH and HTTP Digest."""

import socket
import sys
import json
import urllib.request
import urllib.error
import http.client

try:
    import paramiko
except ImportError:
    paramiko = None

HOST = "192.168.188.163"

CREDS = [
    ("admin", "admin123"),
    ("admin", "admin"),
    ("admin", ""),
    ("root", "vizxv"),
    ("root", "123456"),
    ("root", "root"),
    ("888888", "888888"),
]

CGI_ACTIONS = [
    "getSoftwareVersion",
    "getDeviceType",
    "getHardwareVersion",
    "getSerialNo",
    "getMachineName",
    "getSystemInfo",
    "getVendor",
    "getDeviceClass",
    "getBuildDate",
]

RPC2_METHODS = [
    ("magicBox.getSoftwareVersion", None),
    ("magicBox.getDeviceType", None),
    ("magicBox.getSerialNo", None),
    ("magicBox.getSystemInfo", None),
    ("configManager.getConfig", {"name": "General"}),
    ("system.multicall", None),
]


def make_opener(user, password):
    pm = urllib.request.HTTPPasswordMgrWithDefaultRealm()
    pm.add_password(None, f"http://{HOST}", user, password)
    digest = urllib.request.HTTPDigestAuthHandler(pm)
    basic = urllib.request.HTTPBasicAuthHandler(pm)
    return urllib.request.build_opener(digest, basic)


def http_get(path, user, password):
    opener = make_opener(user, password)
    url = f"http://{HOST}{path}"
    try:
        with opener.open(url, timeout=12) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", errors="replace")
    except Exception as e:
        return None, str(e)


def rpc2_call(method, params, user, password, req_id=1):
    body = json.dumps({"method": method, "params": params, "id": req_id})
    opener = make_opener(user, password)
    req = urllib.request.Request(
        f"http://{HOST}/RPC2",
        data=body.encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with opener.open(req, timeout=12) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", errors="replace")
    except Exception as e:
        return None, str(e)


def test_ssh(user, password):
    if not paramiko:
        print("paramiko unavailable")
        return False
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(
            HOST, port=22, username=user, password=password,
            timeout=10, allow_agent=False, look_for_keys=False,
            banner_timeout=10, auth_timeout=10,
        )
        print(f"\n[SSH SUCCESS] user={user} password={password!r}")
        cmds = [
            "uname -a",
            "cat /proc/version 2>/dev/null",
            "cat /etc/version 2>/dev/null",
            "cat /mnt/mtd/Config/version 2>/dev/null",
            "cat /mnt/custom/Config/version 2>/dev/null",
            "cat /var/version 2>/dev/null",
            "ls -la /mnt/mtd/ 2>/dev/null",
            "ls -la /mnt/ 2>/dev/null",
            "find /mnt -maxdepth 4 -type f \\( -name '*.bin' -o -name '*firmware*' -o -name 'version*' \\) 2>/dev/null",
            "cat /proc/cmdline 2>/dev/null",
            "mount 2>/dev/null",
            "df -h 2>/dev/null",
            "ps 2>/dev/null | head -20",
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
                    print(f"STDERR: {err[:500]}")
        client.close()
        return True
    except paramiko.AuthenticationException:
        return False
    except Exception as e:
        print(f"[SSH] {user}/{password!r}: {type(e).__name__}: {e}")
        return False


def main():
    print("=== Port scan ===")
    for port in [22, 80, 443, 37777, 554, 5000, 8080]:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(3)
        try:
            s.connect((HOST, port))
            print(f"Port {port}: OPEN")
        except Exception:
            pass
        finally:
            s.close()

    print("\n=== HTTP Digest CGI ===")
    working_creds = None
    for user, pwd in CREDS:
        ok = False
        for action in CGI_ACTIONS:
            status, body = http_get(f"/cgi-bin/magicBox.cgi?action={action}", user, pwd)
            if status == 200 and body.strip():
                print(f"[OK] {user}:{pwd!r} -> {action}")
                print(f"     {body.strip()}")
                ok = True
                working_creds = (user, pwd)
                break
            elif status not in (401, 403, None):
                print(f"[{status}] {user}:{pwd!r} {action}: {body[:120]}")
        if ok:
            break
        else:
            print(f"CGI failed for {user}:{pwd!r}")

    print("\n=== RPC2 API ===")
    for user, pwd in CREDS:
        for method, params in RPC2_METHODS:
            status, body = rpc2_call(method, params, user, pwd)
            if status == 200 and body.strip() and "error" not in body.lower()[:50]:
                print(f"[RPC2 OK] {user}:{pwd!r} {method}: {body[:400]}")
                if not working_creds:
                    working_creds = (user, pwd)
                break
        else:
            continue
        break

    if working_creds:
        user, pwd = working_creds
        print(f"\n=== Full info dump with {user}:{pwd!r} ===")
        for action in CGI_ACTIONS:
            status, body = http_get(f"/cgi-bin/magicBox.cgi?action={action}", user, pwd)
            if status == 200 and body.strip():
                print(f"{action}: {body.strip()}")

    print("\n=== SSH ===")
    if paramiko:
        for user, pwd in CREDS:
            print(f"Trying SSH {user}:{pwd!r}...", end=" ", flush=True)
            if test_ssh(user, pwd):
                return
            print("auth failed")
    else:
        print("Install paramiko for SSH")


if __name__ == "__main__":
    main()
