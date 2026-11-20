"""Draw3 Example — Generates Animated Shapes & Colors for C++ OpenGL Renderer.

Constructs visual shapes with animated HSV cycle, pulsing border widths,
and rich colors, and serializes the complete scene to scene.json for the C++ backend.
"""

import json
import os
import sys

# Ensure Draw module is on path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import Draw
from Draw import color

def generate_scene():
    Draw.shapes.clear()
    Draw.color.clear()

    print("Generating shapes with Draw.shape and Draw.color...")

    # 1. Central hexagon with rainbow cycling body and complementary border
    star = Draw.shape(
        name="central_hex",
        vertices=6,
        size=(200.0, 200.0),
        position=(0.0, 0.0),
        color=Draw.color(
            name="central_theme",
            body=color.body(
                fill=color.hsv(
                    h=color.cycle(speed=60.0),   # 60 degrees/second
                    s=90.0,
                    v=100.0,
                )
            ),
            border=color.border(
                fill=color.hsv(
                    h=color.cycle(speed=60.0, offset=180.0),  # Complementary (+180 deg)
                    s=100.0,
                    v=100.0,
                ),
                width=4.0,
            ),
        ),
    )

    # 2. Pulsing neon card on the left
    card = Draw.shape(
        name="pulsing_card",
        type="rectangle",
        size=(220.0, 140.0),
        position=(-300.0, 0.0),
        color=Draw.color(
            name="card_theme",
            body=color.body(fill="#0f172a"),  # Deep navy fill
            border=color.border(
                fill=color.rgb(56, 189, 248),  # Cyan
                width=color.pulse(min_val=2.0, max_val=8.0, speed=2.0),
            ),
        ),
    )

    # 3. Oscillating badge on the right
    badge = Draw.shape(
        name="oscillating_badge",
        vertices=8,
        size=(180.0, 180.0),
        position=(300.0, 0.0),
        color=Draw.color(
            name="badge_theme",
            body=color.body(fill=color.rgb(220, 38, 38)),  # Crimson red
            border=color.border(
                fill=color.hsv(h=color.cycle(speed=90.0), s=100.0, v=100.0),
                width=3.0,
            ),
        ),
    )

    # Serialize scene shapes and their color data
    scene_data = {
        "title": "Draw3 OpenGL Visual Color & Shape Test",
        "canvas": [960.0, 720.0],
        "shapes": [
            star.to_dict(),
            card.to_dict(),
            badge.to_dict(),
        ],
    }

    output_path = os.path.join(project_root, "rander_engin", "scene.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(scene_data, f, indent=2)

    print(f"Scene successfully written to: {output_path}")
    return output_path

if __name__ == "__main__":
    generate_scene()
