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


def feedback_obj_pos(name_pos):
    """Where the object goes in feedback: feedbackNameOffset_px from the
    name, inward along the line to the screen centre.

    Inward rather than above, so the object stays on screen for every slot.
    """
    x, y = name_pos
    r = math.hypot(x, y)
    shrink = (r - GEOMETRY['feedbackNameOffset_px']) / r
    return (x * shrink, y * shrink)


def check_feedback_fit():
    """Stop if the feedback circle can leave the screen.

    The circle's farthest point from the screen centre is its own centre
    (ring radius minus half the name-object distance) plus its radius. With
    ringRotation "random" a slot can sit at any angle, so it must fit
    within the nearer screen edge: half of the shorter screen side.
    """
    farthest = (GEOMETRY['ringRadius'] - GEOMETRY['feedbackNameOffset_px'] / 2
                + pair_circle_radius())
    edge = min(DISPLAY['size']) / 2
    if farthest > edge:
        raise ValueError(
            f"The feedback circle reaches {farthest:.0f} px from the centre, but "
            f"the screen edge is {edge:.0f} px away. Lower GEOMETRY['ringRadius'] "
            f"by at least {farthest - edge:.0f} px, or reduce objSize_px or "
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
