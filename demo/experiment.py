"""experiment.py: session and trial flow.

demographics -> calibration -> recording -> 1 trial per object in
design.trial_sequence(seed), with a new seed each session.
"""

import csv
import random
import sys
from datetime import datetime
sys.path.insert(0, r"C:\Users\Public\Documents\CRS LiveTrack Python Bindings")
import LiveTrack

from psychopy import core, event

import calibrate
import design
import eventlog
import geometry
import response
import trialdata
from config import (CENTRAL_FIXATION, GENDER_OPTIONS, IMAGE_NAME_ORDER,
                    NAMES, PATHS, POSTTASK, SCREEN_TEXT, SESSION, TIMING)
from presentation import Presentation, QuitRequested, check_quit


def ask_demographics(pres):
    """Ask SONA ID, age and gender. Age can be skipped (saved as empty)."""
    digits = "0123456789"
    question, hint = SCREEN_TEXT["sonaId"]
    sona_id = pres.type_answer(question, digits, hint=hint, max_len=6,
                               is_valid=lambda a: len(a) == 6)
    question, hint = SCREEN_TEXT["age"]
    age = pres.type_answer(question, digits, hint=hint, max_len=2,
                           is_valid=lambda a: 1 <= int(a) <= 99, optional=True)
    gender = pres.choose_option(SCREEN_TEXT["gender"], GENDER_OPTIONS)

    if gender == "Prefer to self-describe":
        letters = "abcdefghijklmnopqrstuvwxyz"
        typed = pres.type_answer(SCREEN_TEXT["selfDescribe"],
                                 letters + letters.upper() + " -", max_len=24)
        gender = f"self-described: {typed}"
    return {"sonaID": sona_id, "age": "" if age is None else int(age),
            "gender": gender}


def posttask_q(pres, tracker_path):
    """Ask the four post-task questions and save the answers.

    Keyboard only; every question can be skipped (saved as an empty cell).
    Saved once per session, next to the tracker file:
        data/<id>_<date>_<time>_posttask.csv
    """
    # Q3 shows each feature alone: the image whose row has a 1 only for
    # that feature, e.g. "100000.png" for the first feature
    images = []
    for feature in IMAGE_NAME_ORDER:
        row = "".join("1" if f == feature else "0" for f in IMAGE_NAME_ORDER)
        images.append((PATHS["stimDir"] / f"{row}.png",
                       POSTTASK["q3Labels"][feature]))

    answers = {
        "q1Pattern": pres.type_long_answer(POSTTASK["q1"], "Question 1 of 4"),
        "q2Strategy": pres.type_long_answer(POSTTASK["q2"], "Question 2 of 4"),
    }
    chosen = pres.choose_images(POSTTASK["q3"], images, "Question 3 of 4")
    answers["q3Features"] = None if chosen is None else "|".join(chosen)
    answers["q4Difficulty"] = pres.rate_scale(POSTTASK["q4"], *POSTTASK["q4Ends"],
                                              progress="Question 4 of 4")

    path = tracker_path.with_name(tracker_path.stem + "_posttask.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(answers))
        writer.writeheader()
        writer.writerow(answers)          # None is written as an empty cell
    print(f"Post-task answers to {path}")
    return answers


def run_trial(pres, target, trial_n, previous_obj):
    """Run one trial and return what happened.

    previous_obj: the previous trial's target (the prime), None on trial 1.

    1. dot alone until central fixation is held
    2. names appear on the ring; gaze must stay on the dot for a jittered
       config.TIMING["previewDurRange"]
    3. dot becomes the object; poll until a name is selected or timeout
    4. feedback
    5. blank interval

    Names appear before the object so that cue-to-gaze time does not
    include searching for them.

    Each event is marked in the tracker's data file straight after the
    flip that shows it, so the marker lands as close as possible to the
    moment the screen changed.
    """
    times = {}

    def mark(event, **fields):
        # Each event gets three times, all taken right after its flip:
        # the PsychoPy time, the tracker time from GetLastResult, and the
        # marker in the tracker file. The first two go in the trial file.
        column = trialdata.EVENT_TIMES[event]
        times[column] = core.getTime()
        times[trialdata.tracker_column(column)] = eventlog.tracker_time_us()
        eventlog.mark(event, trial=trial_n, **fields)

    rotation = geometry.ring_rotation()
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
    pres.draw_names(positions)
    pres.draw_fixation()
    pres.flip()
    mark("names_on")
    # Gaze must stay on the dot before the object appears
    preview_s = random.uniform(*TIMING['previewDurRange'])
    response.wait_for_central_fixation(pres, preview_s, positions)

    # --- 3. cue and response ---------------------------------------------
    responder = response.GazeDwellResponder(positions, pres.ring_order,
                                            pres.name_radius_px)

    pres.draw_names(positions)
    pres.draw_object(target)
    pres.flip()
    mark("object_on")
    responder.start()

    # Redraw every frame: flipping advances the frame, and the responder
    # is polled once per frame.
    clock = core.Clock()
    while clock.getTime() < TIMING['responseTimeout_s'] and responder.result() is None:
        check_quit()
        responder.poll()
        pres.draw_names(positions)
        pres.draw_object(target)
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
        "previousObj": previous_obj,
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
    geometry.check_feedback_fit()
    geometry.ring_rotation()          # stops here if the setting is invalid
    design.check_design()

    # Trial order for this session. Built before anything opens, so a
    # problem shows up at once. The seed goes in the data file.
    seed = random.randint(1, 9999)
    sequence = design.trial_sequence(seed)
    print(f"Seed {seed}: {len(sequence)} trials")

    pres = Presentation()
    screen_rate = pres.win.getActualFrameRate()    # None if it was unstable

    LiveTrack.Init()
    LiveTrack.SetResultsTypeRaw()     # calibration reads pupil/glint vectors
    LiveTrack.StartTracking()
    tracker_rate = LiveTrack.GetCaptureConfig()[2]
    tracked_eyes = LiveTrack.GetTracking()          # (left, right)

    results = []
    accuracy = {}                     # stays empty if calibration is skipped
    calibration_attempts = 0          # stays 0 if calibration is skipped
    participant = {"sonaID": "debug", "age": "", "gender": ""}
    try:
        # Inside the try, so Esc during the questions still closes the
        # window and the tracker.
        pres.show_message(SCREEN_TEXT["greeting"])          # Screen 1
        if SESSION["yesDemographics"]:
            participant = ask_demographics(pres)            # Screen 2
        pid = participant["sonaID"]

        # From here on the cursor must not be on the stimulus screen.
        pres.park_mouse()

        if SESSION["yesCalibration"]:
            # Repeat until both eyes pass. After a failure the participant
            # sees a waiting screen (4b) and the researcher chooses in the
            # terminal: R recalibrates, Esc ends the session. No limit on
            # attempts; the count is shown in the terminal and saved.
            while True:
                calibration_attempts += 1
                pres.show_message(SCREEN_TEXT["calibration"])   # Screen 3
                accuracy = calibrate.gaze_calibration(pres.win)
                if calibrate.report_calibration(pres, accuracy,
                                                calibration_attempts):
                    print(f"PASSED on attempt {calibration_attempts}.")
                    break
                pres.message.text = SCREEN_TEXT["calibrationWait"]  # Screen 4b
                pres.message.draw()
                pres.flip()
                print(f"FAILED (attempt {calibration_attempts}). Adjust the "
                      "camera or the participant, then press R to recalibrate, "
                      "or Esc to end the session.")
                if event.waitKeys(keyList=["r", "escape"])[0] == "escape":
                    raise QuitRequested("ended after failed calibration")
            pres.show_message(SCREEN_TEXT["calibrationDone"])   # Screen 4

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
            screen_rate, tracker_rate, tracked_eyes, pres.ring_order, seed,
            calibration_attempts)
        print(f"Trials to {trialdata.open_file(path, session)}")

        # One marker for everything known at the start. Markers sent close
        # together can collapse into one (seen with the two calibration
        # markers), so these values share a single comment.
        calibration = {f"cal_{eye}_deg": f"{entry['accuracy_deg']:.3f}"
                       for eye, entry in accuracy.items()}
        eventlog.mark("session_start", participant=pid,
                      ring_order="|".join(pres.ring_order), seed=seed,
                      **calibration)

        pres.show_message(SCREEN_TEXT["task"])               # Screen 5
        previous_obj = None               # trial 1 has no prime
        for trial_n, target in enumerate(sequence, start=1):
            row = run_trial(pres, target, trial_n, previous_obj)
            trialdata.write_row(session, row)
            results.append(row)
            previous_obj = target
        eventlog.mark("trials_end")
        posttask_q(pres, path)
        eventlog.mark("session_end")
        # After session_end: the data are complete, so leaving the letter
        # early with Esc is not an abort
        pres.show_debrief()                                 # Screens 13-14
        try:
            pres.show_message(SCREEN_TEXT["endOfStudy"])    # Screen 15
        except QuitRequested:
            pass                    # data are saved; Esc just closes
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
