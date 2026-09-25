"""Counterbalancing: which image each object shows.

An object's image follows from its row in config.CONTEXT and the coding in
config.ATTRIBUTES. For example, with m1 = size (1 = big), m2 = colour
(1 = black) and m3 = shape (1 = tri), the row [1, 1, 0] gives
big_black_square.png.
"""

from config import ATTRIBUTES, CONTEXT, GEOMETRY, IMAGE_NAME_ORDER, NAMES, PATHS


def object_image(obj):
    """Image file name for one object, e.g. "big_black_square.png"."""
    levels = {}
    for spec, value in zip(ATTRIBUTES.values(), CONTEXT[obj]):
        levels[spec["feature"]] = spec[value]
    return "_".join(levels[feature] for feature in IMAGE_NAME_ORDER) + ".png"


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

    images = {obj: object_image(obj) for obj in CONTEXT}

    # With features standing for attributes, equal rows mean equal images,
    # and two objects that look the same cannot be told apart.
    seen = {}
    for obj, image in images.items():
        if image in seen:
            raise ValueError(f"{seen[image]} and {obj} have the same row in "
                             f"CONTEXT, so both would show {image}")
        seen[image] = obj

    missing = [image for image in images.values()
               if not (PATHS["stimDir"] / image).exists()]
    if missing:
        raise FileNotFoundError(f"Not in {PATHS['stimDir']}: {missing}")
