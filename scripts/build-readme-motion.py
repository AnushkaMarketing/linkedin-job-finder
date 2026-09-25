"""Build a GitHub-compatible animated fallback for the README hero."""
from math import cos, sin, pi
from pathlib import Path
from PIL import Image, ImageDraw

out = Path(__file__).parents[1] / "docs" / "particle-loop.gif"
frames = []
for frame in range(24):
    image = Image.new("RGB", (1200, 420), "#0b1421")
    draw = ImageDraw.Draw(image)
    # A moving constellation that remains visible in GitHub's image proxy.
    for i in range(280):
        angle = (i * 2.399963 + frame * 0.08) % (2 * pi)
        radius = 35 + ((i * 37) % 180)
        x = 880 + cos(angle) * radius * 1.45
        y = 210 + sin(angle) * radius * 0.72
        color = (148, 245, 204) if i % 3 == 0 else (93, 142, 255)
        size = 1 if i % 5 else 2
        draw.ellipse((x-size, y-size, x+size, y+size), fill=color)
    for path in range(3):
        points = []
        for step in range(120):
            x = 710 + step * 3.3
            y = 210 + sin(step * 0.12 + frame * 0.14 + path) * (28 + path * 14)
            points.append((x, y))
        draw.line(points, fill=(148, 245, 204), width=1)
    draw.rectangle((48, 64, 76, 68), fill=(148, 245, 204))
    draw.text((90, 55), "SIGNAL / ENGINE 02", fill=(148, 245, 204))
    draw.text((48, 150), "Find the work", fill=(240, 245, 255), stroke_width=0)
    draw.text((48, 215), "that fits.", fill=(240, 245, 255), stroke_width=0)
    draw.text((50, 286), "Less noise. Clearer evidence. Your next move.", fill=(174, 190, 211))
    frames.append(image)
frames[0].save(out, save_all=True, append_images=frames[1:], duration=90, loop=0, optimize=True)
print(out)
