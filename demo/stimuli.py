"""Stimuli: draw one image for every combination of the visual features.

This file knows only features, never attributes or CONTEXT. Which feature
stands for which attribute is counterbalanced (config.ATTRIBUTES), so the
images cannot depend on the context. design.object_image() picks the
right image for each object in a session.

File names are the feature values in config.IMAGE_NAME_ORDER, 1 = present.
With IMAGE_NAME_ORDER = [fill, disk, stripes, dots, outline, notch],
110000.png shows orange fill + blue disk and nothing else.

Run this file directly to draw all 64 images:
    python stimuli.py

PLACEHOLDER: the features follow the octagon illustration. The real
features are not decided yet.
"""

import math
from itertools import product

from PIL import Image, ImageChops, ImageDraw

from config import IMAGE_NAME_ORDER, PATHS

# Canvas and base shape, in pixels. PsychoPy scales the image down to
# GEOMETRY["objSize_px"] on screen, so a large canvas keeps edges smooth.
CANVAS = 1200
CENTRE = CANVAS / 2
OCT_RADIUS = 500                # centre to corner of the octagon

ORANGE = (255, 102, 0)
GRAY = (170, 170, 170)          # the fill when "fill" is absent
BLUE = (0, 102, 221)
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)


# --- base shape -------------------------------------------------------------

def _octagon(radius):
    """Corner points of an octagon with a flat top edge."""
    # Starting at 22.5 degrees puts an edge, not a corner, at the top.
    return [(CENTRE + radius * math.cos(math.radians(22.5 + 45 * k)),
             CENTRE + radius * math.sin(math.radians(22.5 + 45 * k)))
            for k in range(8)]


# The notch is a circle centred on the top edge, right of centre.
APOTHEM = OCT_RADIUS * math.cos(math.radians(22.5))   # centre to edge
NOTCH_CENTRE = (CENTRE + 150, CENTRE - APOTHEM)
NOTCH_RADIUS = 90
OUTLINE_WIDTH = 40


def _shape_mask(inset, notch):
    """Black/white mask of the shape: white inside, black outside.

    inset: move every edge inward by this many pixels. inset=0 is the shape
    itself; inset=OUTLINE_WIDTH is the shape minus a band along its edge.
    notch: 1 = cut the notch out of the shape.
    """
    mask = Image.new("L", (CANVAS, CANVAS), 0)
    draw = ImageDraw.Draw(mask)
    # Moving the edges in by `inset` shrinks the apothem by `inset`.
    radius = (APOTHEM - inset) / math.cos(math.radians(22.5))
    draw.polygon(_octagon(radius), fill=255)
    if notch:
        # The notch grows by `inset`, so the band also runs around the notch.
        r = NOTCH_RADIUS + inset
        x, y = NOTCH_CENTRE
        draw.ellipse([x - r, y - r, x + r, y + r], fill=0)
    return mask


# --- one function per feature -----------------------------------------------
# Each takes the image and ft, a dict {feature: 0/1} for this object, and
# draws only its own feature. If its feature is 0 it draws nothing, except
# ft_fill, which paints gray, because the shape needs some fill.

def ft_fill(img, ft):
    """Orange (1) or gray (0) octagon. This is the base everything sits on."""
    colour = ORANGE if ft["fill"] else GRAY
    img.paste(colour, mask=_shape_mask(0, notch=0))


def ft_stripes(img, ft):
    """Black diagonal stripes across the shape."""
    if not ft["stripes"]:
        return
    # Draw the stripes over the whole canvas on a separate mask, then keep
    # only the part inside the octagon.
    layer = Image.new("L", (CANVAS, CANVAS), 0)
    draw = ImageDraw.Draw(layer)
    for c in range(-CANVAS, CANVAS, 110):          # 110 px between stripes
        draw.line([(c, CANVAS), (c + CANVAS, 0)], fill=255, width=30)
    inside = ImageChops.multiply(layer, _shape_mask(0, notch=0))
    img.paste(BLACK, mask=inside)


def ft_dots(img, ft):
    """White dots: a ring of 8 plus 4 inner dots."""
    if not ft["dots"]:
        return
    draw = ImageDraw.Draw(img)
    r = 35
    centres = [(330, 22.5 + 45 * k) for k in range(8)]    # (distance, angle)
    centres += [(170, 45 + 90 * k) for k in range(4)]
    for dist, angle in centres:
        x = CENTRE + dist * math.cos(math.radians(angle))
        y = CENTRE + dist * math.sin(math.radians(angle))
        draw.ellipse([x - r, y - r, x + r, y + r], fill=WHITE)


def ft_disk(img, ft):
    """Blue disk in the centre."""
    if not ft["disk"]:
        return
    draw = ImageDraw.Draw(img)
    r = 160
    draw.ellipse([CENTRE - r, CENTRE - r, CENTRE + r, CENTRE + r], fill=BLUE)


def ft_outline(img, ft):
    """Thick black band along the edge, following the notch if there is one."""
    if not ft["outline"]:
        return
    # band = shape minus the same shape moved in by OUTLINE_WIDTH
    band = ImageChops.subtract(_shape_mask(0, ft["notch"]),
                               _shape_mask(OUTLINE_WIDTH, ft["notch"]))
    img.paste(BLACK, mask=band)


def ft_notch(img, ft):
    """Cut a half-circle out of the top edge (made transparent)."""
    if not ft["notch"]:
        return
    draw = ImageDraw.Draw(img)
    x, y = NOTCH_CENTRE
    r = NOTCH_RADIUS
    # ImageDraw replaces pixels rather than blending, so this makes them
    # fully transparent.
    draw.ellipse([x - r, y - r, x + r, y + r], fill=(0, 0, 0, 0))


# Feature name -> its drawing function.
# The ORDER here is the drawing order, and it matters: later features are
# drawn on top of earlier ones. Fill is the base; the notch cuts last so it
# removes everything under it. This order is separate from IMAGE_NAME_ORDER,
# which only sets the digit order in the file names.
FT_FUNCTIONS = {
    "fill": ft_fill,
    "stripes": ft_stripes,
    "dots": ft_dots,
    "disk": ft_disk,
    "outline": ft_outline,
    "notch": ft_notch,
}


# --- drawing ----------------------------------------------------------------

def draw_obj(ft_row):
    """Draw one image from a row in IMAGE_NAME_ORDER, e.g. [1, 1, 0, 0, 0, 0].

    Returns the image; draw_c_obj() saves it.
    """
    ft = dict(zip(IMAGE_NAME_ORDER, ft_row))
    img = Image.new("RGBA", (CANVAS, CANVAS), (0, 0, 0, 0))  # transparent
    for feature, ft_function in FT_FUNCTIONS.items():
        ft_function(img, ft)
    return img


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
