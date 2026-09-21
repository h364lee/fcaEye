"""Trial sequence for the gaze-dwell demo."""

import random

from psychopy import core

import eventlog
import geometry
import response
from config import GEOMETRY, NAMES, PHASES, TIMING
from presentation import Presentation, check_quit


def run_trial(pres, target, phase_config, trial_n):
    """Run one trial and return what happened.

    1. dot alone until central fixation is held
    2. objects appear; jittered wait
    3. dot becomes the name; poll until selection or timeout
    4. feedback
    5. blank interval

    Objects appear before the cue so that cue-to-gaze time does not
    include searching for them.

    Each event is marked in the tracker's data file straight after the
    flip that shows it, so the marker lands as close as possible to the
    moment the screen changed.
    """
    def mark(event, **fields):
        eventlog.mark(event, trial=trial_n, **fields)

    if GEOMETRY['random_rotation']:
        rotation = random.uniform(0, 360 / GEOMETRY['n_positions'])
    else:
        rotation = 0.0
    positions = geometry.ring_positions(rotation)

    # --- 1. central fixation ---------------------------------------------
    pres.draw_fixation()
    pres.flip()
    mark("dot_on", target=target, cue=NAMES[target],
         rotation_deg=f"{rotation:.2f}")
    response.wait_for_central_fixation(pres)
    mark("fixation_held")

    # --- 2. preview -------------------------------------------------------
    # Jittered so cue onset cannot be anticipated.
    pres.draw_array(positions)
    pres.draw_fixation()
    pres.flip()
    mark("objects_on")
    core.wait(random.uniform(*TIMING['preview_range']))

    # --- 3. cue and response ---------------------------------------------
    responder = response.make_responder(
        phase_config['responder'], pres.win, positions, pres.ring_order
    )

    pres.draw_array(positions)
    pres.draw_cue(target)
    pres.flip()
    mark("cue_on")
    responder.start()

    # Redraw every frame: flipping advances the frame, and the responder
    # is polled once per frame.
    clock = core.Clock()
    while clock.getTime() < phase_config['timeout'] and responder.result() is None:
        check_quit()
        responder.poll()
        pres.draw_array(positions)
        pres.draw_cue(target)
        pres.flip()

    outcome = responder.result()
    if outcome is None:
        mark("timeout")
    else:
        mark("selection", object=outcome['selection'],
             correct=outcome['selection'] == target)

    # --- 4. feedback ------------------------------------------------------
    if phase_config['feedback']:
        correct_pos = positions[pres.ring_order.index(target)]

        selected_pos = None
        if outcome is not None:
            selected_pos = positions[pres.ring_order.index(outcome['selection'])]

        pres.draw_array(positions)
        pres.draw_feedback(correct_pos, selected_pos)
        pres.flip()
        mark("feedback_on")
        core.wait(TIMING['feedback_dur'])

    # --- 5. blank interval ------------------------------------------------
    pres.flip()
    mark("blank_on")
    core.wait(TIMING['iti'])

    return {
        "target": target,
        "cue": NAMES[target],
        "selection": None if outcome is None else outcome["selection"],
        "correct": outcome is not None and outcome["selection"] == target,
        "selection_ms": None if outcome is None else outcome["selection_ms"],
        "rotation_deg": rotation,
    }


def main():
    """Run one trial per object, without the tracker's lifecycle.

    Use demo_calibrated.py for gaze trials; this one does not open LiveTrack.
    """
    geometry.check_tolerance()      # fail before any window opens

    pres = Presentation()

    pres.show_message(
        "Look at the central dot until a name appears in its place.\n\n"
        "Then look at the object that name belongs to, and keep looking "
        "at it until the screen changes.\n\n"
        "Press space to start."
    )

    results = []
    for trial_n, target in enumerate(pres.ring_order, start=1):
        results.append(run_trial(pres, target, PHASES['demo'], trial_n))

    pres.close()

    for r in results:
        print(r)


if __name__ == "__main__":
    main()
