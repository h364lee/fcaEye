"""Counterbalancing, stimulus sets, trial orders, and design checks.

An object's image file name is its CONTEXT row, mapped to features by
ATTRIBUTES and written in IMAGE_NAME_ORDER (see stimuli.py).
"""

import random
import sys
from dataclasses import dataclass

from config import (ATTRIBUTES, COUNTERBALANCE, DEMO_TRIALS, EULER_TOUR,
                    GEOMETRY, GROUP_CELLS, IMAGE_NAME_ORDER, NAMES, NAMES_B,
                    OBJECT_SETS, ORDER, PHASES, PRACTICE_NAMES,
                    PRACTICE_OBJECTS,
                    PROJECT_DIR)
from config import CONTEXT, CONTEXTS

# eulerTours/ sits at the project root, outside demo/
sys.path.insert(0, str(PROJECT_DIR))
from eulerTours import euler


def object_image(obj, context=CONTEXT, object_set=1):
    """Image file name for one object, e.g. "111000.png".

    The same row gives a different file under a different ATTRIBUTES mapping.
    """
    attributes = OBJECT_SETS[object_set]["attributes"]
    name_order = OBJECT_SETS[object_set]["imageNameOrder"]
    ft = {}
    for attr, value in zip(attributes, context[obj]):
        ft[attributes[attr]["feature"]] = value
    return "".join(str(ft[feature]) for feature in name_order) + ".png"


@dataclass
class StimulusSet:
    """Names, context and images for the practice or one phase.

    All sets use labels g0-g7, so trial files keep the same columns.

    label:      "practice", "phase1" or "phase2"
    context:    {object: attribute row}; None for the practice
    images:     {object: image file name}; None for the practice
    ring_order: objects in ring-slot order
    context_label, object_set: the GROUP_CELLS entry used (empty for practice)
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
    """{label: StimulusSet} for the practice and both phases.

    Phases use the GROUP_CELLS row chosen by COUNTERBALANCE["groupCell"].
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
    """Seed for one block; saved so the block's order can be rebuilt."""
    return random.randint(1, 9999)


def shuffled_sequence(seed, objects, n_trials):
    """n_trials targets in random order, each object as equally often as possible.

    Uses its own random generator, so the seed does not fix other random
    values (preview jitter, rotation).
    """
    repeats = -(-n_trials // len(objects))          # rounded up
    sequence = list(objects) * repeats
    random.Random(seed).shuffle(sequence)
    return sequence[:n_trials]


def trial_sequence(seed, objects=None):
    """Test-block targets from an Euler tour, e.g. ["g3", "g0", "g5", ...].

    Each transition i -> j appears exactly tour_repeats times. The same
    seed always gives the same sequence.
    """
    if objects is None:
        objects = list(CONTEXT)

    # euler.py uses the shared random generator. Restore its state after,
    # so this seed does not fix preview jitter or ring rotation.
    saved_state = random.getstate()
    random.seed(seed)
    try:
        tour = euler.Euler(stimuli=len(objects),
                           stim_repeat=EULER_TOUR["stay_trial"],
                           seq_repeats=EULER_TOUR["tour_repeats"])
        labels = tour.get_sequence()
    finally:
        random.setstate(saved_state)

    # euler.py labels are "0", "1", ...: positions in objects
    return [objects[int(label)] for label in labels]


def attributes_text(attributes=ATTRIBUTES):
    """Attribute coding as one cell, e.g. "m0:colour[1=orange/0=gray];...".

    No commas, so the cell stays readable in a plain text editor.
    """
    return ";".join(f"{attr}:{spec['feature']}[1={spec[1]}/0={spec[0]}]"
                    for attr, spec in attributes.items())


def check_design():
    """Raise an error before anything opens if the config values do not fit."""
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
    for n, cell in GROUP_CELLS.items():
        contexts = [context for context, _ in cell]
        sets = [object_set for _, object_set in cell]
        if any(c not in CONTEXTS for c in contexts):
            raise ValueError(f"GROUP_CELLS[{n}] = {cell}: contexts must be "
                             f"from {list(CONTEXTS)}")
        if sorted(sets) != sorted(OBJECT_SETS):
            raise ValueError(f"GROUP_CELLS[{n}] = {cell}: each of "
                             f"{list(OBJECT_SETS)} must appear once")
    # Each combination (2 x 2 x 2) must appear once
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

    # Equal rows give equal images. A formal context allows this, so only
    # warn; but participants cannot tell such objects apart.
    seen = {}
    for obj, image in images.items():
        if image in seen:
            print(f"WARNING: {seen[image]} and {obj} have the same row in "
                  f"CONTEXT, so both will show {image}")
        seen.setdefault(image, obj)

    # Both phases are checked, although phase 2 is not run for now
    for half in (stimulus_sets()["phase1"], stimulus_sets()["phase2"]):
        missing = [image for image in half.images.values()
                   if not (half.stim_dir / image).exists()]
        if missing:
            raise FileNotFoundError(f"{half.label}: not in "
                                    f"{half.stim_dir}: {missing}")
