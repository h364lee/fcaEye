"""Session and trial flow.

Session: greeting, demographics -> instructions -> calibration ->
recording starts -> practice rounds -> learning 1 (until criterion) ->
test 1 -> post-task questions -> thank you, debrief letter.
Esc opens the pause screen (presentation.pause_menu).
"""

import csv
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
from config import (CENTRAL_FIXATION, COUNTERBALANCE, DEMO_TRIALS,
                    GENDER_OPTIONS,
                    IMAGE_NAME_ORDER, PATHS, PHASES, POSTTASK, SCREEN_TEXT,
                    SESSION, TIMING)
from presentation import (EndSession, Presentation, RestartBlock,
                          SkipSection, check_escape, set_trials_running)


def ask_demographics(pres):
    """Ask SONA ID, age (optional) and gender."""
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
    """Ask the post-task questions; save to <tracker file>_posttask.csv."""
    # Q3 image for each feature: only that feature present, e.g. 100000.png
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


def run_trial(pres, target, trial_n, previous_obj, feedback=True):
    """Run one trial and return its data row.

    Args:
        previous_obj: previous target (the prime); None on a block's first trial.
        feedback: False in test blocks.

    Names appear before the object so that cue-to-gaze time does not
    include searching for them. Each event is marked right after its flip.
    """
    times = {}

    def mark(event, **fields):
        # Three times per event: PsychoPy time and tracker time (both in
        # the trial file), and a marker in the tracker file.
        column = trialdata.EVENT_TIMES[event]
        times[column] = core.getTime()
        times[trialdata.tracker_column(column)] = eventlog.tracker_time_us()
        eventlog.mark(event, trial=trial_n, **fields)

    def tracker_us(event):
        return times[trialdata.tracker_column(trialdata.EVENT_TIMES[event])]

    rotation = geometry.ring_rotation()
    positions = geometry.ring_positions(rotation)

    # --- 1. central fixation ---------------------------------------------
    pres.draw_fixation()
    pres.flip()
    mark("dot_on", target=target, name=pres.stim_set.names[target],
         rotation_deg=f"{rotation:.2f}")
    # Live gaze state (whereGaze), from the dot until feedback or blank
    response.STATES.start(trial_n, positions, pres.ring_order,
                          pres.name_radius_px, tracker_us("dot_on"))
    response.wait_for_central_fixation(pres, CENTRAL_FIXATION['centralHold_ms'] / 1000)
    mark("fixation_held")

    # --- 2. preview -------------------------------------------------------
    # Random duration, so the object onset cannot be anticipated.
    pres.draw_names(positions)
    pres.draw_fixation()
    pres.flip()
    mark("names_on")
    response.STATES.show_names(tracker_us("names_on"))
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

    # The responder is polled once per frame.
    clock = core.Clock()
    while clock.getTime() < TIMING['responseTimeout_s'] and responder.result() is None:
        check_escape()
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
    if feedback:
        pres.draw_feedback(target, selection, positions)
        pres.flip()
        mark("feedback_on")
        response.STATES.stop(tracker_us("feedback_on"))
        core.wait(TIMING['feedbackDur'])

    # --- 5. blank interval ------------------------------------------------
    pres.flip()
    mark("blank_on")
    response.STATES.stop(tracker_us("blank_on"))   # test blocks (no feedback)
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
        "name": pres.stim_set.names[target],
        "targetImage": pres.stim_set.image_code(target),
        "rotation_deg": rotation,
    }
    for obj in pres.ring_order:
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


def demo_cut(targets, stage):
    """TEST: keep the first DEMO_TRIALS[stage] targets (all if None)."""
    limit = DEMO_TRIALS[stage]
    return targets if limit is None else targets[:limit]


class Session:
    """Session-wide trial count and rows.

    trial_n counts abandoned trials too, so trial numbers stay unique.
    """

    def __init__(self):
        self.trial_n = 0
        self.rows = []


def run_block(pres, session, block_info, targets, feedback):
    """Run one block of trials; return its rows.

    block_info is written on every row of the block.
    """
    eventlog.mark("block_start", **block_info)
    rows = []
    previous_obj = None
    pres.park_mouse()                   # cursor off the participant's screen
    set_trials_running(True)
    try:
        for target in targets:
            session.trial_n += 1
            trial = run_trial(pres, target, session.trial_n, previous_obj,
                              feedback)
            row = {**block_info, "feedback": feedback, **trial}
            trialdata.write_row(row)
            session.rows.append(row)
            rows.append(row)
            previous_obj = target
    finally:
        # Runs before the caller handles RestartBlock, so Esc during a
        # recalibration is not treated as during trials.
        set_trials_running(False)
    eventlog.mark("block_end", phase=block_info["phase"],
                  block=block_info["block"])
    return rows


def run_block_until_done(pres, session, phase, block_n, stim_set,
                         make_targets, feedback):
    """Run a block, and run it again (new seed) each time it is abandoned.

    Returns (rows, restarted); restarted is True if an attempt was abandoned.
    """
    pres.use_set(stim_set)
    restarted = False
    attempt = 0
    while True:
        attempt += 1
        seed = design.new_seed()
        block_info = {"phase": phase, "block": block_n, "attempt": attempt,
                      "stimSet": stim_set.label, "blockSeed": seed}
        try:
            rows = run_block(pres, session, block_info, make_targets(seed),
                             feedback)
            return rows, restarted
        except RestartBlock as restart:
            restarted = True
            # "lastTrial", not "trial": merge.py reads every marker with
            # "trial=" as a trial event.
            eventlog.mark("block_abandoned", phase=phase, block=block_n,
                          attempt=attempt, lastTrial=session.trial_n,
                          recalibrate=restart.recalibrate)
            print(f"{phase} block {block_n} abandoned at trial "
                  f"{session.trial_n}.")
            if restart.recalibrate:
                recalibrate(pres)
            pres.show_pages(SCREEN_TEXT["blockRestart"])


def run_practice(pres, session, stim_set):
    """Practice rounds until the participant chooses to move on."""
    round_n = 0
    try:
        while True:
            round_n += 1
            run_block_until_done(
                pres, session, "practice", round_n, stim_set,
                lambda seed: demo_cut(design.shuffled_sequence(
                    seed, stim_set.objects, PHASES["practiceTrials"]),
                    "practice"),
                feedback=True)
            key = pres.show_choice(SCREEN_TEXT["practiceChoice"],
                                   ["space", "right"])
            again = key == "space"
            eventlog.mark("practice_choice", round=round_n,
                          choice="again" if again else "move_on")
            if not again:
                return
    except SkipSection:
        eventlog.mark("section_skipped", phase="practice")
        print("Practice skipped by the researcher.")


def run_learning(pres, session, phase, stim_set):
    """Learning blocks until the criterion is met.

    An abandoned block resets the consecutive count to 0. If the criterion
    is not met in PHASES["learnMaxBlocks"] blocks, raises EndSession.
    """
    try:
        in_a_row = 0
        for block_n in range(1, PHASES["learnMaxBlocks"] + 1):
            rows, restarted = run_block_until_done(
                pres, session, phase, block_n, stim_set,
                lambda seed: demo_cut(design.shuffled_sequence(
                    seed, stim_set.objects, PHASES["learnBlockTrials"]),
                    "learning"),
                feedback=True)
            if restarted:
                in_a_row = 0

            n_correct = sum(row["outcome"] == "correct" for row in rows)
            proportion = n_correct / len(rows)
            if proportion >= PHASES["learnCriterion"]:
                in_a_row += 1
            else:
                in_a_row = 0
            print(f"{phase} block {block_n}: {n_correct}/{len(rows)} correct, "
                  f"{in_a_row} in a row at criterion")
            met = in_a_row >= PHASES["learnCriterionBlocks"]
            if met:
                next_part = "test"
            elif block_n == PHASES["learnMaxBlocks"]:
                next_part = "end"
            else:
                next_part = "round"
            pres.show_pages(SCREEN_TEXT["roundEnd"],
                            fill={"round": block_n,
                                  "percent": round(100 * proportion),
                                  "next":
                                      SCREEN_TEXT["roundEndNext"][next_part]})

            if met:
                eventlog.mark("criterion_met", phase=phase, blocks=block_n)
                return

        eventlog.mark("criterion_not_met", phase=phase,
                      blocks=PHASES["learnMaxBlocks"])
        raise EndSession(f"{phase}: criterion not met in "
                         f"{PHASES['learnMaxBlocks']} blocks")
    except SkipSection:
        eventlog.mark("section_skipped", phase=phase)
        print(f"{phase} skipped by the researcher.")


def run_test(pres, session, phase, stim_set):
    """Run one test block: one Euler tour, no feedback."""
    try:
        run_block_until_done(
            pres, session, phase, 1, stim_set,
            lambda seed: demo_cut(design.trial_sequence(seed, stim_set.objects),
                                  "test"),
            feedback=False)
    except SkipSection:
        eventlog.mark("section_skipped", phase=phase)
        print(f"{phase} skipped by the researcher.")


def calibration_fields(accuracy):
    """Calibration error per eye as marker fields, e.g. cal_left_deg=0.130."""
    return {f"cal_{eye}_deg": f"{entry['accuracy_deg']:.3f}"
            for eye, entry in accuracy.items()}


def run_calibration(pres):
    """Calibrate until both eyes pass (no attempt limit).

    Assumes the tracker is set to raw results and is tracking.
    Returns (accuracy, attempts).
    """
    pres.show_pages(SCREEN_TEXT["calibration"])
    attempts = 0
    while True:
        attempts += 1
        pres.park_mouse()
        accuracy = calibrate.gaze_calibration(pres.win)
        if calibrate.report_calibration(accuracy, attempts):
            print(f"PASSED on attempt {attempts}.")
            pres.show_pages(SCREEN_TEXT["calibrationDone"])
            return accuracy, attempts
        print(f"FAILED (attempt {attempts}); running it again. Adjust the "
              "camera or the participant if needed (Esc: pause screen).")
        pres.show_pages(SCREEN_TEXT["calibrationFailed"])


def recalibrate(pres):
    """Calibrate again mid-session, with the data file open.

    Samples between the recalibration_start and recalibration_end markers
    are raw (not screen pixels); the merge step can drop them.
    NOT YET TESTED: whether the data file keeps recording across
    StopTracking/StartTracking.
    """
    eventlog.mark("recalibration_start")
    # The marker is written with the next sample, so let one arrive first.
    core.wait(0.01)
    LiveTrack.StopTracking()
    LiveTrack.SetResultsTypeRaw()
    LiveTrack.StartTracking()

    accuracy, attempts = run_calibration(pres)

    LiveTrack.StopTracking()
    LiveTrack.SetResultsTypeCalibrated()
    LiveTrack.ClearDataBuffer()
    LiveTrack.StartTracking()
    core.wait(0.5)        # past the tracker's clock reset, as at the start
    eventlog.mark("recalibration_end", attempts=attempts,
                  **calibration_fields(accuracy))


def main():
    geometry.check_feedback_fit()
    geometry.ring_rotation()          # stops here if the setting is invalid
    design.check_design()

    # Phase 2 is not run for now, but its set is still built and logged.
    sets = design.stimulus_sets()
    practice_set = sets["practice"]
    phase1_set = sets["phase1"]
    phase2_set = sets["phase2"]
    used_sets = [practice_set, phase1_set, phase2_set]
    print(f"Group cell {COUNTERBALANCE['groupCell']} "
          f"({design.phase2_relation()}):")
    for phase in (phase1_set, phase2_set):
        print(f"  {phase.label}: context {phase.context_label}, "
              f"object set {phase.object_set}")
    # Builds one test order now, so an Euler tour problem shows up early.
    test_length = len(design.trial_sequence(1, phase1_set.objects))
    if any(v is not None for v in DEMO_TRIALS.values()):
        print(f"DEMO: blocks cut to {DEMO_TRIALS} (config.DEMO_TRIALS)")
    print(f"Practice rounds of {PHASES['practiceTrials']}; learning blocks of "
          f"{PHASES['learnBlockTrials']}; test blocks of {test_length}")

    pres = Presentation()
    screen_rate = pres.win.getActualFrameRate()    # None if it was unstable

    LiveTrack.Init()
    LiveTrack.SetResultsTypeRaw()     # calibration reads pupil/glint vectors
    LiveTrack.StartTracking()
    tracker_rate = LiveTrack.GetCaptureConfig()[2]
    tracked_eyes = LiveTrack.GetTracking()          # (left, right)

    session = None                    # set once recording starts
    accuracy = {}                     # stays empty if calibration is skipped
    calibration_attempts = 0
    participant = {"sonaID": "debug", "age": "", "gender": ""}
    try:
        # Inside the try, so Esc here still closes the window and tracker.
        pres.show_pages(SCREEN_TEXT["greeting"])
        if SESSION["yesDemographics"]:
            participant = ask_demographics(pres)
        pid = participant["sonaID"]

        pres.show_pages(SCREEN_TEXT["task"])

        pres.park_mouse()

        if SESSION["yesCalibration"]:
            accuracy, calibration_attempts = run_calibration(pres)

        # From here gaze is in screen pixels centred at 0,0 (the units of
        # the calibration targets). The results type is set while tracking
        # is stopped, as in CRS's demos.
        LiveTrack.StopTracking()
        LiveTrack.SetResultsTypeCalibrated()
        LiveTrack.ClearDataBuffer()

        # Recording starts after calibration, so the file holds only
        # calibrated data.
        path = eventlog.open_session(pid)
        LiveTrack.StartTracking()
        print(f"Recording to {path}")

        # The tracker resets its clock about 0.4 s after recording starts;
        # wait so every marker comes after the reset.
        core.wait(0.5)

        columns = trialdata.session_columns(
            participant, accuracy,
            datetime.now().isoformat(timespec="seconds"),
            screen_rate, tracker_rate, tracked_eyes, used_sets,
            calibration_attempts)
        # Needed later to judge where gaze was
        columns["nameSelectRadius_px"] = round(pres.name_radius_px, 2)
        columns["px_per_deg"] = round(geometry.px_per_deg(), 4)
        session_path, trials_path = trialdata.open_files(path, pid, columns)
        print(f"Session to {session_path}")
        print(f"Trials to {trials_path}")
        session = Session()

        # One marker only: markers sent close together can merge into one.
        eventlog.mark("session_start", participant=pid,
                      **calibration_fields(accuracy))

        pres.show_pages(SCREEN_TEXT["practice"])
        run_practice(pres, session, practice_set)

        pres.show_pages(SCREEN_TEXT["learning"])
        run_learning(pres, session, "learning1", phase1_set)
        pres.show_pages(SCREEN_TEXT["test"])
        run_test(pres, session, "test1", phase1_set)

        # Learning 2 and test 2 are off for now. To add them back:
        #   pres.show_pages(SCREEN_TEXT["learning2"])
        #   run_learning(pres, session, "learning2", phase2_set)
        #   pres.show_pages(SCREEN_TEXT["test"])
        #   run_test(pres, session, "test2", phase2_set)

        eventlog.mark("trials_end")
        pres.show_pages(SCREEN_TEXT["taskEnd"])
        posttask_q(pres, path)
        eventlog.mark("session_end")
        pres.show_debrief()
    except EndSession as e:
        # Data so far are on disk; the participant still gets the debrief.
        set_trials_running(False)
        eventlog.mark("session_ended_early")    # no-op before recording
        print(f"\nENDED EARLY: {e}")
        pres.show_debrief()
    except response.FixationTimeout as e:
        eventlog.mark("session_aborted", reason="fixation_timeout")
        print(f"\nABORTED: {e}")
        print("Check that the eye is in view and that gaze reads near the "
              "dot when the participant looks at it; recalibrate if not.")
    finally:
        trialdata.close_file()
        eventlog.close_session()
        LiveTrack.StopTracking()
        LiveTrack.ClearDataBuffer()
        LiveTrack.Close()
        pres.close()

    print(participant)
    if session is not None:
        for r in session.rows:
            print(r["phase"], r["block"], r["attempt"], r["trialN"],
                  r["targetObj"], r["outcome"], r["selection_ms"])


if __name__ == "__main__":
    main()
