"""Stimuli: draw one image for every combination of the visual features.

This file knows only features, never attributes or CONTEXT. Which feature
stands for which attribute is counterbalanced (config.ATTRIBUTES), so the
images cannot depend on the context. design.object_image() picks the
right image for each object in a session.

The 6 features are present/absent (1 = present), each from a different
guiding attribute in Wolfe & Horowitz (2017):
    colour   orange fill instead of gray          colour
    stripes  diagonal stripes                     orientation
    outline  thick dark outline                   luminance polarity
    hole     round hole in the centre             topological status
    slot     cut at the top left, straight sides  line termination
             and a rounded inner end
    circle   circle instead of square             curvature
No feature makes an object reach farther from its centre than the plain
square's corners.

File names are the feature values in config.IMAGE_NAME_ORDER. With
IMAGE_NAME_ORDER = [colour, stripes, outline, hole, slot, circle],
100001.png is an orange circle with nothing else.

Run this file directly to draw all 64 images:
    python stimuli.py
"""

import math
from itertools import product

import numpy as np
from PIL import Image, ImageDraw

from config import IMAGE_NAME_ORDER, PATHS

# Canvas and shapes, in pixels. PsychoPy scales the image down to
# GEOMETRY["objSize_px"] on screen, so a large canvas keeps edges smooth.
CANVAS = 1200
CENTRE = CANVAS / 2
SQUARE_HALF = 450                                 # centre to each side of the square
# The circle has the same AREA as the square, so the two look about the same
# size: pi * r^2 = (2 * half)^2  ->  r = half * 2 / sqrt(pi), about 508.
# It is wider than the square at the sides, but still reaches less far
# than the square's corners (about 636).
CIRCLE_RADIUS = SQUARE_HALF * 2 / math.sqrt(math.pi)

OUTLINE_WIDTH = 40
HOLE_RADIUS = 200
SLOT_HALF_WIDTH = 70
# The slot's inner end is at the same distance from the centre for both
# shapes, so the gap between slot and hole is the same (118 px).
SLOT_INNER = CIRCLE_RADIUS - 190
STRIPE_PERIOD = 150          # stripes repeat every 150 px, measured along x
STRIPE_WIDTH = 45            # dark part of each period, measured along x

GRAY = (200, 200, 200)       # the fill when "colour" is absent; lighter than
                             # the mid-gray background so the shape stands out
ORANGE = (255, 102, 0)
BLACK = (0, 0, 0)


# --- shape ------------------------------------------------------------------

def _draw_slot(draw, grow, fill):
    """Draw the slot: a cut along the line from the centre to the top left,
    with straight sides and a half-circle inner end.

    grow: widen it by this many pixels on every side (for the outline).
    Its innermost point is SLOT_INNER - grow from the centre.
    """
    # unit vector toward the top left, and one perpendicular to it
    u = (-1 / math.sqrt(2), -1 / math.sqrt(2))
    v = (-u[1], u[0])
    half_w = SLOT_HALF_WIDTH + grow
    # the half circle is centred SLOT_HALF_WIDTH beyond SLOT_INNER, so its
    # inner edge lands exactly on SLOT_INNER (minus grow)
    end = SLOT_INNER + SLOT_HALF_WIDTH
    outer = SQUARE_HALF * math.sqrt(2) + 60       # past the square's corner
    rect = [(CENTRE + u[0] * s + v[0] * t, CENTRE + u[1] * s + v[1] * t)
            for s, t in [(end, -half_w), (outer, -half_w),
                         (outer, half_w), (end, half_w)]]
    draw.polygon(rect, fill=fill)
    x, y = CENTRE + u[0] * end, CENTRE + u[1] * end
    draw.ellipse([x - half_w, y - half_w, x + half_w, y + half_w], fill=fill)


def _shape_mask(ft, inset=0, slot=True):
    """True inside the object's outline (square or circle, minus the slot).

    inset: move every edge inward by this many pixels. inset=0 is the shape
    itself; inset=OUTLINE_WIDTH is the shape minus a band along its edge.
    slot=False ignores the slot (used to draw the base shape before the cut).
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
        # moving the edges in also widens the slot, so the band runs around it
        _draw_slot(draw, grow=inset, fill=0)
    return np.array(mask) > 0


# Pixel coordinates, for the stripes and the hole
_YY, _XX = np.mgrid[:CANVAS, :CANVAS]


# --- one function per feature -----------------------------------------------
# Each takes img, an RGBA array (CANVAS x CANVAS x 4) that it changes in
# place, and ft, a dict {feature: 0/1} for this object. Each draws only its
# own feature and draws nothing if its feature is 0, except ft_circle, which
# draws the square when "circle" is 0, because the object needs a base shape.

def ft_circle(img, ft):
    """Base shape: circle (1) or square (0), filled gray."""
    img[_shape_mask(ft, slot=False)] = (*GRAY, 255)


def ft_colour(img, ft):
    """Orange instead of gray, over the whole shape."""
    if not ft["colour"]:
        return
    shape = img[..., 3] > 0                 # every pixel the shape covers
    img[shape, :3] = ORANGE


def ft_stripes(img, ft):
    """Black diagonal stripes over the whole shape."""
    if not ft["stripes"]:
        return
    shape = img[..., 3] > 0
    # x + y is constant along a diagonal, so every STRIPE_PERIOD in x + y
    # starts a new stripe
    on = ((_XX + _YY) % STRIPE_PERIOD) < STRIPE_WIDTH
    img[shape & on] = (*BLACK, 255)


def ft_outline(img, ft):
    """Thick black band along the edge, following the slot if there is one.

    It reads ft["slot"] so the band runs around the slot's edge too. The
    band is the shape minus the same shape moved inward by OUTLINE_WIDTH, so
    it is equally thick on every edge.
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


# Feature name -> its drawing function.
# The ORDER here is the drawing order, and it matters: later features are
# drawn on top of earlier ones. The base shape comes first; colour and
# stripes paint the shape; the outline goes over their edge; the slot and the
# hole cut last, so they remove everything under them. This order is
# separate from IMAGE_NAME_ORDER, which only sets the digit order in file names.
FT_FUNCTIONS = {
    "circle": ft_circle,
    "colour": ft_colour,
    "stripes": ft_stripes,
    "outline": ft_outline,
    "slot": ft_slot,
    "hole": ft_hole,
}


# --- drawing ----------------------------------------------------------------

def draw_obj(ft_row):
    """Draw one image from a row in IMAGE_NAME_ORDER, e.g. [1, 0, 0, 0, 0, 1].

    Returns the image; draw_c_obj() saves it.
    """
    ft = dict(zip(IMAGE_NAME_ORDER, ft_row))
    img = np.zeros((CANVAS, CANVAS, 4), np.uint8)       # transparent
    for feature, ft_function in FT_FUNCTIONS.items():
        ft_function(img, ft)
    return Image.fromarray(img)


def draw_c_obj():
    """Draw all 2**6 = 64 feature combinations and save them to stimDir."""
    # Stop if a feature has no drawing function, or a function no feature.
    if sorted(FT_FUNCTIONS) != sorted(IMAGE_NAME_ORDER):
        raise ValueError(f"FT_FUNCTIONS has {sorted(FT_FUNCTIONS)} but "
                         f"IMAGE_NAME_ORDER has {sorted(IMAGE_NAME_ORDER)}; "
                         "they must name the same features")

    out_dir = PATHS["stimDir"]
    out_dir.mkdir(parents=True, exist_ok=True)
    # product gives every 0/1 row: (0,0,0,0,0,0), (0,0,0,0,0,1), ...
    for ft_row in product([0, 1], repeat=len(IMAGE_NAME_ORDER)):
        name = "".join(str(v) for v in ft_row) + ".png"
        draw_obj(ft_row).save(out_dir / name)
    print(f"saved {2 ** len(IMAGE_NAME_ORDER)} images to {out_dir}")


if __name__ == "__main__":
    draw_c_obj()
