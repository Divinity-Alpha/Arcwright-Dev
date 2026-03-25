"""Generate Arcwright branded PNG logos for the UE editor panel."""
import sys, os, math
from PIL import Image, ImageDraw, ImageFont

# Brand colors (RGB tuples)
DEEP_NAVY = (6, 10, 20)
HEADER_BG = (7, 11, 22)
BRAND_BLUE = (74, 158, 255)
LIGHT_BLUE = (106, 180, 255)
DEEP_BLUE = (26, 92, 192)
MID_BLUE = (42, 106, 191)
GRID_LINE = (18, 32, 58)
BORDER_LINE = (26, 37, 64)
TEXT_DIM = (51, 64, 96)
TEXT_SEC = (96, 112, 144)

FONT_BOLD = "C:/Windows/Fonts/segoeuib.ttf"
FONT_REGULAR = "C:/Windows/Fonts/segoeui.ttf"


def draw_aframe(draw, cx, cy, size, color, thickness=2):
    """Draw the A-frame / triangle icon (stylized A) with proper thickness."""
    half = size * 0.5
    # Triangle vertices
    top = (cx, cy - half)
    bl = (cx - size * 0.43, cy + half)
    br = (cx + size * 0.43, cy + half)

    # Draw thick triangle by drawing polygon outline multiple times
    for i in range(thickness):
        scale = 1.0 + i * 0.012
        t = (cx, cy - half * scale)
        l = (cx - size * 0.43 * scale, cy + half + i * 0.4)
        r = (cx + size * 0.43 * scale, cy + half + i * 0.4)
        draw.line([t, l], fill=color, width=thickness)
        draw.line([l, r], fill=color, width=thickness)
        draw.line([r, t], fill=color, width=thickness)

    # Crossbar
    bar_y = cy + size * 0.1
    frac = (bar_y - top[1]) / (bl[1] - top[1])
    lx = top[0] + frac * (bl[0] - top[0])
    rx = top[0] + frac * (br[0] - top[0])
    inset = (rx - lx) * 0.18
    draw.line([(lx + inset, bar_y), (rx - inset, bar_y)], fill=color, width=max(1, thickness))


def draw_grid_lines(draw, w, h, spacing=40, color=GRID_LINE):
    """Draw subtle grid lines across the image."""
    for x in range(0, w, spacing):
        draw.line([(x, 0), (x, h)], fill=color, width=1)
    for y in range(0, h, spacing):
        draw.line([(0, y), (w, y)], fill=color, width=1)


def generate_hero_banner(path, w=1080, h=280):
    """Full hero banner with grid + A-frame + ARCWRIGHT text."""
    img = Image.new("RGBA", (w, h), DEEP_NAVY)
    draw = ImageDraw.Draw(img)

    # Subtle grid background
    draw_grid_lines(draw, w, h, spacing=35, color=GRID_LINE)

    # Very subtle radial glow — just a gentle blue tint, not white
    glow_layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow_layer)
    for r in range(200, 0, -3):
        # Very low alpha so it stays subtle
        alpha = max(1, int(6 * (1.0 - r / 200.0)))
        glow_color = (BRAND_BLUE[0] // 3, BRAND_BLUE[1] // 3, BRAND_BLUE[2] // 2, alpha)
        cx, cy = w // 2, h // 2
        bbox = (cx - r * 2.5, cy - r, cx + r * 2.5, cy + r)
        glow_draw.ellipse(bbox, fill=glow_color)
    img = Image.alpha_composite(img, glow_layer)
    draw = ImageDraw.Draw(img)

    # A-frame icon (large, centered above text)
    icon_cy = h * 0.32
    draw_aframe(draw, w // 2, icon_cy, size=72, color=BRAND_BLUE, thickness=3)

    # "ARCWRIGHT" text below icon
    font_size = 40
    font = ImageFont.truetype(FONT_BOLD, font_size)
    text = "A R C W R I G H T"
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    tx = (w - tw) // 2
    ty = int(h * 0.60)
    draw.text((tx, ty), text, fill=BRAND_BLUE, font=font)

    # Tagline
    tag_font = ImageFont.truetype(FONT_REGULAR, 14)
    tagline = "Architect Your Game from Language"
    bbox2 = draw.textbbox((0, 0), tagline, font=tag_font)
    ttw = bbox2[2] - bbox2[0]
    draw.text(((w - ttw) // 2, ty + font_size + 10), tagline, fill=TEXT_SEC, font=tag_font)

    # Top accent line in brand blue
    draw.line([(0, 0), (w, 0)], fill=BRAND_BLUE, width=2)
    # Bottom subtle border
    draw.line([(0, h - 1), (w, h - 1)], fill=BORDER_LINE, width=1)

    img.save(path, "PNG")
    print(f"  Hero banner: {path} ({w}x{h})")


def generate_logo(path, w=320, h=72):
    """Nav-sized logo: A-frame icon + ARCWRIGHT text on transparent bg."""
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # A-frame icon on left
    icon_size = 30
    icon_cx = 26
    icon_cy = h // 2
    draw_aframe(draw, icon_cx, icon_cy, size=icon_size, color=BRAND_BLUE, thickness=2)

    # "ARCWRIGHT" text
    font_size = 20
    font = ImageFont.truetype(FONT_BOLD, font_size)
    text = "A R C W R I G H T"
    bbox = draw.textbbox((0, 0), text, font=font)
    text_h = bbox[3] - bbox[1]
    tx = icon_cx + icon_size + 14
    ty = (h - text_h) // 2 - 2
    draw.text((tx, ty), text, fill=BRAND_BLUE, font=font)

    img.save(path, "PNG")
    print(f"  Logo: {path} ({w}x{h})")


def generate_icon(path, size=40):
    """Square icon: just the A-frame triangle."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    icon_size = size * 0.65
    thickness = max(2, size // 14)
    draw_aframe(draw, size // 2, size // 2, size=icon_size, color=BRAND_BLUE, thickness=thickness)

    img.save(path, "PNG")
    print(f"  Icon: {path} ({size}x{size})")


def main():
    out_dir = r"C:\Junk\BlueprintLLMTest\Plugins\BlueprintLLM\Resources"
    os.makedirs(out_dir, exist_ok=True)

    src_dir = r"C:\Arcwright\ue_plugin\BlueprintLLM\Resources"
    os.makedirs(src_dir, exist_ok=True)

    print("Generating Arcwright branded PNGs...")

    for d in [out_dir, src_dir]:
        generate_hero_banner(os.path.join(d, "ArcwrightHeroBanner.png"), 1080, 280)
        generate_logo(os.path.join(d, "ArcwrightLogo.png"), 320, 72)
        generate_icon(os.path.join(d, "ArcwrightIcon40.png"), 40)
        generate_icon(os.path.join(d, "ArcwrightIcon16.png"), 16)

    print("Done!")


if __name__ == "__main__":
    main()
