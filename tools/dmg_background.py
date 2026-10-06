"""Draw the background of the macOS .dmg window: where to drag the app, and
how to get past Gatekeeper on the first start.

    python -m tools.dmg_background <out_dir>

Writes background.png and background@2x.png (Retina); build_app.sh joins them
into one .tiff with tiffutil and lays the icons out on top (create-dmg). It
takes the icon positions from what this prints (DMG_W=660 ...), so the drawing
and the icons share LAYOUT, in window points.
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

LAYOUT = {
    "window": (660, 480),
    "app": (170, 140),
    "applications": (490, 140),
    "readme": (170, 395),
    "manual": (330, 395),
    "handbuch": (490, 395),
    "icon_size": 96,
}

TITLE = "Drag the app onto Applications  ·  App auf Programme ziehen"
HINT = [
    ("First start blocked?  ·  Erster Start blockiert?", True),
    ("System Settings › Privacy & Security › Open Anyway", False),
    ("Systemeinstellungen › Datenschutz & Sicherheit › Trotzdem öffnen", False),
]

BG = (246, 246, 248)
INK = (40, 40, 48)
SOFT = (110, 110, 120)
ACCENT = (200, 60, 50)

# Helvetica on the Mac that builds it; Arial where this is tried on Windows.
FONTS = {
    False: [("/System/Library/Fonts/Helvetica.ttc", 0), ("arial.ttf", 0)],
    True: [("/System/Library/Fonts/Helvetica.ttc", 1), ("arialbd.ttf", 0)],
}


def font(size, bold=False):
    for path, index in FONTS[bold]:
        try:
            return ImageFont.truetype(path, size, index=index)
        except OSError:
            continue
    return ImageFont.load_default(size)


def draw(scale):
    w, h = LAYOUT["window"]
    img = Image.new("RGB", (w * scale, h * scale), BG)
    d = ImageDraw.Draw(img)

    def centered(text, y, size, fill, bold=False):
        d.text((w * scale / 2, y * scale), text, fill=fill,
               font=font(size * scale, bold), anchor="mm")

    centered(TITLE, 30, 15, SOFT)

    # The arrow from the app to the Applications folder.
    (ax, ay), (bx, _) = LAYOUT["app"], LAYOUT["applications"]
    half = LAYOUT["icon_size"] / 2 + 24
    x0, x1, y = (ax + half) * scale, (bx - half) * scale, ay * scale
    d.line([(x0, y), (x1 - 14 * scale, y)], fill=SOFT, width=4 * scale)
    d.polygon([(x1, y), (x1 - 18 * scale, y - 11 * scale),
               (x1 - 18 * scale, y + 11 * scale)], fill=SOFT)

    # The Gatekeeper hint, in a box between the icons' labels and the README
    # and manuals.
    top, bottom = 250, 340
    d.rounded_rectangle([40 * scale, top * scale, (w - 40) * scale, bottom * scale],
                        radius=10 * scale, fill=(255, 255, 255),
                        outline=ACCENT, width=2 * scale)
    for i, (text, bold) in enumerate(HINT):
        centered(text, top + 22 + i * 24, 15 if bold else 13,
                 ACCENT if bold else INK, bold)
    return img


def shell_vars():
    """LAYOUT as the shell variables build_app.sh reads."""
    out = {"DMG_W": LAYOUT["window"][0], "DMG_H": LAYOUT["window"][1],
           "DMG_ICON": LAYOUT["icon_size"]}
    for key in ("app", "applications", "readme", "manual", "handbuch"):
        out[f"{key.upper()}_X"], out[f"{key.upper()}_Y"] = LAYOUT[key]
    return out


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    out = Path(argv[0] if argv else ".")
    out.mkdir(parents=True, exist_ok=True)
    draw(1).save(out / "background.png")
    draw(2).save(out / "background@2x.png")
    for name, value in shell_vars().items():
        print(f"{name}={value}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
