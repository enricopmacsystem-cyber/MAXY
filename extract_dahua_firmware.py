#!/usr/bin/env python3
"""Extract Dahua DH firmware (.bin = DH-prefixed ZIP)."""

import shutil
import struct
import zipfile
from pathlib import Path

SRC = Path(
    r"c:\Users\enrico.patres\OneDrive - MAC SYSTEM SRL\Desktop"
    r"\DH_VTOVilla_Vale_MultiLang_PN_128M_SIP_EMEA_V4.810.0000000.3.R.260528.bin"
)
OUT = Path(r"c:\MAXY\firmware_extracted\V4.810.0000000.3.R.260528")
WORK = Path(r"c:\MAXY\firmware_work\V4.810.0000000.3.R.260528.bin")

UIMAGE_MAGIC = 0x27051956


def parse_uimage_header(data: bytes):
    if len(data) < 64:
        return None
    fields = struct.unpack(">IIIIIIIII", data[:36])
    magic, hcrc, ts, sz, load, ep, dcrc, pt, name = fields[:9]
    if magic != UIMAGE_MAGIC:
        return None
    name_bytes = data[32:64].split(b"\x00", 1)[0]
    return {
        "magic": hex(magic),
        "size": sz,
        "load": hex(load),
        "entry": hex(ep),
        "name": name_bytes.decode("ascii", errors="replace"),
        "header_size": 64,
    }


def main():
    if not SRC.exists():
        raise SystemExit(f"Source not found: {SRC}")

    WORK.parent.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)

    shutil.copy2(SRC, WORK)
    raw = bytearray(WORK.read_bytes())
    print(f"Source: {SRC.name}")
    print(f"Size:   {len(raw):,} bytes ({len(raw)/1024/1024:.2f} MB)")
    print(f"Header: {raw[:8]!r}")

    if raw[:2] != b"DH":
        raise SystemExit("Unexpected header (expected DH)")

    raw[0:2] = b"PK"
    patched = WORK.with_suffix(".patched.zip")
    patched.write_bytes(raw)
    print(f"Patched ZIP: {patched}")

    with zipfile.ZipFile(patched, "r") as zf:
        bad = zf.testzip()
        if bad:
            print(f"WARNING: corrupt zip member: {bad}")
        print(f"\nArchive members ({len(zf.namelist())}):")
        for info in zf.infolist():
            print(f"  {info.file_size:>12,}  {info.filename}")
        zf.extractall(OUT)

    print(f"\nExtracted to: {OUT}\n")

    # Analyze extracted files
    for path in sorted(OUT.rglob("*")):
        if not path.is_file():
            continue
        data = path.read_bytes()
        rel = path.relative_to(OUT)
        line = f"--- {rel} ({len(data):,} bytes) ---"

        if path.suffix == ".img" or "img" in path.name:
            hdr = parse_uimage_header(data)
            if hdr:
                payload = data[hdr["header_size"] : hdr["header_size"] + min(64, hdr["size"])]
                tail = data[-128:]
                enc = b"SecrityImgMagic" in data or b"SecurityImgMagic" in data
                squash = payload[:4] in (b"hsqs", b"sqsh")
                print(line)
                print(f"  uImage name={hdr['name']!r} size={hdr['size']:,}")
                print(f"  payload magic: {payload[:16].hex()} ascii={payload[:16]!r}")
                print(f"  encrypted/sign block: {enc}")
                print(f"  looks like squashfs: {squash}")
                if enc:
                    print(f"  tail ascii: {tail.decode('ascii', errors='replace')[-80:]}")
            else:
                # text files like hwid, Install, partition
                if all(32 <= b < 127 or b in (9, 10, 13) for b in data[: min(200, len(data))]):
                    preview = data[:500].decode("utf-8", errors="replace")
                    print(line)
                    print(preview[:500])
                else:
                    print(line)
                    print(f"  head: {data[:32].hex()}")
        elif path.name in ("hwid", "Install", "partition-x.cramfs.img") or path.suffix in (".txt", ""):
            try:
                text = data.decode("utf-8", errors="replace")
                print(line)
                print(text[:800])
            except Exception:
                print(line)

    print("\nDone.")


if __name__ == "__main__":
    main()
