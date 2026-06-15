#!/usr/bin/env python3
"""Try Dahua DHIP (port 37777) debug console access on VTO."""

import hashlib
import json
import socket
import struct

HOST = "192.168.188.163"
PORT = 37777
USER = "admin"
PASSWORD = "qazwsx123!"
MAGIC = 0x44484950  # DHIP


def dhip_send(sock, payload: bytes):
    sock.sendall(struct.pack("<II", MAGIC, len(payload)) + payload)


def dhip_recv(sock):
    hdr = sock.recv(8)
    if len(hdr) < 8:
        return None
    _, length = struct.unpack("<II", hdr)
    data = b""
    while len(data) < length:
        chunk = sock.recv(length - len(data))
        if not chunk:
            break
        data += chunk
    return data


def login(sock):
    dhip_send(
        sock,
        json.dumps(
            {"method": "global.login", "params": {"userName": USER, "password": "", "clientType": "DahuaAuth"}, "id": 1}
        ).encode(),
    )
    r1 = json.loads(dhip_recv(sock).decode())
    params = r1["params"]
    session = r1["session"]
    h1 = hashlib.md5(f"{USER}:{params['realm']}:{PASSWORD}".encode()).hexdigest().upper()
    ph = hashlib.md5(f"{USER}:{params['random']}:{h1}".encode()).hexdigest().upper()
    dhip_send(
        sock,
        json.dumps(
            {
                "method": "global.login",
                "params": {
                    "userName": USER,
                    "password": ph,
                    "clientType": "DahuaAuth",
                    "authorityType": "Default",
                    "passwordType": "Default",
                },
                "id": 2,
                "session": session,
            }
        ).encode(),
    )
    r2 = json.loads(dhip_recv(sock).decode())
    if not r2.get("result"):
        raise RuntimeError(f"login failed: {r2}")
    return r2.get("session", session)


def call(sock, session, method, params=None, req_id=3):
    dhip_send(
        sock,
        json.dumps({"method": method, "params": params or {}, "id": req_id, "session": session}).encode(),
    )
    return json.loads(dhip_recv(sock).decode())


def main():
    sock = socket.socket()
    sock.settimeout(10)
    sock.connect((HOST, PORT))
    print(f"Connected to {HOST}:{PORT}")

    session = login(sock)
    print(f"Login OK, session={session}\n")

    probes = [
        ("console.factory.instance", {}),
        ("console.factory.attach", {}),
        ("magicBox.getSoftwareVersion", {}),
        ("configManager.getConfig", {"name": "SSHD"}),
    ]
    for method, params in probes:
        try:
            resp = call(sock, session, method, params)
            print(f"=== {method} ===")
            print(json.dumps(resp, indent=2, ensure_ascii=False)[:2000])
            print()
        except Exception as e:
            print(f"=== {method} ERROR: {e}\n")

    sock.close()


if __name__ == "__main__":
    main()
