"""Check that design.trial_sequence balances every transition, for every seed.

Run after changing the sequence code, CONTEXT, or EULER_TOUR:
    python test_euler_tour.py
A failure means a bug, not bad luck: Euler tours balance by construction.
"""

import random
from collections import Counter

from config import EULER_TOUR
from config import CONTEXT
from design import trial_sequence


def test_euler_tour():
    objects = list(CONTEXT)
    repeats = EULER_TOUR["tour_repeats"]
    stay = EULER_TOUR["stay_trial"]

    pairs = [(i, j) for i in objects for j in objects if stay or i != j]
    expected = {pair: repeats for pair in pairs}
    n_trials = len(pairs) * repeats + 1     # first trial has no prime

    for seed in range(1, 10000):            # every seed new_seed() can give
        seq = trial_sequence(seed)
        counts = Counter(zip(seq[:-1], seq[1:]))

        assert len(seq) == n_trials, \
            f"seed {seed}: {len(seq)} trials, expected {n_trials}"
        assert counts == expected, \
            f"seed {seed}: transitions are not balanced: {counts}"

    assert trial_sequence(42) == trial_sequence(42), "seed 42 gave two sequences"

    # The shared generator (preview jitter, ring rotation) must be unchanged.
    random.seed(0)
    before = random.random()
    random.seed(0)
    trial_sequence(42)
    assert random.random() == before, "trial_sequence changed the shared random state"

    print(f"OK: seeds 1-9999, {n_trials} trials each, every one of the "
          f"{len(pairs)} transitions appears {repeats} time(s)")


if __name__ == "__main__":
    test_euler_tour()
