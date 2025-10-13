#!/usr/bin/env python3
"""
Generate favicon.ico with multiple sizes from SVG
"""
from PIL import Image, ImageDraw
import os

def create_favicon():
    """Create a fraud detection shield favicon"""

    # Create images at different sizes for the .ico file
    sizes = [(16, 16), (32, 32), (48, 48), (64, 64)]
    images = []

    for size in sizes:
        # Create new image with transparency
        img = Image.new('RGBA', size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        width, height = size

        # Scale factors
        scale = width / 64.0

        # Shield outline (simplified polygon)
        shield_points = [
            (width * 0.5, height * 0.06),   # Top center
            (width * 0.84, height * 0.19),  # Top right
            (width * 0.84, height * 0.44),  # Right middle
            (width * 0.5, height * 0.91),   # Bottom center
            (width * 0.16, height * 0.44),  # Left middle
            (width * 0.16, height * 0.19),  # Top left
        ]

        # Draw shield with gradient effect (use solid color for simplicity)
        # Main shield - red color for fraud detection/alert
        draw.polygon(shield_points, fill=(231, 76, 60, 255), outline=(153, 45, 34, 255))

        # Add alert symbol (exclamation mark)
        # Calculate sizes
        bar_width = max(2, int(width * 0.09))
        bar_height = max(8, int(height * 0.31))
        bar_x = int(width * 0.5 - bar_width / 2)
        bar_y = int(height * 0.28)

        # Exclamation bar
        draw.rounded_rectangle(
            [bar_x, bar_y, bar_x + bar_width, bar_y + bar_height],
            radius=max(1, int(bar_width * 0.3)),
            fill=(255, 255, 255, 255)
        )

        # Exclamation dot
        dot_radius = max(1, int(width * 0.055))
        dot_y = int(height * 0.69)
        draw.ellipse(
            [width/2 - dot_radius, dot_y - dot_radius,
             width/2 + dot_radius, dot_y + dot_radius],
            fill=(255, 255, 255, 255)
        )

        images.append(img)

    # Save as .ico with multiple sizes
    output_path = 'app/static/favicon.ico'
    os.makedirs('app/static', exist_ok=True)
    images[0].save(
        output_path,
        format='ICO',
        sizes=[(img.width, img.height) for img in images],
        append_images=images[1:]
    )

    print(f"✓ Created {output_path} with sizes: {[f'{s[0]}x{s[1]}' for s in sizes]}")

    # Also save a 32x32 PNG for modern browsers
    images[1].save('app/static/favicon.png', format='PNG')
    print("✓ Created app/static/favicon.png (32x32)")

if __name__ == '__main__':
    create_favicon()
    print("\n✅ Favicon generation complete!")
    print("\nNext steps:")
    print("1. Restart your FastAPI server")
    print("2. Add favicon route to main.py if not already present")
