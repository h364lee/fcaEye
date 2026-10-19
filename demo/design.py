"""Experiment side: counterbalancing, i.e. which image each object shows.

An object's image follows from its row in config.CONTEXT (attributes) and
config.ATTRIBUTES (which feature stands for each attribute). The row is
reordered into the fixed feature order of config.IMAGE_NAME_ORDER, which
is the file name of the image stimuli.py drew.
"""

import random
import sys
from dataclasses import dataclass

from config import (ATTRIBUTES, COUNTERBALANCE, DEMO_TRIALS, EULER_TOUR,
                    GEOMETRY, GROUP_CELLS, IMAGE_NAME_ORDER, NAMES, NAMES_B,
                    OBJECT_SETS, ORDER, PATHS, PHASES, PRACTICE_NAMES,
                    PRACTICE_OBJECTS,
                    PROJECT_DIR)
from config import CONTEXT, CONTEXTS

# eulerTours/ sits at the project root, outside demo/
sys.path.insert(0, str(PROJECT_DIR))
from eulerTours import euler


def object_image(obj, context=CONTEXT, object_set=1):
    """Image file name for one object, e.g. "110000.png".

    Example: CONTEXT["g0"] = [1, 1, 1, 0, 0, 0] (has m0, m1, m2). If
    m0 = fill, m1 = disk, m2 = stripes, then g0 shows fill + disk + stripes.
    In IMAGE_NAME_ORDER (fill, disk, stripes, dots, outline, notch) that is
    111000.png. With another mapping, the same row gives another file.
    """
    attributes = OBJECT_SETS[object_set]["attributes"]
    name_order = OBJECT_SETS[object_set]["imageNameOrder"]
    # attribute row -> {feature: 0/1}
    ft = {}
    for attr, value in zip(attributes, context[obj]):
        ft[attributes[attr]["feature"]] = value
    # {feature: 0/1} -> digits in the fixed feature order
    return "".join(str(ft[feature]) for feature in name_order) + ".png"


@dataclass
class StimulusSet:
    """Everything that differs between the practice and the two halves.

    All sets use the object labels g0-g7, so the trial file keeps the same
    columns; the "stimSet" column says which set a trial used.

    label:        "practice", "phase1" or "phase2"
    names:        {object: name}
    context:      {object: attribute row}, or None for the practice
    images:       {object: image file name}, or None for the practice
                  (Presentation draws white circles instead)
    ring_order:   objects in ring-slot order
    stim_dir:     folder of the images (None for the practice)
    context_label, object_set: the design-table cells this set was built
                  from (empty for the practice)
    """
    label: str
    names: dict
    context: dict | None
    images: dict | None
    ring_order: list
    stim_dir: object = None
    context_label: str = ""
    object_set: int | None = None

    @property
    def objects(self):
        return list(self.names)

    def image_code(self, obj):
        """Attribute row as text, e.g. "1 1 0 ...", or "" for the practice."""
        if self.context is None:
            return ""
        return " ".join(str(v) for v in self.context[obj])


def phase2_relation():
    """ "isom" if both phases use the same context, otherwise "shift"."""
    (context1, _), (context2, _) = GROUP_CELLS[COUNTERBALANCE["groupCell"]]
    return "isom" if context1 == context2 else "shift"


def stimulus_sets():
    """The practice set and one set per phase, by label.

    Each phase takes its context and object set (with its names) from the
    row of config.GROUP_CELLS chosen by COUNTERBALANCE["groupCell"].
    """
    sets = {"practice": StimulusSet("practice", PRACTICE_NAMES, None, None,
                                    list(PRACTICE_NAMES))}
    cell = GROUP_CELLS[COUNTERBALANCE["groupCell"]]
    for phase, (context_label, object_set) in enumerate(cell, start=1):
        context = CONTEXTS[context_label]
        sets[f"phase{phase}"] = StimulusSet(
            label=f"phase{phase}",
            names=OBJECT_SETS[object_set]["names"],
            context=context,
            images={obj: object_image(obj, context, object_set)
                    for obj in context},
            ring_order=list(ORDER["ringOrder"]),
            stim_dir=OBJECT_SETS[object_set]["stimDir"],
            context_label=context_label,
            object_set=object_set,
        )
    return sets


def new_seed():
    """A seed for one block. Saved in the trial file, so the block's order
    can be rebuilt."""
    return random.randint(1, 9999)


def shuffled_sequence(seed, objects, n_trials):
    """n_trials targets in random order; each object equally often when
    n_trials is a multiple of the object count (learning blocks), otherwise
    as close to that as possible (a 1-trial practice round: one random
    object).

    A separate random generator, so the seed does not affect other random
    values (preview jitter, rotation).
    """
    repeats = -(-n_trials // len(objects))          # n / count, rounded up
    sequence = list(objects) * repeats
    random.Random(seed).shuffle(sequence)
    return sequence[:n_trials]


def trial_sequence(seed, objects=None):
    """Target object of every trial, e.g. ["g3", "g0", "g5", ...].

    An Euler tour on the graph with one edge per ordered pair i -> j, so
    every transition between consecutive trials appears exactly
    tour_repeats times. euler.py labels objects "0".."7"; label "3" is the
    4th object in CONTEXT, i.e. "g3".

    The same seed always gives the same sequence, so a session's sequence
    can be rebuilt from the seed saved in its data file.
    """
    if objects is None:
        objects = list(CONTEXT)

    # euler.py draws from Python's shared random generator, which the
    # experiment also uses (preview jitter, ring rotation). Seed it only for
    # this call, then put its state back, so the seed does not also fix
    # those other random values.
    saved_state = random.getstate()
    random.seed(seed)
    try:
        tour = euler.Euler(stimuli=len(objects),
                           stim_repeat=EULER_TOUR["stay_trial"],
                           seq_repeats=EULER_TOUR["tour_repeats"])
        labels = tour.get_sequence()
    finally:
        random.setstate(saved_state)

    return [objects[int(label)] for label in labels]


def image_code(obj):
    """An object's attribute row as text, e.g. "1 1 0".

    Spaces keep a leading 0 when the data file is read back.
    """
    return " ".join(str(value) for value in CONTEXT[obj])


def attributes_text(attributes=ATTRIBUTES):
    """The coding in one cell: "m1:size[1=big/0=small];m2:...".

    No commas, so the cell stays readable in a plain text editor.
    """
    return ";".join(f"{attr}:{spec['feature']}[1={spec[1]}/0={spec[0]}]"
                    for attr, spec in attributes.items())


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

    n_objects = len(CONTEXT)
    if PHASES["learnBlockTrials"] % n_objects != 0:
        raise ValueError(f"PHASES['learnBlockTrials'] = "
                         f"{PHASES['learnBlockTrials']} must be a multiple of "
                         f"{n_objects}, so each object appears equally often")
    if not isinstance(PHASES["practiceTrials"], int) or PHASES["practiceTrials"] < 1:
        raise ValueError("PHASES['practiceTrials'] must be a whole number "
                         f"of 1 or more; it is {PHASES['practiceTrials']!r}")
    if not 0 < PHASES["learnCriterion"] <= 1:
        raise ValueError("PHASES['learnCriterion'] is a proportion, "
                         "between 0 and 1")
    if PHASES["learnCriterionBlocks"] > PHASES["learnMaxBlocks"]:
        raise ValueError("PHASES['learnCriterionBlocks'] is larger than "
                         "PHASES['learnMaxBlocks']: the criterion could never "
                         "be met")
    for stage, limit in DEMO_TRIALS.items():
        if limit is not None and (not isinstance(limit, int) or limit < 1):
            raise ValueError(f"DEMO_TRIALS[{stage!r}] must be None or a "
                             f"whole number of 1 or more; it is {limit!r}")
    if list(PRACTICE_OBJECTS) != list(PRACTICE_NAMES):
        raise ValueError("PRACTICE_OBJECTS must list the same objects as "
                         "PRACTICE_NAMES, in the same order")
    allowed = ({"white", "black"}, {"square", "triangle"}, {"big", "small"})
    for obj, features in PRACTICE_OBJECTS.items():
        if len(features) != 3 or any(f not in a for f, a in zip(features, allowed)):
            raise ValueError(f"PRACTICE_OBJECTS[{obj!r}] = {features}: use "
                             "(white/black, square/triangle, big/small)")
    if len(set(PRACTICE_OBJECTS.values())) != len(PRACTICE_OBJECTS):
        raise ValueError("PRACTICE_OBJECTS: two objects look the same")
    if COUNTERBALANCE["groupCell"] not in GROUP_CELLS:
        raise ValueError(f"COUNTERBALANCE['groupCell'] must be one of "
                         f"{list(GROUP_CELLS)}; it is "
                         f"{COUNTERBALANCE['groupCell']!r}")
    # Every cell: known contexts, and both object sets, one per phase
    for n, cell in GROUP_CELLS.items():
        contexts = [context for context, _ in cell]
        sets = [object_set for _, object_set in cell]
        if any(c not in CONTEXTS for c in contexts):
            raise ValueError(f"GROUP_CELLS[{n}] = {cell}: contexts must be "
                             f"from {list(CONTEXTS)}")
        if sorted(sets) != sorted(OBJECT_SETS):
            raise ValueError(f"GROUP_CELLS[{n}] = {cell}: each of "
                             f"{list(OBJECT_SETS)} must appear once")
    # The table must hold each combination once (2 x 2 x 2)
    combos = {(cell[0][0], cell[0][0] == cell[1][0], cell[0][1])
              for cell in GROUP_CELLS.values()}
    if len(combos) != len(GROUP_CELLS):
        raise ValueError("GROUP_CELLS repeats a combination of phase-1 "
                         "context, isom/shift and first object set")
    if set(NAMES.values()) & set(NAMES_B.values()):
        raise ValueError("NAMES and NAMES_B share names: "
                         f"{set(NAMES.values()) & set(NAMES_B.values())}")
    for label, names in (("NAMES_B", NAMES_B),
                         ("PRACTICE_NAMES", PRACTICE_NAMES)):
        if list(names) != list(CONTEXT):
            raise ValueError(f"{label} must use the same object labels "
                             "as CONTEXT")
    for label, context in CONTEXTS.items():
        if list(context) != list(CONTEXT):
            raise ValueError(f"context {label} must use the same object "
                             "labels as CONTEXT")

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

    # Every image either half will show
    for half in (stimulus_sets()["phase1"], stimulus_sets()["phase2"]):
        missing = [image for image in half.images.values()
                   if not (half.stim_dir / image).exists()]
        if missing:
            raise FileNotFoundError(f"{half.label}: not in "
                                    f"{half.stim_dir}: {missing}")
