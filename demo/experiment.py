"""experiment.py: session flow and trial flow.

Session: demographics -> calibration -> recording -> one trial per object.
Demographics and calibration can be switched off in config.SESSION.
"""

import random
import sys
sys.path.insert(0, r"C:\Users\Public\Documents\CRS LiveTrack Python Bindings")
import LiveTrack

from psychopy import core

import calibrate
import eventlog
import geometry
import response
from config import CENTRAL_FIXATION, GENDER_OPTIONS, GEOMETRY, NAMES, SESSION, TIMING
from presentation import Presentation, QuitRequested, check_quit


def ask_demographics(pres):
    """Ask SONA ID, age and gender on the experiment screen."""
    digits = "0123456789"
    sona_id = pres.type_answer("SONA ID", digits)
    age = pres.type_answer("Age", digits)
    gender = pres.choose_option("Gender", GENDER_OPTIONS)

    self_describe = ""
    if gender == "Prefer to self-describe":
        self_describe = pres.type_answer("Please describe your gender",
                                         "abcdefghijklmnopqrstuvwxyz -")
    return {
        "sonaID": sona_id,
        "age": int(age),
        "gender": gender,
        "genderSelfDescribe": self_describe,
    }


def run_trial(pres, target, trial_n):
    """Run one trial and return what happened.

    1. dot alone until central fixation is held
    2. objects appear; gaze must stay on the dot for a jittered time
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

    if GEOMETRY['randomRotation']:
        rotation = random.uniform(0, 360 / GEOMETRY['objCount'])
    else:
        rotation = 0.0
    positions = geometry.ring_positions(rotation)

    # --- 1. central fixation ---------------------------------------------
    pres.draw_fixation()
    pres.flip()
    mark("dot_on", target=target, cue=NAMES[target],
         rotation_deg=f"{rotation:.2f}")
    response.wait_for_central_fixation(pres, CENTRAL_FIXATION['centralHold_ms'] / 1000)
    mark("fixation_held")

    # --- 2. preview -------------------------------------------------------
    # Jittered so cue onset cannot be anticipated.
    pres.draw_array(positions)
    pres.draw_fixation()
    pres.flip()
    mark("objects_on")
    # Gaze must stay on the dot, unbroken, for a random time before the
    # name appears; the random length keeps the name from being anticipated.
    response.wait_for_central_fixation(
        pres, random.uniform(*TIMING['previewDurRange']), positions)

    # --- 3. cue and response ---------------------------------------------
    responder = response.GazeDwellResponder(positions, pres.ring_order)

    pres.draw_array(positions)
    pres.draw_cue(target)
    pres.flip()
    mark("cue_on")
    responder.start()

    # Redraw every frame: flipping advances the frame, and the responder
    # is polled once per frame.
    clock = core.Clock()
    while clock.getTime() < TIMING['responseTimeout_s'] and responder.result() is None:
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
    selection = None if outcome is None else outcome['selection']
    pres.draw_feedback(target, selection, positions)
    pres.flip()
    mark("feedback_on")
    core.wait(TIMING['feedbackDur'])

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
    geometry.check_tolerance()        # fail before anything opens
    pres = Presentation()

    LiveTrack.Init()
    LiveTrack.SetResultsTypeRaw()     # calibration reads pupil/glint vectors
    LiveTrack.StartTracking()

    results = []
    accuracy = {}                     # stays empty if calibration is skipped
    participant = {"sonaID": "debug", "age": "", "gender": "",
                   "genderSelfDescribe": ""}
    try:
        # Inside the try, so Esc during the questions still closes the
        # window and the tracker.
        if SESSION["yesDemographics"]:
            participant = ask_demographics(pres)
        pid = participant["sonaID"]

        if SESSION["yesCalibration"]:
            pres.show_message("Look at each dot until it "
                              "disappears.\n\nPress space to begin.")

            accuracy = calibrate.gaze_calibration(pres.win)
            if not calibrate.report_calibration(pres, accuracy):
                # In the real experiment this is where you would recalibrate,
                # and the numbers would go to the experimenter only.
                print("Calibration did not meet criterion -- continuing anyway.")

        # From here gaze comes back as GazeX/GazeY in screen pixels centred
        # at 0,0 -- the same frame the responders use -- because the
        # calibration targets were given in those units.
        #
        # The results type is set while buffering is stopped, the order
        # CRS's own demos use.
        LiveTrack.StopTracking()
        LiveTrack.SetResultsTypeCalibrated()
        LiveTrack.ClearDataBuffer()

        # Recording starts here, after calibration, so the file holds only
        # calibrated trial data in screen pixels.
        path = eventlog.open_session(pid)
        LiveTrack.StartTracking()
        print(f"Recording to {path}")

        eventlog.mark("session_start", participant=pid,
                      ring_order="|".join(pres.ring_order))
        for eye, entry in accuracy.items():
            eventlog.mark("calibration", eye=eye,
                          accuracy_deg=f"{entry['accuracy_deg']:.3f}",
                          n_points=entry['n_points'])

        pres.show_message("Look at the central dot until a name appears.\n\n"
                          "Then look at the object that name belongs to, and "
                          "keep looking at it until the screen changes.\n\n"
                          "Press space to start. Press Esc to end the session.")
        for trial_n, target in enumerate(pres.ring_order, start=1):
            results.append(run_trial(pres, target, trial_n))
        eventlog.mark("session_end")
    except response.FixationTimeout as e:
        eventlog.mark("session_aborted", reason="fixation_timeout")
        print(f"\nABORTED: {e}")
        print("Check that the eye is in view and that gaze reads near the "
              "dot when the participant looks at it; recalibrate if not.")
    except QuitRequested:
        eventlog.mark("session_aborted", reason="escape")
        print("\nStopped by the experimenter.")
    finally:
        eventlog.close_session()
        LiveTrack.StopTracking()
        LiveTrack.ClearDataBuffer()
        LiveTrack.Close()
        pres.close()

    print(participant)
    for r in results:
        print(r)


if __name__ == "__main__":
    main()
