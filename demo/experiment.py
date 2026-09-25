"""experiment.py: session flow and trial flow.

Session: demographics -> calibration -> recording -> one trial per object.
Demographics and calibration can be switched off in config.SESSION.
"""

import random
import sys
from datetime import datetime
sys.path.insert(0, r"C:\Users\Public\Documents\CRS LiveTrack Python Bindings")
import LiveTrack

from psychopy import core

import calibrate
import design
import eventlog
import geometry
import response
import trialdata
from config import (CENTRAL_FIXATION, GENDER_OPTIONS, GEOMETRY, NAMES,
                    SESSION, TIMING)
from presentation import Presentation, QuitRequested, check_quit


def ask_demographics(pres):
    """Ask SONA ID, age and gender on the experiment screen."""
    digits = "0123456789"
    sona_id = pres.type_answer("What is your SONA ID?", digits,
                               "Question 1 of 3", "6 digits", max_len=6,
                               is_valid=lambda a: len(a) == 6)
    age = pres.type_answer("What is your age?", digits,
                           "Question 2 of 3", "In years, 1 to 99", max_len=2,
                           is_valid=lambda a: 1 <= int(a) <= 99)
    gender = pres.choose_option("What is your gender?", GENDER_OPTIONS,
                                "Question 3 of 3")

    # One gender column: a self-description replaces the option text,
    # marked so it can be told apart from the fixed options.
    if gender == "Prefer to self-describe":
        letters = "abcdefghijklmnopqrstuvwxyz"
        typed = pres.type_answer("Please describe your gender",
                                 letters + letters.upper() + " -",
                                 "Question 3 of 3",
                                 "Letters, spaces and hyphens", max_len=24)
        gender = f"self-described: {typed}"
    return {"sonaID": sona_id, "age": int(age), "gender": gender}


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
    times = {}

    def mark(event, **fields):
        # The PsychoPy time is taken at the same moment the marker is sent,
        # so the trial file and the tracker file can be checked against
        # each other.
        times[trialdata.EVENT_TIMES[event]] = core.getTime()
        eventlog.mark(event, trial=trial_n, **fields)

    if GEOMETRY['randomRotation']:
        rotation = random.uniform(0, 360 / GEOMETRY['objCount'])
    else:
        rotation = 0.0
    positions = geometry.ring_positions(rotation)

    # --- 1. central fixation ---------------------------------------------
    pres.draw_fixation()
    pres.flip()
    mark("dot_on", target=target, name=NAMES[target],
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
    preview_s = random.uniform(*TIMING['previewDurRange'])
    response.wait_for_central_fixation(pres, preview_s, positions)

    # --- 3. cue and response ---------------------------------------------
    responder = response.GazeDwellResponder(positions, pres.ring_order)

    pres.draw_array(positions)
    pres.draw_cue(target)
    pres.flip()
    mark("name_on")
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

    if outcome is None:
        result = "timeout"
    elif selection == target:
        result = "correct"
    else:
        result = "incorrect"

    # None is written as an empty cell.
    row = {
        "trialN": trial_n,
        "targetObj": target,
        "name": NAMES[target],
        "targetImage": design.image_code(target),
        "rotation_deg": rotation,
    }
    for obj in NAMES:
        x, y = positions[pres.ring_order.index(obj)]
        row[f"{obj}X"] = round(x, 1)
        row[f"{obj}Y"] = round(y, 1)
    row.update({
        "previewDur_s": preview_s,
        "selected": selection,
        "outcome": result,
        "selection_ms": None if outcome is None else outcome["selection_ms"],
        "firstMove_ms": None if outcome is None else outcome["first_move_ms"],
    })
    row.update(times)
    return row


def main():
    geometry.check_tolerance()        # fail before anything opens
    design.check_design()
    pres = Presentation()
    screen_rate = pres.win.getActualFrameRate()    # None if it was unstable

    LiveTrack.Init()
    LiveTrack.SetResultsTypeRaw()     # calibration reads pupil/glint vectors
    LiveTrack.StartTracking()
    tracker_rate = LiveTrack.GetCaptureConfig()[2]
    tracked_eyes = LiveTrack.GetTracking()          # (left, right)

    results = []
    accuracy = {}                     # stays empty if calibration is skipped
    participant = {"sonaID": "debug", "age": "", "gender": ""}
    try:
        # Inside the try, so Esc during the questions still closes the
        # window and the tracker.
        if SESSION["yesDemographics"]:
            participant = ask_demographics(pres)
        pid = participant["sonaID"]

        # From here on the cursor must not be on the stimulus screen.
        pres.park_mouse()

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

        # About 0.4 s after recording starts, the tracker resets its own
        # clock once (seen in CRS's demo files too). Waiting past that point
        # puts every marker after the reset.
        core.wait(0.5)

        session = trialdata.session_columns(
            participant, accuracy,
            datetime.now().isoformat(timespec="seconds"),
            screen_rate, tracker_rate, tracked_eyes, pres.ring_order)
        print(f"Trials to {trialdata.open_file(path, session)}")

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
            row = run_trial(pres, target, trial_n)
            trialdata.write_row(session, row)
            results.append(row)
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
        trialdata.close_file()
        eventlog.close_session()
        LiveTrack.StopTracking()
        LiveTrack.ClearDataBuffer()
        LiveTrack.Close()
        pres.close()

    print(participant)
    for r in results:
        print(r["trialN"], r["targetObj"], r["outcome"], r["selection_ms"])


if __name__ == "__main__":
    main()
