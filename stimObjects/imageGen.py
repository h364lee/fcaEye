"""
Stimulus image generator
"""

import argparse
import itertools
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

CANVAS_PX = 400      # identical for every object, so PsychoPy never rescales one differently
SUPERSAMPLE = 4      # PIL does not antialias shapes; draw big, downsample
INK = (0, 0, 0, 255)
BODY = (255, 255, 255, 255)
OUTLINE_PX = 3

ATTRIBUTES = {
    "shape": ["square", "circle"],
    "element": ["dots", "lines"],
    "density": ["sparse", "dense"],
}

# Which of the 8 combinations serve as g1..g5. Arbitrary; edit freely.
OBJECTS = {
    "g1": ("square", "dots", "sparse"),
    "g2": ("square", "lines", "sparse"),
    "g3": ("circle", "dots", "dense"),
    "g4": ("circle", "lines", "dense"),
    "g5": ("square", "dots", "dense"),
}

FORMAL_CONTEXTS = {
    "M3": {"g1": [1, 0, 0], "g2": [1, 0, 0], "g3": [0, 1, 0], "g4": [0, 1, 0], "g5": [0, 0, 1]},
    "N5": {"g1": [1, 1, 0], "g2": [1, 0, 0], "g3": [0, 0, 1], "g4": [0, 0, 1], "g5": [0, 0, 0]},
}

# Fractions of the canvas, so CANVAS_PX rescales everything consistently.
# Density is element frequency, so it lives in spacing. Coverage is matched
# across element types within a density level so that dots/lines is not also
# a brightness difference: lines cover w/s, dots cover pi*r^2/s^2.
GEOMETRY = {
    "extent": 0.72,
    "spacing": {"sparse": 0.115, "dense": 0.050},
    "coverage": {"sparse": 0.15, "dense": 0.40},
}


def outline(shape, side):
    """Silhouette of the shape. Square and circle share a bounding box."""
    c, half = side / 2, GEOMETRY["extent"] * side / 2
    box = [c - half, c - half, c + half, c + half]
    if shape == "circle":
        return "ellipse", box
    return "polygon", [(box[0], box[1]), (box[2], box[1]), (box[2], box[3]), (box[0], box[3])]


def pattern(element, density, side):
    """Elements across the whole canvas, to be clipped by the shape mask.

    Drawn edge to edge rather than fitted to each shape, so spatial frequency
    does not change with shape; anchored to the centre so square and circle
    versions show the same part of the pattern.
    """
    layer = Image.new("RGBA", (side, side), BODY)
    draw = ImageDraw.Draw(layer)
    c = side / 2
    s = GEOMETRY["spacing"][density] * side
    cov = GEOMETRY["coverage"][density]
    offsets = [i * s for i in range(-int(c / s) - 1, int(c / s) + 2)]

    if element == "lines":
        w = max(1, round(cov * s))
        for dy in offsets:
            draw.line([(0, c + dy), (side, c + dy)], fill=INK, width=w)
    else:
        r = s * np.sqrt(cov / np.pi)
        for dx in offsets:
            for dy in offsets:
                x, y = c + dx, c + dy
                draw.ellipse([x - r, y - r, x + r, y + r], fill=INK)
    return layer


def render(shape, element, density):
    """One object, RGBA with a transparent background."""
    side = CANVAS_PX * SUPERSAMPLE
    kind, geom = outline(shape, side)

    mask = Image.new("L", (side, side), 0)
    getattr(ImageDraw.Draw(mask), kind)(geom, fill=255)

    image = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    image.paste(pattern(element, density, side), (0, 0), mask)

    # Outline last, so the elements never overwrite it.
    edge = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    getattr(ImageDraw.Draw(edge), kind)(geom, outline=INK, width=OUTLINE_PX * SUPERSAMPLE)

    return Image.alpha_composite(image, edge).resize((CANVAS_PX, CANVAS_PX), Image.LANCZOS)


def generate(out_dir="stims", preview=True):
    out_dir = Path(out_dir)
    (out_dir / "objects").mkdir(parents=True, exist_ok=True)
    names = {v: k for k, v in OBJECTS.items()}

    objects = {}
    for combo in itertools.product(*ATTRIBUTES.values()):
        code = "-".join(combo)
        render(*combo).save(out_dir / "objects" / f"{code}.png")
        objects[code] = {
            "object": names.get(combo),                    # None if unused
            "features": dict(zip(ATTRIBUTES, combo)),
            "file": f"objects/{code}.png",                 # POSIX: works on macOS and Windows
        }

    manifest = {
        "canvas_px": CANVAS_PX,
        "attributes": ATTRIBUTES,
        "geometry": GEOMETRY,
        "objects": objects,
        "object_assignment": {k: "-".join(v) for k, v in OBJECTS.items()},
        "formal_contexts": FORMAL_CONTEXTS,
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))

    if preview:
        make_preview(objects, out_dir)
    return manifest


def make_preview(objects, out_dir):
    """Contact sheet on mid grey, which is the intended background and also
    shows whether the PNGs are really transparent."""
    cols, cell, label = 4, CANVAS_PX, 30
    rows = -(-len(objects) // cols)
    sheet = Image.new("RGB", (cols * cell, rows * (cell + label)), (128, 128, 128))
    draw = ImageDraw.Draw(sheet)
    for i, (code, entry) in enumerate(objects.items()):
        r, c = divmod(i, cols)
        img = Image.open(out_dir / entry["file"])
        sheet.paste(img, (c * cell, r * (cell + label)), img)
        draw.text((c * cell + 8, r * (cell + label) + cell + 8),
                  f"{entry['object'] or '-'}  {code}", fill=(255, 255, 255))
    sheet.save(out_dir / "preview.png")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--out", default="stims")
    p.add_argument("--no-preview", action="store_true")
    args = p.parse_args()
    m = generate(args.out, preview=not args.no_preview)
    for code, e in m["objects"].items():
        print(f"  {e['object'] or ' ':>3}  {code}")
