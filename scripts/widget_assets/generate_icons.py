"""
Generate UI icon and texture assets for the Widget DSL theme system.

All icons are white silhouettes on transparent background (64x64).
The theme system tints them to the right color at runtime.
"""

import math
import os
import random
from PIL import Image, ImageDraw, ImageFilter

ICON_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "Content", "UI_Common", "Icons")
TEX_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "Content", "UI_Common", "Textures")
SIZE = 64
WHITE = (255, 255, 255, 255)
CLEAR = (0, 0, 0, 0)


def _img(size=SIZE):
    return Image.new("RGBA", (size, size), CLEAR)


def _save_icon(img, name):
    path = os.path.join(ICON_DIR, name)
    img.save(path)
    return path


def _save_tex(img, name):
    path = os.path.join(TEX_DIR, name)
    img.save(path)
    return path


# ── Icon generators ──────────────────────────────────────

def gen_health():
    img = _img(); d = ImageDraw.Draw(img)
    # Plus/cross shape
    d.rectangle([24, 12, 40, 52], fill=WHITE)
    d.rectangle([12, 24, 52, 40], fill=WHITE)
    return _save_icon(img, "icon_health.png")


def gen_shield():
    img = _img(); d = ImageDraw.Draw(img)
    pts = [(32, 6), (52, 16), (50, 40), (32, 56), (14, 40), (12, 16)]
    d.polygon(pts, outline=WHITE, width=3)
    return _save_icon(img, "icon_shield.png")


def gen_ammo():
    img = _img(); d = ImageDraw.Draw(img)
    # Bullet shape: rectangle body + rounded top
    d.rectangle([24, 20, 40, 54], fill=WHITE)
    d.ellipse([24, 10, 40, 30], fill=WHITE)
    return _save_icon(img, "icon_ammo.png")


def gen_coin():
    img = _img(); d = ImageDraw.Draw(img)
    d.ellipse([8, 8, 56, 56], outline=WHITE, width=3)
    d.ellipse([20, 20, 44, 44], outline=WHITE, width=2)
    return _save_icon(img, "icon_coin.png")


def gen_key():
    img = _img(); d = ImageDraw.Draw(img)
    # Key head (circle)
    d.ellipse([8, 8, 32, 32], outline=WHITE, width=3)
    # Key shaft
    d.rectangle([28, 18, 56, 22], fill=WHITE)
    # Key teeth
    d.rectangle([46, 22, 50, 30], fill=WHITE)
    d.rectangle([52, 22, 56, 28], fill=WHITE)
    return _save_icon(img, "icon_key.png")


def gen_skull():
    img = _img(); d = ImageDraw.Draw(img)
    # Skull dome
    d.ellipse([12, 6, 52, 42], outline=WHITE, width=3)
    # Jaw
    d.rectangle([18, 36, 46, 48], outline=WHITE, width=2)
    # Eyes
    d.ellipse([20, 18, 30, 28], fill=WHITE)
    d.ellipse([34, 18, 44, 28], fill=WHITE)
    return _save_icon(img, "icon_skull.png")


def gen_star():
    img = _img(); d = ImageDraw.Draw(img)
    cx, cy, r = 32, 32, 24
    pts = []
    for i in range(10):
        a = math.radians(i * 36 - 90)
        rad = r if i % 2 == 0 else r * 0.4
        pts.append((cx + rad * math.cos(a), cy + rad * math.sin(a)))
    d.polygon(pts, fill=WHITE)
    return _save_icon(img, "icon_star.png")


def gen_arrow_up():
    img = _img(); d = ImageDraw.Draw(img)
    d.polygon([(32, 8), (52, 36), (40, 36)], fill=WHITE)
    d.polygon([(32, 8), (12, 36), (24, 36)], fill=WHITE)
    d.rectangle([24, 36, 40, 56], fill=WHITE)
    return _save_icon(img, "icon_arrow_up.png")


def gen_arrow_right():
    img = _img(); d = ImageDraw.Draw(img)
    d.polygon([(56, 32), (28, 12), (28, 24)], fill=WHITE)
    d.polygon([(56, 32), (28, 52), (28, 40)], fill=WHITE)
    d.rectangle([8, 24, 28, 40], fill=WHITE)
    return _save_icon(img, "icon_arrow_right.png")


def gen_checkmark():
    img = _img(); d = ImageDraw.Draw(img)
    d.line([(12, 34), (26, 50), (52, 14)], fill=WHITE, width=5)
    return _save_icon(img, "icon_checkmark.png")


def gen_crosshair_dot():
    img = _img(); d = ImageDraw.Draw(img)
    d.ellipse([28, 28, 36, 36], fill=WHITE)
    return _save_icon(img, "icon_crosshair_dot.png")


def gen_crosshair_cross():
    img = _img(); d = ImageDraw.Draw(img)
    d.rectangle([30, 8, 34, 26], fill=WHITE)
    d.rectangle([30, 38, 34, 56], fill=WHITE)
    d.rectangle([8, 30, 26, 34], fill=WHITE)
    d.rectangle([38, 30, 56, 34], fill=WHITE)
    return _save_icon(img, "icon_crosshair_cross.png")


def gen_crosshair_circle():
    img = _img(); d = ImageDraw.Draw(img)
    d.ellipse([12, 12, 52, 52], outline=WHITE, width=2)
    d.ellipse([29, 29, 35, 35], fill=WHITE)
    return _save_icon(img, "icon_crosshair_circle.png")


def gen_timer():
    img = _img(); d = ImageDraw.Draw(img)
    d.ellipse([8, 10, 56, 58], outline=WHITE, width=3)
    # Clock hands
    d.line([(32, 34), (32, 18)], fill=WHITE, width=3)
    d.line([(32, 34), (44, 34)], fill=WHITE, width=2)
    # Top nub
    d.rectangle([28, 4, 36, 12], fill=WHITE)
    return _save_icon(img, "icon_timer.png")


def gen_compass():
    img = _img(); d = ImageDraw.Draw(img)
    d.ellipse([6, 6, 58, 58], outline=WHITE, width=2)
    # N arrow
    d.polygon([(32, 10), (28, 32), (36, 32)], fill=WHITE)
    # S arrow (outline)
    d.polygon([(32, 54), (28, 32), (36, 32)], outline=WHITE, width=1)
    return _save_icon(img, "icon_compass.png")


def gen_gear():
    img = _img(); d = ImageDraw.Draw(img)
    cx, cy = 32, 32
    # Outer teeth
    for i in range(8):
        a = math.radians(i * 45)
        x1 = cx + 22 * math.cos(a) - 4
        y1 = cy + 22 * math.sin(a) - 4
        d.rectangle([x1, y1, x1 + 8, y1 + 8], fill=WHITE)
    # Outer ring
    d.ellipse([14, 14, 50, 50], outline=WHITE, width=4)
    # Inner hole
    d.ellipse([24, 24, 40, 40], fill=CLEAR)
    d.ellipse([24, 24, 40, 40], outline=WHITE, width=2)
    return _save_icon(img, "icon_gear.png")


def gen_volume():
    img = _img(); d = ImageDraw.Draw(img)
    # Speaker body
    d.polygon([(10, 24), (22, 24), (34, 12), (34, 52), (22, 40), (10, 40)], fill=WHITE)
    # Sound waves
    d.arc([34, 18, 48, 46], -50, 50, fill=WHITE, width=2)
    d.arc([38, 10, 56, 54], -50, 50, fill=WHITE, width=2)
    return _save_icon(img, "icon_volume.png")


def gen_eye():
    img = _img(); d = ImageDraw.Draw(img)
    # Eye outline
    d.ellipse([6, 18, 58, 46], outline=WHITE, width=3)
    # Pupil
    d.ellipse([24, 24, 40, 40], fill=WHITE)
    return _save_icon(img, "icon_eye.png")


def gen_lock():
    img = _img(); d = ImageDraw.Draw(img)
    # Lock body
    d.rectangle([14, 28, 50, 54], outline=WHITE, width=3)
    # Shackle
    d.arc([18, 8, 46, 36], 180, 0, fill=WHITE, width=3)
    # Keyhole
    d.ellipse([28, 36, 36, 44], fill=WHITE)
    d.rectangle([30, 42, 34, 50], fill=WHITE)
    return _save_icon(img, "icon_lock.png")


def gen_trophy():
    img = _img(); d = ImageDraw.Draw(img)
    # Cup body
    d.rectangle([18, 8, 46, 36], outline=WHITE, width=3)
    # Handles
    d.arc([8, 12, 22, 30], 90, 270, fill=WHITE, width=2)
    d.arc([42, 12, 56, 30], -90, 90, fill=WHITE, width=2)
    # Stem
    d.rectangle([28, 36, 36, 46], fill=WHITE)
    # Base
    d.rectangle([16, 46, 48, 52], fill=WHITE)
    return _save_icon(img, "icon_trophy.png")


# ── Texture generators ───────────────────────────────────

def gen_panel_solid():
    img = Image.new("RGBA", (4, 4), WHITE)
    return _save_tex(img, "panel_solid.png")


def gen_panel_rounded(radius, name):
    img = _img()
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, 63, 63], radius=radius, fill=WHITE)
    return _save_tex(img, name)


def gen_progress_fill():
    img = Image.new("RGBA", (4, 64), WHITE)
    return _save_tex(img, "progress_fill.png")


def gen_gradient_horizontal():
    img = Image.new("RGBA", (256, 4), CLEAR)
    for x in range(256):
        a = 255 - x
        for y in range(4):
            img.putpixel((x, y), (255, 255, 255, a))
    return _save_tex(img, "gradient_horizontal.png")


def gen_gradient_radial():
    size = 128
    img = Image.new("RGBA", (size, size), CLEAR)
    cx, cy = size // 2, size // 2
    max_dist = math.sqrt(cx * cx + cy * cy)
    for y in range(size):
        for x in range(size):
            dist = math.sqrt((x - cx) ** 2 + (y - cy) ** 2)
            a = max(0, int(255 * (1.0 - dist / max_dist)))
            img.putpixel((x, y), (255, 255, 255, a))
    return _save_tex(img, "gradient_radial.png")


def gen_vignette():
    size = 512
    img = Image.new("RGBA", (size, size), CLEAR)
    cx, cy = size // 2, size // 2
    max_dist = math.sqrt(cx * cx + cy * cy)
    for y in range(size):
        for x in range(size):
            dist = math.sqrt((x - cx) ** 2 + (y - cy) ** 2)
            t = max(0.0, min(1.0, (dist / max_dist - 0.4) / 0.6))
            a = int(200 * t)
            img.putpixel((x, y), (0, 0, 0, a))
    return _save_tex(img, "vignette.png")


def gen_noise():
    size = 256
    img = Image.new("RGBA", (size, size), CLEAR)
    random.seed(42)
    for y in range(size):
        for x in range(size):
            v = random.randint(0, 255)
            img.putpixel((x, y), (v, v, v, 13))  # ~5% opacity
    return _save_tex(img, "noise_overlay.png")


# ── Main ─────────────────────────────────────────────────

if __name__ == "__main__":
    os.makedirs(ICON_DIR, exist_ok=True)
    os.makedirs(TEX_DIR, exist_ok=True)

    print("Generating UI icons (64x64, white on transparent)...")
    icons = [
        gen_health, gen_shield, gen_ammo, gen_coin, gen_key, gen_skull,
        gen_star, gen_arrow_up, gen_arrow_right, gen_checkmark,
        gen_crosshair_dot, gen_crosshair_cross, gen_crosshair_circle,
        gen_timer, gen_compass, gen_gear, gen_volume, gen_eye, gen_lock, gen_trophy,
    ]
    for fn in icons:
        path = fn()
        size = os.path.getsize(path)
        print(f"  {os.path.basename(path):30s} {size:5d} bytes")

    print(f"\nGenerating UI textures...")
    textures = [
        lambda: gen_panel_solid(),
        lambda: gen_panel_rounded(8, "panel_rounded_8.png"),
        lambda: gen_panel_rounded(16, "panel_rounded_16.png"),
        lambda: gen_progress_fill(),
        lambda: gen_gradient_horizontal(),
        lambda: gen_gradient_radial(),
        lambda: gen_vignette(),
        lambda: gen_noise(),
    ]
    for fn in textures:
        path = fn()
        size = os.path.getsize(path)
        print(f"  {os.path.basename(path):30s} {size:5d} bytes")

    total = len(icons) + len(textures)
    total_size = sum(
        os.path.getsize(os.path.join(ICON_DIR, f)) for f in os.listdir(ICON_DIR)
    ) + sum(
        os.path.getsize(os.path.join(TEX_DIR, f)) for f in os.listdir(TEX_DIR)
    )
    print(f"\nTotal: {total} files, {total_size / 1024:.1f} KB")
