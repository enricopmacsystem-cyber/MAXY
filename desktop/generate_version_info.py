#!/usr/bin/env python3

"""Genera version_info.txt per metadati Windows nell'exe PyInstaller."""



from __future__ import annotations



import json

from pathlib import Path



DESKTOP_ROOT = Path(__file__).resolve().parent

VERSION_FILE = DESKTOP_ROOT / "version.json"

OUTPUT = DESKTOP_ROOT / "version_info.txt"





def _parse_version(version: str) -> tuple[int, int, int, int]:

    parts = [int(p) if p.isdigit() else 0 for p in version.strip().split(".")]

    while len(parts) < 4:

        parts.append(0)

    return tuple(parts[:4])





def main() -> None:

    meta = json.loads(VERSION_FILE.read_text(encoding="utf-8"))

    version = meta["version"]

    filevers = _parse_version(version)

    prodvers = filevers

    title = meta.get("product_title", "Maxy 2.0 - daisy")

    publisher = meta.get("publisher", "MacSystem s.r.l.")

    developer = meta.get("developer", "Andrea Santin")

    description = meta.get("description", "Maxy AI")

    copyright_line = meta.get("copyright", "")

    exe_name = f"{title}.exe"



    content = f"""# UTF-8

VSVersionInfo(

  ffi=FixedFileInfo(

    filevers={filevers},

    prodvers={prodvers},

    mask=0x3f,

    flags=0x0,

    OS=0x40004,

    fileType=0x1,

    subtype=0x0,

    date=(0, 0)

  ),

  kids=[

    StringFileInfo(

      [

      StringTable(

        '040904B0',

        [

        StringStruct('CompanyName', '{publisher}'),

        StringStruct('FileDescription', '{description} — {developer}'),

        StringStruct('FileVersion', '{version}'),

        StringStruct('InternalName', '{title}'),

        StringStruct('LegalCopyright', '{copyright_line}'),

        StringStruct('OriginalFilename', '{exe_name}'),

        StringStruct('ProductName', '{title}'),

        StringStruct('ProductVersion', '{version} beta')

        ])

      ]

    ),

    VarFileInfo([VarStruct('Translation', [1033, 1200])])

  ]

)

"""

    OUTPUT.write_text(content, encoding="utf-8")

    print(f"Generato: {OUTPUT}")





if __name__ == "__main__":

    main()

