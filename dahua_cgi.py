#!/usr/bin/env python3
"""Dahua CGI digest auth firmware query."""

import urllib.request
from urllib.request import HTTPDigestAuthHandler, HTTPPasswordMgrWithDefaultRealm, build_opener

HOST = "192.168.188.163"
USER = "admin"
PASSWORD = "qazwsx123!"

ACTIONS = [
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

pm = HTTPPasswordMgrWithDefaultRealm()
pm.add_password(None, f"http://{HOST}", USER, PASSWORD)
opener = build_opener(HTTPDigestAuthHandler(pm))

for action in ACTIONS:
    url = f"http://{HOST}/cgi-bin/magicBox.cgi?action={action}"
    try:
        with opener.open(url, timeout=12) as resp:
            body = resp.read().decode("utf-8", errors="replace").strip()
            print(f"{action}: {body}")
    except Exception as e:
        print(f"{action}: ERROR {e}")
