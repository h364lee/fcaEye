"""Draw one image per combination of the 6 binary visual features.

Features only, not attributes: design.object_image() maps objects to images.
File names are 0/1 digits in IMAGE_NAME_ORDER (100001.png = orange circle).
Run to draw all 64 images:  python stimuli.py
"""

import math
from itertools import product

import numpy as np
from PIL import Image, ImageDraw

from config import IMAGE_NAME_ORDER, PATHS

# Each feature is from a different guiding attribute in Wolfe & Horowitz
# (2017): colour, orientation (stripes), luminance polarity (outline),
# topological status (hole), line termination (slot), curvature (circle).
# No feature reaches farther from the centre than the square's corners.

# Sizes in pixels. PsychoPy scales the image down to
# GEOMETRY["objSize_px"], so a large canvas keeps edges smooth.
CANVAS = 1200
CENTRE = CANVAS / 2
SQUARE_HALF = 450                                 # centre to side
# Circle has the same area as the square, so they look the same size:
# r = half * 2 / sqrt(pi), about 508; still inside the corners (about 636).
CIRCLE_RADIUS = SQUARE_HALF * 2 / math.sqrt(math.pi)

OUTLINE_WIDTH = 40
HOLE_RADIUS = 200
SLOT_HALF_WIDTH = 70
# Same for both shapes, so the slot-to-hole gap is always about 118 px.
SLOT_INNER = CIRCLE_RADIUS - 190
STRIPE_PERIOD = 150          # measured along x
STRIPE_WIDTH = 45            # dark part of each period, along x

GRAY = (200, 200, 200)       # lighter than the mid-gray screen background
ORANGE = (255, 102, 0)
BLACK = (0, 0, 0)


def _draw_slot(draw, grow, fill):
    """Draw the slot: a cut from the top-left edge toward the centre, with a
    rounded inner end.

    grow: widen by this many px on every side (used for the outline).
    """
    # u points to the top left (image y grows downward); v is perpendicular
    u = (-1 / math.sqrt(2), -1 / math.sqrt(2))
    v = (-u[1], u[0])
    half_w = SLOT_HALF_WIDTH + grow
    # Round end centred here, so its inner edge is at SLOT_INNER - grow
    end = SLOT_INNER + SLOT_HALF_WIDTH
    outer = SQUARE_HALF * math.sqrt(2) + 60       # past the square's corner
    rect = [(CENTRE + u[0] * s + v[0] * t, CENTRE + u[1] * s + v[1] * t)
            for s, t in [(end, -half_w), (outer, -half_w),
                         (outer, half_w), (end, half_w)]]
    draw.polygon(rect, fill=fill)
    x, y = CENTRE + u[0] * end, CENTRE + u[1] * end
    draw.ellipse([x - half_w, y - half_w, x + half_w, y + half_w], fill=fill)


def _shape_mask(ft, inset=0, slot=True):
    """Boolean mask of the shape (square or circle, minus the slot).

    inset: move every edge inward by this many px.
    slot: False ignores the slot.
    """
    mask = Image.new("L", (CANVAS, CANVAS), 0)
    draw = ImageDraw.Draw(mask)
    if ft["circle"]:
        r = CIRCLE_RADIUS - inset
        draw.ellipse([CENTRE - r, CENTRE - r, CENTRE + r, CENTRE + r], fill=255)
    else:
        h = SQUARE_HALF - inset
        draw.rectangle([CENTRE - h, CENTRE - h, CENTRE + h, CENTRE + h], fill=255)
    if slot and ft["slot"]:
        # widen the slot too, so the outline band runs around it
        _draw_slot(draw, grow=inset, fill=0)
    return np.array(mask) > 0


_YY, _XX = np.mgrid[:CANVAS, :CANVAS]


# Feature functions: change img (RGBA array) in place; ft = {feature: 0/1}.
# Each does nothing when its feature is 0, except ft_circle, which then
# draws the square base shape.

def ft_circle(img, ft):
    """Base shape: circle (1) or square (0), filled gray."""
    img[_shape_mask(ft, slot=False)] = (*GRAY, 255)


def ft_colour(img, ft):
    """Orange instead of gray, over the whole shape."""
    if not ft["colour"]:
        return
    shape = img[..., 3] > 0                 # non-transparent pixels
    img[shape, :3] = ORANGE


def ft_stripes(img, ft):
    """Black diagonal stripes over the whole shape."""
    if not ft["stripes"]:
        return
    shape = img[..., 3] > 0
    # x + y is constant along a diagonal
    on = ((_XX + _YY) % STRIPE_PERIOD) < STRIPE_WIDTH
    img[shape & on] = (*BLACK, 255)


def ft_outline(img, ft):
    """Thick black band along the edge, including the slot's edge.

    Shape minus the shape inset by OUTLINE_WIDTH, so equally thick everywhere.
    """
    if not ft["outline"]:
        return
    band = _shape_mask(ft) & ~_shape_mask(ft, inset=OUTLINE_WIDTH)
    img[band] = (*BLACK, 255)


def ft_slot(img, ft):
    """Cut the slot out (made transparent)."""
    if not ft["slot"]:
        return
    mask = Image.new("L", (CANVAS, CANVAS), 0)
    _draw_slot(ImageDraw.Draw(mask), grow=0, fill=255)
    img[np.array(mask) > 0] = 0


def ft_hole(img, ft):
    """Cut a round hole in the centre (made transparent)."""
    if not ft["hole"]:
        return
    inside = (_XX - CENTRE) ** 2 + (_YY - CENTRE) ** 2 <= HOLE_RADIUS ** 2
    img[inside] = 0


# Dict order is drawing order: later features go on top, and slot and hole
# cut last. Separate from IMAGE_NAME_ORDER (digit order in file names).
FT_FUNCTIONS = {
    "circle": ft_circle,
    "colour": ft_colour,
    "stripes": ft_stripes,
    "outline": ft_outline,
    "slot": ft_slot,
    "hole": ft_hole,
}


def draw_obj(ft_row):
    """PIL image for one 0/1 row in IMAGE_NAME_ORDER, e.g. [1, 0, 0, 0, 0, 1]."""
    ft = dict(zip(IMAGE_NAME_ORDER, ft_row))
    img = np.zeros((CANVAS, CANVAS, 4), np.uint8)       # transparent
    for feature, ft_function in FT_FUNCTIONS.items():
        ft_function(img, ft)
    return Image.fromarray(img)


def draw_c_obj():
    """Draw all 64 feature combinations and save them to PATHS["stimDir"]."""
    if sorted(FT_FUNCTIONS) != sorted(IMAGE_NAME_ORDER):
        raise ValueError(f"FT_FUNCTIONS has {sorted(FT_FUNCTIONS)} but "
                         f"IMAGE_NAME_ORDER has {sorted(IMAGE_NAME_ORDER)}; "
                         "they must name the same features")

    out_dir = PATHS["stimDir"]
    out_dir.mkdir(parents=True, exist_ok=True)
    for ft_row in product([0, 1], repeat=len(IMAGE_NAME_ORDER)):
        name = "".join(str(v) for v in ft_row) + ".png"
        draw_obj(ft_row).save(out_dir / name)
    print(f"saved {2 ** len(IMAGE_NAME_ORDER)} images to {out_dir}")


if __name__ == "__main__":
    draw_c_obj()
