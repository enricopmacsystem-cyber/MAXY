"""Genera splash-screen Maxy su sfondo bianco (eseguire dopo aver aggiunto splash-maxy-source.png)."""

from __future__ import annotations

from pathlib import Path

from PIL import Image

RESOURCES = Path(__file__).resolve().parent
SOURCE = RESOURCES / "splash-maxy-source.png"
OUTPUT = RESOURCES / "splash-maxy.png"

# Larghezza finale splash (alta risoluzione per display nitidi)
TARGET_WIDTH = 720
PADDING = 40
BG = (255, 255, 255)


def _remove_near_black(img: Image.Image, threshold: int = 28) -> Image.Image:
    rgba = img.convert("RGBA")
    pixels = rgba.load()
    w, h = rgba.size
    for y in range(h):
        for x in range(w):
            r, g, b, a = pixels[x, y]
            if r <= threshold and g <= threshold and b <= threshold:
                pixels[x, y] = (255, 255, 255, 0)
    return rgba


def main() -> None:
    if not SOURCE.is_file():
        raise SystemExit(f"File sorgente mancante: {SOURCE}")

    src = Image.open(SOURCE)
    src = _remove_near_black(src)

    ratio = TARGET_WIDTH / src.width
    target_h = int(src.height * ratio)
    resized = src.resize((TARGET_WIDTH, target_h), Image.Resampling.LANCZOS)

    canvas_w = TARGET_WIDTH + PADDING * 2
    canvas_h = target_h + PADDING * 2
    canvas = Image.new("RGB", (canvas_w, canvas_h), BG)
    canvas.paste(resized, (PADDING, PADDING), resized)
    canvas.save(OUTPUT, format="PNG", optimize=True)
    print(f"Creato {OUTPUT} ({canvas_w}x{canvas_h})")


if __name__ == "__main__":
    main()
