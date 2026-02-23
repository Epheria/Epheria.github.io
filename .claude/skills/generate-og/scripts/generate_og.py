#!/usr/bin/env python3
"""Generate OG image for blog posts with background image and text overlay."""

import argparse
import sys
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("Error: Pillow is required. Install with: pip3 install Pillow")
    sys.exit(1)

# Default accent colors per category (can be overridden via --color)
CATEGORY_COLORS = {
    "security": (100, 180, 160),
    "network": (60, 180, 220),
    "unity": (100, 200, 100),
    "unreal": (80, 120, 220),
    "csharp": (150, 100, 220),
    "cpp": (60, 120, 200),
    "ml": (220, 140, 60),
    "mathematics": (180, 100, 180),
    "python": (60, 160, 200),
    "common": (140, 160, 180),
    "etc": (140, 160, 180),
}

TARGET_W, TARGET_H = 1200, 630

FONT_PATHS = {
    "bold": [
        "/Library/Fonts/Roboto-Bold.ttf",
        "/usr/share/fonts/truetype/roboto/Roboto-Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ],
    "medium": [
        "/Library/Fonts/Roboto-Medium.ttf",
        "/usr/share/fonts/truetype/roboto/Roboto-Medium.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ],
    "regular": [
        "/Library/Fonts/Roboto-Regular.ttf",
        "/usr/share/fonts/truetype/roboto/Roboto-Regular.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ],
}


def find_font(style, size):
    for path in FONT_PATHS[style]:
        try:
            return ImageFont.truetype(path, size)
        except (OSError, IOError):
            continue
    return ImageFont.load_default()


def parse_color(color_str):
    """Parse color string like '100,180,160' into RGB tuple."""
    parts = [int(x.strip()) for x in color_str.split(",")]
    if len(parts) != 3:
        raise ValueError("Color must be R,G,B format")
    return tuple(parts)


def generate_og(source_image, category, output_path, accent_color, overlay_alpha, subtitle):
    src = Image.open(source_image)

    # Crop to 1200x630 aspect ratio
    aspect = TARGET_W / TARGET_H
    src_w, src_h = src.size
    crop_w = src_w
    crop_h = src_w / aspect

    if crop_h > src_h:
        crop_h = src_h
        crop_w = src_h * aspect

    left = (src_w - crop_w) / 2
    top = (src_h - crop_h) / 2
    top = max(0, top)
    right = left + crop_w
    bottom = min(src_h, top + crop_h)

    src_cropped = src.crop((int(left), int(top), int(right), int(bottom)))
    src_resized = src_cropped.resize((TARGET_W, TARGET_H), Image.LANCZOS)

    # Dark overlay
    overlay = Image.new("RGBA", (TARGET_W, TARGET_H), (0, 0, 0, overlay_alpha))
    base = src_resized.convert("RGBA")
    composited = Image.alpha_composite(base, overlay)

    # Left gradient for text readability
    gradient = Image.new("RGBA", (TARGET_W, TARGET_H), (0, 0, 0, 0))
    gradient_draw = ImageDraw.Draw(gradient)
    for x in range(600):
        alpha = int(120 * (1 - x / 600))
        gradient_draw.line([(x, 0), (x, TARGET_H)], fill=(0, 0, 0, alpha))
    composited = Image.alpha_composite(composited, gradient)

    draw = ImageDraw.Draw(composited)

    # Fonts
    font_title = find_font("bold", 52)
    font_subtitle = find_font("medium", 24)
    font_small = find_font("regular", 20)

    # Left accent line
    draw.rectangle([(60, 200), (64, 330)], fill=accent_color)

    # Category text
    draw.text((80, 200), category, fill=(230, 230, 230), font=font_title)

    # Subtitle
    draw.text((80, 270), subtitle, fill=(160, 160, 170), font=font_subtitle)

    # Small accent square
    draw.rectangle([(80, 320), (94, 334)], fill=(120, 140, 150))

    # Bottom URL
    draw.text((60, TARGET_H - 50), "epheria.github.io", fill=accent_color, font=font_small)

    # Save
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    composited.convert("RGB").save(str(output_path), quality=95)
    print(f"Generated: {output_path}")
    print(f"Size: {TARGET_W}x{TARGET_H}")


def main():
    parser = argparse.ArgumentParser(description="Generate OG image for blog posts")
    parser.add_argument("source", help="Source background image path")
    parser.add_argument("category", help="Category name displayed on the image")
    parser.add_argument(
        "-o", "--output",
        help="Output path (default: assets/img/og/{category_lower}.png)",
    )
    parser.add_argument(
        "-c", "--color",
        help="Accent color as R,G,B (default: auto from category)",
    )
    parser.add_argument(
        "--alpha", type=int, default=140,
        help="Overlay darkness 0-255 (default: 140)",
    )
    parser.add_argument(
        "--subtitle", default="Sehyup  |  Game Programmer",
        help="Subtitle text (default: 'Sehyup  |  Game Programmer')",
    )

    args = parser.parse_args()

    category_lower = args.category.lower().replace(" ", "-")

    if args.color:
        accent_color = parse_color(args.color)
    else:
        accent_color = CATEGORY_COLORS.get(category_lower, (140, 160, 180))

    output_path = args.output or f"assets/img/og/{category_lower}.png"

    generate_og(args.source, args.category, output_path, accent_color, args.alpha, args.subtitle)


if __name__ == "__main__":
    main()
