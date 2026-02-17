#!/usr/bin/env python3
"""Generate category-specific OG images for the blog."""

from PIL import Image, ImageDraw, ImageFont
import os

# Output settings
WIDTH, HEIGHT = 1200, 630
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "assets", "img", "og")

# Colors from the original OG image
BG_TOP = (42, 40, 62)       # dark purple-gray top
BG_BOTTOM = (52, 50, 72)    # slightly lighter bottom
TEXT_WHITE = (220, 220, 225)
TEXT_GRAY = (140, 140, 160)
URL_COLOR = (120, 130, 190)

# Category configs: (directory_name, display_name, accent_color)
CATEGORIES = [
    ("Common",       "Common",          (120, 144, 216)),  # blue (default-like)
    ("Csharp",       "C#",              (104, 33, 122)),   # purple (C# brand)
    ("cpp",          "C++",             (0, 89, 156)),     # blue (C++ brand)
    ("ETC",          "ETC",             (130, 140, 150)),  # gray
    ("Investment",   "Investment",      (46, 139, 87)),    # green
    ("Language",     "Language",        (218, 165, 32)),   # gold
    ("Mathematics",  "Mathematics",     (70, 130, 180)),   # steel blue
    ("ML",           "Machine Learning",(255, 111, 0)),    # orange
    ("Pobos",        "Pobos",           (180, 80, 80)),    # red
    ("Python",       "Python",          (55, 118, 171)),   # python blue
    ("Survivor",     "Survivor",        (200, 60, 60)),    # red
    ("TheQuesting",  "The Questing",    (160, 120, 60)),   # bronze
    ("Toyverse",     "Toyverse",        (180, 100, 200)),  # violet
    ("Unity",        "Unity",           (100, 100, 100)),  # unity gray
    ("Unreal",       "Unreal Engine",   (45, 45, 45)),     # dark (UE brand)
]

# Fonts
FONT_BOLD = "/Library/Fonts/Roboto-Bold.ttf"
FONT_MEDIUM = "/Library/Fonts/Roboto-Medium.ttf"
FONT_REGULAR = "/Library/Fonts/Roboto-Regular.ttf"


def create_gradient(draw, width, height, top_color, bottom_color):
    """Create a vertical gradient background."""
    for y in range(height):
        ratio = y / height
        r = int(top_color[0] + (bottom_color[0] - top_color[0]) * ratio)
        g = int(top_color[1] + (bottom_color[1] - top_color[1]) * ratio)
        b = int(top_color[2] + (bottom_color[2] - top_color[2]) * ratio)
        draw.line([(0, y), (width, y)], fill=(r, g, b))


def generate_og_image(dir_name, display_name, accent_color):
    """Generate a single OG image for a category."""
    img = Image.new("RGB", (WIDTH, HEIGHT))
    draw = ImageDraw.Draw(img)

    # Background gradient
    create_gradient(draw, WIDTH, HEIGHT, BG_TOP, BG_BOTTOM)

    # Accent bar (left side decorative element)
    bar_x, bar_y = 80, 220
    bar_w, bar_h = 8, 120
    draw.rectangle([bar_x, bar_y, bar_x + bar_w, bar_y + bar_h], fill=accent_color)

    # Category name (large)
    font_category = ImageFont.truetype(FONT_BOLD, 72)
    draw.text((110, 210), display_name, font=font_category, fill=TEXT_WHITE)

    # "Sehyup | Game Programmer" subtitle
    font_subtitle = ImageFont.truetype(FONT_REGULAR, 32)
    draw.text((112, 300), "Sehyup  |  Game Programmer", font=font_subtitle, fill=TEXT_GRAY)

    # Accent dot (small square next to category)
    dot_size = 36
    draw.rectangle(
        [80, bar_y + bar_h + 30, 80 + dot_size, bar_y + bar_h + 30 + dot_size],
        fill=(*accent_color, 0),
    )

    # URL at bottom
    font_url = ImageFont.truetype(FONT_MEDIUM, 22)
    draw.text((80, HEIGHT - 70), "epheria.github.io", font=font_url, fill=URL_COLOR)

    # Decorative accent line at top
    draw.rectangle([0, 0, WIDTH, 4], fill=accent_color)

    # Save
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    filename = f"{dir_name.lower()}.png"
    filepath = os.path.join(OUTPUT_DIR, filename)
    img.save(filepath, "PNG", optimize=True)
    print(f"  Created: {filepath}")
    return filepath


def main():
    print(f"Generating {len(CATEGORIES)} category OG images...")
    print(f"Output: {OUTPUT_DIR}\n")

    for dir_name, display_name, accent_color in CATEGORIES:
        generate_og_image(dir_name, display_name, accent_color)

    # Also copy the default
    print(f"\nDone! {len(CATEGORIES)} images generated.")
    print("Remember to update _config.yml with category-specific defaults.")


if __name__ == "__main__":
    main()
