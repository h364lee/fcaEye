"""Five trials of the stimulus presentation.
"""

import random

from psychopy import core

import geometry
import response
from config import GEOMETRY, NAMES, PHASES, TIMING
from presentation import Presentation, check_quit


def run_trial(pres, target, phase_config):
    """One trial.

    Flow:
        0. pick a rotation and compute this trial's positions
        1. preview: objects appear with the dot; the trial waits until gaze
           has been held on the dot, then a jittered extra wait
        2. cue: the dot becomes the name; poll the responder until it
           returns something or the timeout passes, redrawing each frame
        3. feedback, if this phase has it
        4. blank interval

    Why the preview comes before the cue:
        the array must be on screen and encoded before the cue, or the time
        from cue to response includes finding the objects.

    Why the loop redraws every frame:
        flipping is what advances the frame, and the responder needs to be
        polled once per frame. Nothing on screen changes, but the loop has
        to keep running.

    Args:
        pres: a Presentation.
        target: the object whose name is cued, e.g. "g1".
        phase_config: one entry from config.PHASES.

    Returns:
        dict describing what happened.
    """
    rotation = random.uniform(0, 360 / GEOMETRY['n_positions'])
    positions = geometry.ring_positions(rotation)

    # --- 1. central fixation ----------------------------------------------
    # The dot alone. Nothing else happens until gaze has been held on it,
    # so every trial starts from a known eye position.
    response.wait_for_central_fixation(pres)

    # --- 2. preview -------------------------------------------------------
    # The objects appear, dot still showing. The jittered wait means the
    # participant cannot anticipate cue onset -- without it they would
    # control the timing themselves by choosing when to fixate.
    pres.draw_array(positions)
    pres.draw_fixation()
    pres.flip()
    core.wait(random.uniform(*TIMING['preview_range']))

    # --- 3. cue and response ---------------------------------------------
    responder = response.make_responder(
        phase_config['responder'], pres.win, positions, pres.ring_order
    )

    pres.draw_array(positions)
    pres.draw_cue(target)
    pres.flip()
    responder.start()

    clock = core.Clock()
    while clock.getTime() < phase_config['timeout'] and responder.result() is None:
        check_quit()
        responder.poll()
        pres.draw_array(positions)
        pres.draw_cue(target)
        pres.flip()

    outcome = responder.result()

    # --- 3. feedback ------------------------------------------------------
    # positions are looked up by slot: ring_order.index(name) gives the slot.
    if phase_config['feedback']:
        correct_pos = positions[pres.ring_order.index(target)]

        selected_pos = None
        if outcome is not None:
            selected_pos = positions[pres.ring_order.index(outcome['selection'])]

        pres.draw_array(positions)
        pres.draw_feedback(correct_pos, selected_pos)
        pres.flip()
        core.wait(TIMING['feedback_dur'])

    # --- 4. blank interval ------------------------------------------------
    pres.flip()
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
    """Run the demo.

    Flow:
        1. check the tolerance before anything opens
        2. build the Presentation
        3. show instructions
        4. one trial per object
        5. close the window
        6. print the results

    Why the tolerance check comes first:
        it fails loudly on a bad configuration, before a participant is
        sitting in front of a window.
    """
    geometry.check_tolerance()

    pres = Presentation()

    pres.show_message(
        "Look at the central dot until a name appears in its place.\n\n"
        "Then look at the object that name belongs to, and keep looking "
        "at it until the screen changes.\n\n"
        "Press space to start."
    )

    results = []
    for target in pres.ring_order:
        results.append(run_trial(pres, target, PHASES['demo']))

    pres.close()

    for r in results:
        print(r)


if __name__ == "__main__":
    main()
