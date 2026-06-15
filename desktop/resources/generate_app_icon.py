#!/usr/bin/env python3
"""Genera app.ico multi-risoluzione ad alta qualità per Windows."""

from __future__ import annotations

from pathlib import Path

try:
    from PIL import Image, ImageFilter
except ImportError as exc:
    raise SystemExit("Installare Pillow: pip install pillow") from exc

RESOURCES = Path(__file__).resolve().parent
SOURCE = RESOURCES / "logo-m.png"
OUTPUT = RESOURCES / "app.ico"
HEADER_OUTPUT = RESOURCES / "logo-m-header.png"
MASTER_SIZE = 512
HEADER_SIZE = 128
# Dimensioni richieste da Windows 10/11
SIZES = (16, 20, 24, 32, 40, 48, 64, 72, 96, 128, 256)


def _prepare_master(source: Path) -> Image.Image:
    """Logo su canvas quadrato ad alta risoluzione (nitidezza al ridimensionamento)."""
    img = Image.open(source).convert("RGBA")
    width, height = img.size
    side = max(width, height)
    canvas = Image.new("RGBA", (side, side), (255, 255, 255, 255))
    offset = ((side - width) // 2, (side - height) // 2)
    canvas.paste(img, offset, img if img.mode == "RGBA" else None)

    # Upscale a 512px: da sorgenti piccole (es. 83px) mantiene il massimo dettaglio possibile
    master = canvas.resize((MASTER_SIZE, MASTER_SIZE), Image.Resampling.LANCZOS)
    return master


def _resize_icon(master: Image.Image, size: int) -> Image.Image:
    resized = master.resize((size, size), Image.Resampling.LANCZOS)
    if size <= 48:
        resized = resized.filter(
            ImageFilter.UnsharpMask(radius=0.5, percent=130, threshold=2)
        )
    return resized.convert("RGBA")


def main() -> None:
    if not SOURCE.is_file():
        raise SystemExit(f"Logo non trovato: {SOURCE}")

    master = _prepare_master(SOURCE)
    header = master.resize((HEADER_SIZE, HEADER_SIZE), Image.Resampling.LANCZOS)
    header.save(HEADER_OUTPUT, format="PNG", optimize=True)

    icons = [_resize_icon(master, size) for size in SIZES]
    icons[-1].save(
        OUTPUT,
        format="ICO",
        sizes=[(size, size) for size in SIZES],
        append_images=icons[:-1],
    )
    print(
        f"Icona generata da {SOURCE.name}: {OUTPUT} ({len(SIZES)} dimensioni, master {MASTER_SIZE}px)\n"
        f"Header UI: {HEADER_OUTPUT} ({HEADER_SIZE}px)"
    )


if __name__ == "__main__":
    main()
