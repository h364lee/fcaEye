"""Check that design.trial_sequence gives pair-balanced sequences.

Run after any change to the sequence code, context.py, or EULER_TOUR:
    python test_euler_tour.py

No window, no tracker. The Euler tour should balance every sequence by
construction, so a failure here means a bug in our code (e.g. converting
labels to objects, or joining tours), not bad luck.
"""

import random
from collections import Counter

from config import EULER_TOUR
from context import CONTEXT
from design import trial_sequence


def test_euler_tour():
    objects = list(CONTEXT)
    repeats = EULER_TOUR["tour_repeats"]
    stay = EULER_TOUR["stay_trial"]

    # Every ordered pair that should appear, and how many times.
    pairs = [(i, j) for i in objects for j in objects if stay or i != j]
    expected = {pair: repeats for pair in pairs}
    n_trials = len(pairs) * repeats + 1     # first trial has no prime

    for seed in range(1, 10000):            # every seed a session can draw
        seq = trial_sequence(seed)
        # transitions = consecutive (previous, current) pairs
        counts = Counter(zip(seq[:-1], seq[1:]))

        assert len(seq) == n_trials, \
            f"seed {seed}: {len(seq)} trials, expected {n_trials}"
        assert counts == expected, \
            f"seed {seed}: transitions are not balanced: {counts}"

    # Same seed -> same sequence, so a session can be rebuilt from its seed.
    assert trial_sequence(42) == trial_sequence(42), "seed 42 gave two sequences"

    # trial_sequence must not change the shared random generator that the
    # experiment uses for preview jitter and ring rotation.
    random.seed(0)
    before = random.random()
    random.seed(0)
    trial_sequence(42)
    assert random.random() == before, "trial_sequence changed the shared random state"

    print(f"OK: seeds 1-9999, {n_trials} trials each, every one of the "
          f"{len(pairs)} transitions appears {repeats} time(s)")


if __name__ == "__main__":
    test_euler_tour()
