# AI usage: code co-written with Claude Opus 5.5.
# Research questions, experimental design and program requirements came from Caleb and Britt.

"""Ring layout, selection circles, and layout checks.

Positions are in pixels, origin at the screen centre, y up (PsychoPy).
"""

import math
import random

from config import CALIBRATION, DISPLAY, GEOMETRY


def px_per_deg():
    """Screen pixels per degree of visual angle."""
    px_per_mm = DISPLAY['size'][0] / CALIBRATION['screenSize_mm'][0]
    mm_per_deg = math.tan(math.radians(1)) * CALIBRATION['viewDist_mm']
    return mm_per_deg * px_per_mm


def ring_rotation():
    """Ring rotation in degrees for one trial, from GEOMETRY['ringRotation'].

    0 = first slot at 3 o'clock; positive is counter-clockwise. "random"
    draws from 0 to one slot angle; larger values only repeat layouts.
    """
    value = GEOMETRY['ringRotation']
    if value == "random":
        return random.uniform(0, 360 / GEOMETRY['objCount'])
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    raise ValueError(f"GEOMETRY['ringRotation'] must be a number of degrees "
                     f"or \"random\"; it is {value!r}")


def ring_positions(rotation_deg):
    """(x, y) of each ring slot, in slot order, rotated by rotation_deg."""
    n = GEOMETRY['objCount']
    r = GEOMETRY['ringRadius']

    obj_position = []
    for i in range(n):
        angle = math.radians(i * 360 / n + rotation_deg)
        obj_position.append((r*math.cos(angle), r*math.sin(angle)))
    return obj_position

        

def name_select_radius_px(name_sizes):
    """Radius in px of the selection circle, the same for every name.

    name_sizes: (width, height) in px of each drawn name.
    Half the largest name diagonal, so the circle covers the whole name,
    plus a margin for tracker error.
    """
    half_diagonal = max(math.hypot(w / 2, h / 2) for w, h in name_sizes)
    return half_diagonal + GEOMETRY['nameSelectMargin_deg'] * px_per_deg()


def object_at(point, positions, ring_order, radius_px):
    """Object (e.g. "g1") whose selection circle holds point, or None.

    positions: from ring_positions(); ring_order: objects in slot order.
    """
    for name, pos in zip(ring_order, positions):
        if math.dist(pos, point) < radius_px:
            return name
    return None



def pair_circle_radius():
    """Radius of the green feedback circle around a name and its object.

    Centred halfway between them: half their distance plus half the object
    size. The name is smaller than the object, so it fits too.
    """
    return GEOMETRY['feedbackNameOffset_px'] / 2 + GEOMETRY['objSize_px'] / 2


def _pair_circle_fits(name_pos, obj_pos):
    """True if the green circle around this name and object is on screen."""
    cx = (name_pos[0] + obj_pos[0]) / 2
    cy = (name_pos[1] + obj_pos[1]) / 2
    r = pair_circle_radius()
    half_w, half_h = DISPLAY['size'][0] / 2, DISPLAY['size'][1] / 2
    return abs(cx) + r <= half_w and abs(cy) + r <= half_h


def feedback_obj_pos(name_pos):
    """Feedback object position: below the name, or above if the circle
    would leave the screen (currently only the bottom slot).

    Straight below, not toward the centre: names are wide, so a sideways
    offset would put the object over the name.
    """
    x, y = name_pos
    d = GEOMETRY['feedbackNameOffset_px']
    below = (x, y - d)
    if _pair_circle_fits(name_pos, below):
        return below
    return (x, y + d)


def check_feedback_fit():
    """Raise an error if the feedback circle can leave the screen.

    Tests every whole degree, since "random" rotation allows any angle.
    """
    r_ring = GEOMETRY['ringRadius']
    for deg in range(360):
        a = math.radians(deg)
        name_pos = (r_ring * math.cos(a), r_ring * math.sin(a))
        if not _pair_circle_fits(name_pos, feedback_obj_pos(name_pos)):
            raise ValueError(
                f"At {deg} deg on the ring the feedback circle (radius "
                f"{pair_circle_radius():.0f} px) leaves the "
                f"{DISPLAY['size'][0]}x{DISPLAY['size'][1]} screen. Lower "
                "GEOMETRY['ringRadius'], or reduce objSize_px or "
                "feedbackNameOffset_px.")


def adjacent_gap():
    """Distance in px between two adjacent ring slots."""
    pos = ring_positions(0)
    return math.dist(pos[0], pos[1])


def check_tolerance(radius_px):
    """Raise an error if selection circles of adjacent names overlap."""
    adj_gap = adjacent_gap()

    if adj_gap < 2 * radius_px:
        raise ValueError(
            f"Selection circles overlap: radius {radius_px:.0f} px, but "
            f"adjacent names are only {adj_gap:.0f} px apart. Lower "
            "GEOMETRY['nameSelectMargin_deg'] or 'height_name_px', or "
            "raise 'ringRadius'.")
