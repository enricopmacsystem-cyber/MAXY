#!/usr/bin/env python3
"""Probe Dahua VTO for firmware backup/export capabilities."""

import hashlib
import json
import random
import urllib.request

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
    p = r1["params"]
    s = r1["session"]
    h1 = hashlib.md5(f"{USER}:{p['realm']}:{PASSWORD}".encode()).hexdigest().upper()
    ph = hashlib.md5(f"{USER}:{p['random']}:{h1}".encode()).hexdigest().upper()
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
            "session": s,
        },
    )
    if not r2.get("result"):
        raise RuntimeError(r2)
    return r2.get("session", s)


def call(session, method, params=None):
    return rpc2(
        f"http://{HOST}/RPC2",
        {"method": method, "params": params or {}, "id": random.randint(1, 9999), "session": session},
    )


def main():
    session = login()
    print("Logged in\n")

    methods = [
        ("upgrader.getStatus", {}),
        ("upgrader.getCaps", {}),
        ("upgrader.getBackup", {}),
        ("upgrader.factory.getCollectInfo", {}),
        ("configManager.getConfig", {"name": "CloudUpgrade"}),
        ("configManager.getConfig", {"name": "AutoMaintain"}),
        ("configManager.getConfig", {"name": "SSHD"}),
        ("configManager.getConfig", {"name": "General"}),
        ("magicBox.getCaps", {}),
        ("magicBox.getProductDefinition", {"name": "Encryption"}),
        ("magicBox.getProductDefinition", {"name": "SupportExportLog"}),
        ("magicBox.getProductDefinition", {"name": "SupportImportExportConfig"}),
        ("magicBox.getProductDefinition", {"name": "SupportCloudUpgrade"}),
        ("log.export", {}),
        ("system.exportConfig", {}),
        ("configManager.exportConfig", {}),
        ("configManager.exportRemoteDeviceList", {}),
    ]

    for method, params in methods:
        try:
            resp = call(session, method, params)
            ok = resp.get("result", False)
            err = resp.get("error", {})
            print(f"=== {method} === [{'OK' if ok else 'FAIL'}]")
            if err:
                print(f"  error: {err.get('code')} {err.get('message')}")
            if ok and resp.get("params"):
                print(json.dumps(resp["params"], indent=2, ensure_ascii=False)[:2500])
            print()
        except Exception as e:
            print(f"=== {method} === EXCEPTION: {e}\n")

    # HTTP paths sometimes used for config backup
    from urllib.request import HTTPDigestAuthHandler, HTTPPasswordMgrWithDefaultRealm, build_opener

    pm = HTTPPasswordMgrWithDefaultRealm()
    pm.add_password(None, f"http://{HOST}", USER, PASSWORD)
    opener = build_opener(HTTPDigestAuthHandler(pm))
    paths = [
        "/cgi-bin/configManager.cgi?action=backup",
        "/cgi-bin/configManager.cgi?action=export",
        "/cgi-bin/RPC_Loadfile/magicBox.cgi?action=getDeviceType",
        "/RPC2_Loadfile/upgrader/firmware.bin",
    ]
    print("=== HTTP backup paths ===")
    for path in paths:
        try:
            with opener.open(f"http://{HOST}{path}", timeout=10) as r:
                data = r.read(200)
                print(f"{path}: {r.status} len={len(data)} head={data[:80]!r}")
        except Exception as e:
            print(f"{path}: {type(e).__name__}: {e}")


if __name__ == "__main__":
    main()
