#!/usr/bin/env python3
"""Genera icone mipmap Android ad alta qualità dal logo Mac System."""

from __future__ import annotations

from pathlib import Path

try:
    from PIL import Image
except ImportError as exc:
    raise SystemExit("Installare Pillow: pip install pillow") from exc

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT.parent / "desktop" / "resources" / "logo-m.png"
RES = ROOT / "app" / "src" / "main" / "res"
DRAWABLE = RES / "drawable"
MIPMAP_SIZES = {
    "mipmap-mdpi": 48,
    "mipmap-hdpi": 72,
    "mipmap-xhdpi": 96,
    "mipmap-xxhdpi": 144,
    "mipmap-xxxhdpi": 192,
}
FOREGROUND_SIZE = 432


def _square_canvas(image: Image.Image, background: tuple[int, int, int, int]) -> Image.Image:
    width, height = image.size
    side = max(width, height)
    canvas = Image.new("RGBA", (side, side), background)
    offset = ((side - width) // 2, (side - height) // 2)
    canvas.paste(image, offset, image if image.mode == "RGBA" else None)
    return canvas


def main() -> None:
    if not SOURCE.is_file():
        raise SystemExit(f"Logo non trovato: {SOURCE}")

    DRAWABLE.mkdir(parents=True, exist_ok=True)
    logo = Image.open(SOURCE).convert("RGBA")
    master = _square_canvas(logo, (255, 255, 255, 255)).resize((512, 512), Image.Resampling.LANCZOS)
    master.save(DRAWABLE / "logo_m.png", format="PNG", optimize=True)

    foreground = master.resize((FOREGROUND_SIZE, FOREGROUND_SIZE), Image.Resampling.LANCZOS)
    foreground.save(DRAWABLE / "ic_launcher_foreground.png", format="PNG", optimize=True)

    for folder, size in MIPMAP_SIZES.items():
        target = RES / folder
        target.mkdir(parents=True, exist_ok=True)
        icon = master.resize((size, size), Image.Resampling.LANCZOS)
        icon.save(target / "ic_launcher.png", format="PNG", optimize=True)
        icon.save(target / "ic_launcher_round.png", format="PNG", optimize=True)

    print(f"Icone generate da {SOURCE.name}")


if __name__ == "__main__":
    main()
