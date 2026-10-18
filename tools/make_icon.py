import os
from PIL import Image, ImageDraw

def create_app_icon():
    os.makedirs("assets", exist_ok=True)
    size = 512
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 1. Outer rounded container (Squircle style)
    pad = 28
    radius = 110
    
    # Background gradient approximation using multiple rounded rectangles
    for step in range(30):
        t = step / 30.0
        # Gradient from deep dark navy (15, 23, 42) to indigo (30, 27, 75)
        r = int(15 + t * 25)
        g = int(23 + t * 15)
        b = int(42 + t * 50)
        inset = pad + int(step * 0.8)
        draw.rounded_rectangle(
            [inset, inset, size - inset, size - inset],
            radius=max(10, radius - int(step * 1.5)),
            fill=(r, g, b, 255)
        )

    # 2. Glowing outer border rim
    draw.rounded_rectangle(
        [pad, pad, size - pad, size - pad],
        radius=radius,
        outline=(56, 189, 248, 220), # Electric cyan outline
        width=8
    )

    # 3. Inner Vault Shield Contour
    # Coordinates for a stylized vault shield
    shield_pts = [
        (256, 100), # Top tip
        (400, 160), # Top right
        (380, 330), # Mid right
        (256, 420), # Bottom tip
        (132, 330), # Mid left
        (112, 160), # Top left
    ]
    draw.polygon(shield_pts, fill=(24, 32, 60, 240), outline=(99, 102, 241, 200))

    # 4. Stylized High-Tech Download Arrow inside the shield
    # Arrow stem
    draw.rounded_rectangle([236, 165, 276, 280], radius=8, fill=(56, 189, 248, 255))
    
    # Arrow head (triangle)
    head_pts = [
        (185, 270),
        (327, 270),
        (256, 345)
    ]
    draw.polygon(head_pts, fill=(56, 189, 248, 255))

    # Tray / Vault base (receiving the download)
    tray_pts = [
        (175, 360),
        (337, 360),
        (322, 385),
        (190, 385)
    ]
    draw.polygon(tray_pts, fill=(168, 85, 247, 255)) # Violet accent
    
    # Highlight dot / speed particle
    draw.ellipse([246, 135, 266, 155], fill=(255, 255, 255, 240))

    # Save high-res PNG
    png_path = os.path.join("assets", "icon.png")
    img.save(png_path, "PNG")
    print(f"Saved {png_path}")

    # Generate multi-size ICO
    ico_path = os.path.join("assets", "icon.ico")
    icon_sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
    img.save(ico_path, format="ICO", sizes=icon_sizes)
    print(f"Saved multi-resolution {ico_path}")

if __name__ == "__main__":
    create_app_icon()
