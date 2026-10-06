"""Experiment side: counterbalancing, i.e. which image each object shows.

An object's image follows from its row in context.CONTEXT (attributes) and
config.ATTRIBUTES (which feature stands for each attribute). The row is
reordered into the fixed feature order of config.IMAGE_NAME_ORDER, which
is the file name of the image stimuli.py drew.
"""

import random
import sys

from config import (ATTRIBUTES, EULER_TOUR, GEOMETRY, IMAGE_NAME_ORDER, NAMES,
                    ORDER, PATHS, PROJECT_DIR)
from context import CONTEXT

# eulerTours/ sits at the project root, outside demo/
sys.path.insert(0, str(PROJECT_DIR))
from eulerTours import euler


def object_image(obj):
    """Image file name for one object, e.g. "110000.png".

    Example: CONTEXT["g0"] = [1, 1, 1, 0, 0, 0] (has m0, m1, m2). If
    m0 = fill, m1 = disk, m2 = stripes, then g0 shows fill + disk + stripes.
    In IMAGE_NAME_ORDER (fill, disk, stripes, dots, outline, notch) that is
    111000.png. With another mapping, the same row gives another file.
    """
    # attribute row -> {feature: 0/1}
    ft = {}
    for attr, value in zip(ATTRIBUTES, CONTEXT[obj]):
        ft[ATTRIBUTES[attr]["feature"]] = value
    # {feature: 0/1} -> digits in the fixed feature order
    return "".join(str(ft[feature]) for feature in IMAGE_NAME_ORDER) + ".png"


def trial_sequence(seed):
    """Target object of every trial, e.g. ["g3", "g0", "g5", ...].

    An Euler tour on the graph with one edge per ordered pair i -> j, so
    every transition between consecutive trials appears exactly
    tour_repeats times. euler.py labels objects "0".."7"; label "3" is the
    4th object in CONTEXT, i.e. "g3".

    The same seed always gives the same sequence, so a session's sequence
    can be rebuilt from the seed saved in its data file.
    """
    # euler.py draws from Python's shared random generator, which the
    # experiment also uses (preview jitter, ring rotation). Seed it only for
    # this call, then put its state back, so the seed does not also fix
    # those other random values.
    saved_state = random.getstate()
    random.seed(seed)
    try:
        tour = euler.Euler(stimuli=len(CONTEXT),
                           stim_repeat=EULER_TOUR["stay_trial"],
                           seq_repeats=EULER_TOUR["tour_repeats"])
        labels = tour.get_sequence()
    finally:
        random.setstate(saved_state)

    objects = list(CONTEXT)
    return [objects[int(label)] for label in labels]


def image_code(obj):
    """An object's attribute row as text, e.g. "1 1 0".

    Spaces keep a leading 0 when the data file is read back.
    """
    return " ".join(str(value) for value in CONTEXT[obj])


def attributes_text():
    """The coding in one cell: "m1:size[1=big/0=small];m2:...".

    No commas, so the cell stays readable in a plain text editor.
    """
    return ";".join(f"{attr}:{spec['feature']}[1={spec[1]}/0={spec[0]}]"
                    for attr, spec in ATTRIBUTES.items())


def check_design():
    """Stop before anything opens if the counterbalancing values do not fit.

    Each check names what is wrong, so the fix is clear from the message.
    """
    expected = [f"m{j}" for j in range(len(ATTRIBUTES))]
    if list(ATTRIBUTES) != expected:
        raise ValueError(f"ATTRIBUTES keys must be {expected} in this order, "
                         "to match the columns of CONTEXT; they are "
                         f"{list(ATTRIBUTES)}")

    features = [spec["feature"] for spec in ATTRIBUTES.values()]
    if sorted(features) != sorted(IMAGE_NAME_ORDER):
        raise ValueError(f"ATTRIBUTES must use each of {IMAGE_NAME_ORDER} "
                         f"exactly once; it uses {features}")

    if list(CONTEXT) != list(NAMES):
        raise ValueError("CONTEXT and NAMES must list the same objects "
                         "in the same order")
    if len(CONTEXT) != GEOMETRY["objCount"]:
        raise ValueError(f"CONTEXT has {len(CONTEXT)} objects but "
                         f"GEOMETRY['objCount'] is {GEOMETRY['objCount']}")

    for obj, row in CONTEXT.items():
        if len(row) != len(ATTRIBUTES) or any(v not in (0, 1) for v in row):
            raise ValueError(f"CONTEXT[{obj!r}] = {row}: it needs "
                             f"{len(ATTRIBUTES)} values, each 0 or 1")

    ring = ORDER["ringOrder"]
    if sorted(ring) != sorted(CONTEXT):
        raise ValueError(f"ORDER['ringOrder'] = {ring}: it must hold each of "
                         f"{list(CONTEXT)} exactly once")

    if not isinstance(EULER_TOUR["stay_trial"], bool):
        raise ValueError("EULER_TOUR['stay_trial'] must be True or False; "
                         f"it is {EULER_TOUR['stay_trial']!r}")
    repeats = EULER_TOUR["tour_repeats"]
    if not isinstance(repeats, int) or repeats < 1:
        raise ValueError("EULER_TOUR['tour_repeats'] must be a whole number "
                         f"of 1 or more; it is {repeats!r}")

    images = {obj: object_image(obj) for obj in CONTEXT}

    # With features standing for attributes, equal rows mean equal images.
    # A formal context may have equal rows, so this only warns; but the
    # participant cannot tell such objects apart by how they look.
    seen = {}
    for obj, image in images.items():
        if image in seen:
            print(f"WARNING: {seen[image]} and {obj} have the same row in "
                  f"CONTEXT, so both will show {image}")
        seen.setdefault(image, obj)

    missing = [image for image in images.values()
               if not (PATHS["stimDir"] / image).exists()]
    if missing:
        raise FileNotFoundError(f"Not in {PATHS['stimDir']}: {missing}")
