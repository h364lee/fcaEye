"""Ring layout and hit testing.
"""

import math
import random

from config import CALIBRATION, DISPLAY, GEOMETRY


def px_per_deg():
    """Screen pixels per degree of visual angle.
    """
    px_per_mm = DISPLAY['size'][0] / CALIBRATION['screenSize_mm'][0]
    mm_per_deg = math.tan(math.radians(1)) * CALIBRATION['viewDist_mm']
    return mm_per_deg * px_per_mm


def ring_rotation():
    """Ring rotation in degrees for one trial, from GEOMETRY['ringRotation'].

    0 = first slot at 3 o'clock; positive turns the ring counter-clockwise). 
    "random" draws a new rotation each trial between 0 and the angle between two slots; 
    larger rotations would only repeat the same layouts.
    """
    value = GEOMETRY['ringRotation']
    if value == "random":
        return random.uniform(0, 360 / GEOMETRY['objCount'])
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    raise ValueError(f"GEOMETRY['ringRotation'] must be a number of degrees "
                     f"or \"random\"; it is {value!r}")


def ring_positions(rotation_deg):
    # output: the positions (x, y) of the objects along the ring
    # rotated rotation_deg degrees
    n = GEOMETRY['objCount']
    r = GEOMETRY['ringRadius']

    obj_position = []
    for i in range(n):
        angle = math.radians(i * 360 / n + rotation_deg)
        obj_position.append((r*math.cos(angle), r*math.sin(angle)))
    return obj_position

        

def object_at(point, positions, ring_order):
    # Decide which object a point is on

    # point: (x, y) on screen (centre origin)
    # positions: coordinates of the objects, ring_positions()
    # ring_order: object names (i.e., g1, g2 ...) in slot order

    # output: object's name, or None if the point is not within the target radius (tolerance) of any object
    tolerance = GEOMETRY['objSelectRadius_px']

    for name, pos in zip(ring_order, positions):
        if math.dist(pos, point) < tolerance:
            return name
    return None



def pair_circle_radius():
    """Radius of the green feedback circle around a name and its object.

    The circle is centred halfway between the name and the object, so it
    must reach half the name-object distance plus half the object image.
    The name is smaller than the object, so it fits too.
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
    """Where the object goes in feedback: feedbackNameOffset_px below the
    name, or the same distance above it if the green circle would not fit
    on screen below (with the current settings: the bottom slot only).

    Straight below rather than toward the centre: a name is much wider than
    it is tall, so a sideways offset would put the object over the name.
    """
    x, y = name_pos
    d = GEOMETRY['feedbackNameOffset_px']
    below = (x, y - d)
    if _pair_circle_fits(name_pos, below):
        return below
    return (x, y + d)


def check_feedback_fit():
    """Stop if the feedback circle can leave the screen at any ring angle.

    Tries the ring at every whole degree (with ringRotation "random" a name
    can sit at any angle) and places the object as feedback_obj_pos does.
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
    # Distance between two adjacent objects on the ring
    # output: distance in pixels
    pos = ring_positions(0)
    return math.dist(pos[0], pos[1])


def check_tolerance():
    # Check if the tolerance radii of two adjacent objects overlap

    adj_gap = adjacent_gap()
    tol = GEOMETRY['objSelectRadius_px']

    if adj_gap < 2 * tol:
        raise ValueError("The distance between two closest objects is too small for this detection tolerance")
