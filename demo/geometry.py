"""Ring layout and hit testing.
"""

import math

from config import GEOMETRY


def ring_positions(rotation_deg):
    # output: the positions (x, y) of the objects along the ring
    # rotated rotation_deg degrees
    n = GEOMETRY['n_positions']
    r = GEOMETRY['ring_radius']

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
    tolerance = GEOMETRY['target_tolerance_px']

    for name, pos in zip(ring_order, positions):
        if math.dist(pos, point) < tolerance:
            return name
    return None



def adjacent_gap():
    # Distance between two adjacent objects on the ring
    # output: distance in pixels
    pos = ring_positions(0)
    return math.dist(pos[0], pos[1])


def check_tolerance():
    # Check if the tolerance radii of two adjacent objects overlap

    adj_gap = adjacent_gap()
    tol = GEOMETRY['target_tolerance_px']

    if adj_gap < 2 * tol:
        raise ValueError("The distance between two closest objects is too small for this detection tolerance")
