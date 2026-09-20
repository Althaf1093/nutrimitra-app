"""Generate a food-like JPEG with real visual features (edges, textures, shadows)
for vision API testing, per /app/image_testing.md rules."""
import base64
import io
import math
import random
import tempfile
from pathlib import Path

DEFAULT_PATH = str(Path(tempfile.gettempdir()) / "test_food.jpg")


def make_food_image(path: str = DEFAULT_PATH) -> str:
    from PIL import Image, ImageDraw, ImageFilter

    random.seed(42)
    size = 640
    img = Image.new("RGB", (size, size), (245, 240, 230))
    draw = ImageDraw.Draw(img)

    # Table gradient background
    for y in range(size):
        shade = 235 - int(30 * y / size)
        draw.line([(0, y), (size, y)], fill=(shade, shade - 5, shade - 15))

    # Plate shadow
    shadow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    sd.ellipse([100, 130, 560, 570], fill=(60, 50, 40, 120))
    shadow = shadow.filter(ImageFilter.GaussianBlur(18))
    img.paste(Image.alpha_composite(img.convert("RGBA"), shadow).convert("RGB"), (0, 0))

    draw = ImageDraw.Draw(img)
    # White plate
    draw.ellipse([80, 80, 560, 560], fill=(252, 252, 250), outline=(200, 200, 195), width=3)
    draw.ellipse([120, 120, 520, 520], outline=(220, 218, 210), width=2)

    # Rice mound (off-white blobs with grain noise)
    for _ in range(900):
        x = int(random.gauss(320, 55))
        y = int(random.gauss(300, 45))
        r = random.randint(2, 5)
        c = random.choice([(250, 246, 232), (240, 234, 214), (255, 252, 240), (228, 222, 200)])
        draw.ellipse([x - r, y - r // 2, x + r, y + r // 2], fill=c)

    # Curry pool (orange-brown with oily highlights)
    for _ in range(700):
        x = int(random.gauss(400, 50))
        y = int(random.gauss(420, 40))
        r = random.randint(3, 8)
        c = random.choice([(196, 110, 40), (176, 90, 30), (216, 130, 55), (150, 72, 22)])
        draw.ellipse([x - r, y - r, x + r, y + r], fill=c)
    for _ in range(60):  # oil sheen highlights
        x = int(random.gauss(400, 45))
        y = int(random.gauss(415, 35))
        r = random.randint(1, 3)
        draw.ellipse([x - r, y - r, x + r, y + r], fill=(235, 180, 110))

    # Coriander garnish (green specks)
    for _ in range(120):
        x = random.randint(240, 480)
        y = random.randint(180, 480)
        if math.hypot(x - 320, y - 320) < 180:
            r = random.randint(1, 3)
            draw.ellipse([x - r, y - r, x + r, y + r], fill=random.choice([(60, 120, 50), (45, 100, 40), (80, 140, 60)]))

    # Onion slices (pale arcs)
    for i in range(6):
        x = 150 + i * 18
        draw.arc([x, 430 + (i % 2) * 10, x + 46, 500 + (i % 2) * 10], start=200, end=340, fill=(225, 200, 210), width=5)

    img = img.filter(ImageFilter.UnsharpMask(radius=2, percent=80))
    img.save(path, "JPEG", quality=88)
    with open(path, "rb") as fh:
        return base64.b64encode(fh.read()).decode()


if __name__ == "__main__":
    b64 = make_food_image()
    print(f"Generated {DEFAULT_PATH}, base64 length={len(b64)}")
