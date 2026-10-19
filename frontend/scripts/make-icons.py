"""Generate Wellstride's placeholder app icons (a designer will replace them later).

The mark is an upward path that forms a "W". It uses only shapes drawn here (no fonts, no
third-party artwork).

Usage (from the frontend folder):  python scripts/make-icons.py
Needs Pillow (already in backend/requirements.txt).
"""
from pathlib import Path

from PIL import Image, ImageDraw

GREEN = (74, 107, 93)  # #4A6B5D
CREAM = (253, 251, 247)  # #FDFBF7
SCALE = 4  # draw 4x larger, then shrink, for smooth edges

ASSETS = Path(__file__).resolve().parent.parent / "assets"

# The W path in a 0..100 box (x right, y down).
W_POINTS = [(10, 22), (30, 78), (50, 36), (70, 78), (90, 22)]
STROKE = 11  # path thickness in the same units


def segment(draw, a, b, width, ink):
    """One stroke: a rectangle along a-b plus round caps, so every joint is smooth."""
    (ax, ay), (bx, by) = a, b
    length = ((bx - ax) ** 2 + (by - ay) ** 2) ** 0.5
    nx, ny = -(by - ay) / length * width / 2, (bx - ax) / length * width / 2
    draw.polygon([(ax + nx, ay + ny), (bx + nx, by + ny), (bx - nx, by - ny), (ax - nx, ay - ny)], fill=ink)
    for x, y in (a, b):
        draw.ellipse((x - width / 2, y - width / 2, x + width / 2, y + width / 2), fill=ink)


def draw_mark(size, ink, box, background=None):
    """Return a size x size RGBA image with the mark fitted into `box` (fraction of the canvas, centred)."""
    big = size * SCALE
    image = Image.new("RGBA", (big, big), background or (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    side = big * box
    left = (big - side) / 2
    unit = side / 100.0

    def point(x, y):
        return (left + x * unit, left + y * unit)

    width = STROKE * unit
    points = [point(x, y) for x, y in W_POINTS]
    for a, b in zip(points, points[1:]):
        segment(draw, a, b, width, ink)
    return image.resize((size, size), Image.BOX)  # exact 4x reduction: no ringing


def save(image, relative, mode):
    path = ASSETS / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    image.convert(mode).save(path, optimize=True)
    print(f"wrote {path.relative_to(ASSETS.parent)} ({image.size[0]}x{image.size[1]}, {mode})")


def main():
    # App icon: opaque (iOS rejects alpha), mark on the theme green.
    icon = draw_mark(1024, CREAM, 0.62, background=GREEN + (255,))
    save(icon, "images/icon.png", "RGB")

    # Android adaptive icon: transparent foreground, mark kept inside the central safe zone
    # (Android crops to about the middle 66%), over the green set as backgroundColor in app.json.
    save(draw_mark(1024, CREAM, 0.54), "images/adaptive-icon.png", "RGBA")

    # Splash: green mark on the cream splash background (set in app.json).
    save(draw_mark(1024, GREEN, 0.62, background=CREAM + (255,)), "images/splash-image.png", "RGB")

    # Web favicon and Play Store listing icon.
    save(icon.resize((48, 48), Image.LANCZOS), "images/favicon.png", "RGB")
    save(icon.resize((512, 512), Image.LANCZOS), "store/icon-512.png", "RGB")


if __name__ == "__main__":
    main()
