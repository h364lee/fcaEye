"""
Stimulus generator, geometric sets.

Two attribute sets, each with three binary attributes.
Same pipeline as imageGen.py: draw at
SUPERSAMPLE scale, clip a full-canvas pattern layer with a shape mask,
add the outline last, downsample.

    set1 polygons and hashing
        m1 shape       1 rectangle | 0 acute triangle
        m2 texture     1 vertical hashing | 0 horizontal hashing
        m3 orientation 1 long axis vertical | 0 long axis horizontal

    set2 curvilinear and patterns
        m1 size        1 big | 0 little
        m2 form        1 circle | 0 ellipse
        m3 fill        1 dotted regular | 0 dotted irregular

Confound control, same logic as imageGen.py:
  - Patterns are drawn edge to edge and anchored to the canvas centre, so
    hatch and dot spatial frequency does not change with shape or size.
  - Within a set, the two levels of one attribute are matched on the others.
    set1 rectangle and triangle have equal AREA, so shape is not also an ink
    difference. set1 vertical and horizontal hatching share spacing and
    width. set2 circle and ellipse have equal AREA, so form is not also a
    size difference, which matters because size is m1 in the same set.
    set2 irregular dots are the regular lattice with a per-dot random
    displacement, so mean density is unchanged and only regularity differs.
"""

import argparse
import itertools
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

CANVAS_PX = 400
SUPERSAMPLE = 4
INK = (0, 0, 0, 255)
BODY = (255, 255, 255, 255)
OUTLINE_PX = 3

SEED = 20260910          # irregular fill is random but reproducible

SETS = {
    "set1": {"shape": ["rectangle", "triangle"],
             "texture": ["vertical", "horizontal"],
             "orientation": ["axis_v", "axis_h"]},
    "set2": {"size": ["big", "little"],
             "form": ["circle", "ellipse"],
             "fill": ["regular", "irregular"]},
}

# Which of the 8 combinations serve as g1..g5, per set. Arbitrary; edit freely.
#
# The visual attributes are NOT the attributes of the formal context. They
# only have to make the five objects tell each other apart. The context is
# assigned separately below, and it has to be, because M3 cannot be built
# from five DISTINCT three-bit rows: in M3 every pair of attributes meets at
# the bottom, so no object may carry two attributes, which leaves only four
# distinct rows (000, 100, 010, 001) and the fifth object must repeat one.
# Repeating a row is only possible when appearance and incidence are separate.
OBJECTS = {
    "set1": {
        "g1": ("rectangle", "vertical", "axis_v"),
        "g2": ("rectangle", "horizontal", "axis_v"),
        "g3": ("triangle", "vertical", "axis_h"),
        "g4": ("triangle", "horizontal", "axis_h"),
        "g5": ("rectangle", "vertical", "axis_h"),
    },
    "set2": {
        "g1": ("big", "circle", "regular"),
        "g2": ("big", "circle", "irregular"),
        "g3": ("little", "ellipse", "regular"),
        "g4": ("little", "ellipse", "irregular"),
        "g5": ("big", "ellipse", "regular"),
    },
}

# Same incidence as imageGen.py, so a set can be swapped into a phase without
# changing the lattice under test.
FORMAL_CONTEXTS = {
    "M3": {"g1": [1, 0, 0], "g2": [1, 0, 0], "g3": [0, 1, 0], "g4": [0, 1, 0], "g5": [0, 0, 1]},
    "N5": {"g1": [1, 1, 0], "g2": [1, 0, 0], "g3": [0, 0, 1], "g4": [0, 0, 1], "g5": [0, 0, 0]},
}

# Fractions of the canvas.
GEOMETRY = {
    # set1: area of every silhouette, as a fraction of canvas area
    "area_set1": 0.20,
    # set2: silhouette area for each size level
    "area_set2": {"big": 0.26, "little": 0.12},
    # long axis : short axis, for the oriented shapes and the ellipse
    "aspect": 2.0,
    # hatching
    "hatch_spacing": 0.075,
    "hatch_width": 0.020,
    # dots. jitter is the max displacement as a fraction of spacing
    "dot_spacing": 0.075,
    "dot_radius": 0.017,
    "dot_jitter": 0.45,
}


# ------------------------------------------------------------- silhouettes

def rectangle(area, aspect, vertical, side):
    """Axis-aligned rectangle of the given area, centred."""
    short = math.sqrt(area / aspect)
    long_ = short * aspect
    w, h = (short, long_) if vertical else (long_, short)
    c = side / 2
    return "rectangle", [c - w / 2, c - h / 2, c + w / 2, c + h / 2]


def triangle(area, aspect, vertical, side):
    """Isoceles triangle of the given area, height:base = aspect.

    All three angles are acute whenever aspect > 0.5: the apex angle is
    2*atan(base/2h), which is below 90 degrees once h > base/2, and the two
    base angles are then each below 90 by the angle sum.
    """
    base = math.sqrt(2 * area / aspect)     # area = base * height / 2
    height = aspect * base
    c = side / 2
    if vertical:                            # apex up
        pts = [(c, c - height / 2),
               (c - base / 2, c + height / 2),
               (c + base / 2, c + height / 2)]
    else:                                   # apex right
        pts = [(c + height / 2, c),
               (c - height / 2, c - base / 2),
               (c - height / 2, c + base / 2)]
    return "polygon", pts


def circle(area, side):
    r = math.sqrt(area / math.pi)
    c = side / 2
    return "ellipse", [c - r, c - r, c + r, c + r]


def ellipse(area, aspect, side):
    """Long axis horizontal, fixed: orientation is not an attribute here."""
    b = math.sqrt(area / (math.pi * aspect))    # area = pi * a * b
    a = aspect * b
    c = side / 2
    return "ellipse", [c - a, c - b, c + a, c + b]


# ---------------------------------------------------------------- patterns

def hatching(orientation, side):
    """Parallel lines across the whole canvas, centred."""
    layer = Image.new("RGBA", (side, side), BODY)
    draw = ImageDraw.Draw(layer)
    c = side / 2
    s = GEOMETRY["hatch_spacing"] * side
    w = max(1, round(GEOMETRY["hatch_width"] * side))
    offsets = [i * s for i in range(-int(c / s) - 1, int(c / s) + 2)]
    for d in offsets:
        if orientation == "vertical":
            draw.line([(c + d, 0), (c + d, side)], fill=INK, width=w)
        else:
            draw.line([(0, c + d), (side, c + d)], fill=INK, width=w)
    return layer


def dots(fill, side, rng):
    """Dot lattice across the whole canvas, centred.

    Irregular is the same lattice with each dot displaced independently by
    up to dot_jitter * spacing in x and y. Dot count and radius are
    unchanged, so the two levels differ in regularity, not in coverage.
    """
    layer = Image.new("RGBA", (side, side), BODY)
    draw = ImageDraw.Draw(layer)
    c = side / 2
    s = GEOMETRY["dot_spacing"] * side
    r = GEOMETRY["dot_radius"] * side
    j = GEOMETRY["dot_jitter"] * s if fill == "irregular" else 0.0
    offsets = [i * s for i in range(-int(c / s) - 2, int(c / s) + 3)]
    for dx in offsets:
        for dy in offsets:
            x = c + dx + rng.uniform(-j, j)
            y = c + dy + rng.uniform(-j, j)
            draw.ellipse([x - r, y - r, x + r, y + r], fill=INK)
    return layer


# ----------------------------------------------------------------- render

def silhouette(set_name, combo, side):
    if set_name == "set1":
        shape, _texture, orientation = combo
        area = GEOMETRY["area_set1"] * side * side
        vertical = orientation == "axis_v"
        if shape == "rectangle":
            return rectangle(area, GEOMETRY["aspect"], vertical, side)
        return triangle(area, GEOMETRY["aspect"], vertical, side)

    size, form, _fill = combo
    area = GEOMETRY["area_set2"][size] * side * side
    if form == "circle":
        return circle(area, side)
    return ellipse(area, GEOMETRY["aspect"], side)


def render(set_name, combo, rng):
    """One object, RGBA with a transparent background."""
    side = CANVAS_PX * SUPERSAMPLE
    kind, geom = silhouette(set_name, combo, side)

    if set_name == "set1":
        layer = hatching(combo[1], side)
    else:
        layer = dots(combo[2], side, rng)

    mask = Image.new("L", (side, side), 0)
    getattr(ImageDraw.Draw(mask), kind)(geom, fill=255)

    image = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    image.paste(layer, (0, 0), mask)

    # Outline last, so the pattern never overwrites it.
    edge = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    getattr(ImageDraw.Draw(edge), kind)(geom, outline=INK,
                                        width=OUTLINE_PX * SUPERSAMPLE)

    return Image.alpha_composite(image, edge).resize(
        (CANVAS_PX, CANVAS_PX), Image.LANCZOS)


# ----------------------------------------------------------------- output

def generate(out_dir="stims_geo", preview=True):
    """Each set gets its own directory laid out exactly like stims/, so a set
    is a drop-in replacement for the stimulus folder experiment.py reads:

        stims_geo/set1/manifest.json
        stims_geo/set1/objects/<code>.png
        stims_geo/set1/preview.png

    A combined manifest at the top level lists both sets, for anything that
    needs to see them together.
    """
    out_dir = Path(out_dir)
    rng = np.random.default_rng(SEED)
    combined = {"canvas_px": CANVAS_PX, "geometry": GEOMETRY,
                "seed": SEED, "sets": {}}

    for set_name, attributes in SETS.items():
        set_dir = out_dir / set_name
        (set_dir / "objects").mkdir(parents=True, exist_ok=True)
        names = {v: k for k, v in OBJECTS[set_name].items()}

        objects = {}
        for combo in itertools.product(*attributes.values()):
            code = "-".join(combo)
            render(set_name, combo, rng).save(set_dir / "objects" / f"{code}.png")
            objects[code] = {
                "object": names.get(combo),                 # None if unused
                "features": dict(zip(attributes, combo)),
                # Bits as written in the stimulus spec: first level of each
                # attribute is 1. Visual coding only, not the context.
                "m": [1 if v == levels[0] else 0
                      for v, levels in zip(combo, attributes.values())],
                "file": f"objects/{code}.png",              # POSIX, both platforms
            }

        manifest = {
            "canvas_px": CANVAS_PX,
            "set": set_name,
            "attributes": attributes,
            "geometry": GEOMETRY,
            "seed": SEED,
            "objects": objects,
            "object_assignment": {k: "-".join(v)
                                  for k, v in OBJECTS[set_name].items()},
            "formal_contexts": FORMAL_CONTEXTS,
        }
        (set_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
        combined["sets"][set_name] = manifest

        if preview:
            make_preview(objects, set_dir)

    (out_dir / "manifest.json").write_text(json.dumps(combined, indent=2))
    return combined


def make_preview(objects, set_dir):
    """Contact sheet on mid grey: the intended background, and it shows
    whether the PNGs are really transparent."""
    cols, cell, label = 4, CANVAS_PX, 30
    rows = -(-len(objects) // cols)
    sheet = Image.new("RGB", (cols * cell, rows * (cell + label)), (128, 128, 128))
    draw = ImageDraw.Draw(sheet)
    for i, (code, entry) in enumerate(objects.items()):
        r, c = divmod(i, cols)
        img = Image.open(set_dir / entry["file"])
        sheet.paste(img, (c * cell, r * (cell + label)), img)
        draw.text((c * cell + 8, r * (cell + label) + cell + 8),
                  f"{entry['object'] or '-'}  m={''.join(map(str, entry['m']))}"
                  f"  {code}", fill=(255, 255, 255))
    sheet.save(set_dir / "preview.png")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--out", default="stims_geo")
    p.add_argument("--no-preview", action="store_true")
    args = p.parse_args()
    m = generate(args.out, preview=not args.no_preview)
    for set_name, entry in m["sets"].items():
        print(set_name)
        for code, e in entry["objects"].items():
            print(f"  {e['object'] or ' ':>3}  m={''.join(map(str, e['m']))}  {code}")
