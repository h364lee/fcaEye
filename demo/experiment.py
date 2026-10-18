"""experiment.py: session and trial flow.

Session:
    greeting, demographics -> task instructions -> calibration ->
    recording starts ->
    practice (1 block, placeholder objects) ->
    learning 1 (blocks until the criterion; config.PHASES) -> test 1 ->
    learning 2 -> test 2 ->
    post-task questions -> thank you, debrief letter

A learning block: each object equally often in random order, feedback.
A test block: one Euler tour (design.trial_sequence), no feedback.

Esc opens a pause screen (presentation.pause_menu). The researcher chooses:
    End      -> data stay saved; go to the debrief letter
    Continue -> outside a block: the same screen carries on
                inside a block: optional recalibration, then the block
                starts again with a new order; in learning, the count of
                consecutive blocks at criterion starts again from 0
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
from config import (CENTRAL_FIXATION, COUNTERBALANCE, DEMO_TRIALS,
                    GENDER_OPTIONS,
                    IMAGE_NAME_ORDER, PATHS, PHASES, POSTTASK, SCREEN_TEXT,
                    SESSION, TIMING)
from presentation import (EndSession, Presentation, RestartBlock,
                          check_escape, set_trials_running)


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


def run_trial(pres, target, trial_n, previous_obj, feedback=True):
    """Run one trial and return what happened.

    Uses the stimulus set last given to pres.use_set().
    previous_obj: the previous trial's target (the prime), None on the
    first trial of a block.
    feedback: False in test blocks; step 4 is then skipped.

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
    mark("dot_on", target=target, name=pres.stim_set.names[target],
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
    """TEMPORARY: the first DEMO_TRIALS[stage] targets, or all if None."""
    limit = DEMO_TRIALS[stage]
    return targets if limit is None else targets[:limit]


class Session:
    """What every block needs, kept in one place.

    columns: the session columns written on every trial row
    trial_n: trials started so far, abandoned ones included, so trial
             numbers stay unique in the data files
    rows:    every trial row written, for the summary at the end
    """

    def __init__(self, columns):
        self.columns = columns
        self.trial_n = 0
        self.rows = []


def run_block(pres, session, block_info, targets, feedback):
    """Run one block of trials; return its rows.

    block_info: phase, block, attempt, stimSet and blockSeed, written on
    every row of the block.
    """
    eventlog.mark("block_start", **block_info)
    rows = []
    previous_obj = None                 # first trial of a block has no prime
    set_trials_running(True)
    try:
        for target in targets:
            session.trial_n += 1
            trial = run_trial(pres, target, session.trial_n, previous_obj,
                              feedback)
            row = {**block_info, "feedback": feedback, **trial}
            trialdata.write_row(session.columns, row)
            session.rows.append(row)
            rows.append(row)
            previous_obj = target
    finally:
        # Runs before the caller handles RestartBlock, so a recalibration
        # there is not treated as trials (Continue resumes the calibration).
        set_trials_running(False)
    eventlog.mark("block_end", phase=block_info["phase"],
                  block=block_info["block"])
    return rows


def run_block_until_done(pres, session, phase, block_n, stim_set,
                         make_targets, feedback):
    """Run a block; if it is abandoned from the pause screen, run it again.

    make_targets(seed) returns the block's targets. Each attempt gets a new
    seed, so a repeated block does not repeat the same order.

    Returns (rows, restarted). restarted is True if an attempt was abandoned.
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
    """One block of placeholder trials, to learn the gaze selection."""
    run_block_until_done(
        pres, session, "practice", 1, stim_set,
        lambda seed: demo_cut(design.shuffled_sequence(
            seed, stim_set.objects, PHASES["practiceTrials"]), "practice"),
        feedback=True)


def run_learning(pres, session, phase, stim_set):
    """Learning blocks until the criterion is met; return the blocks run.

    Criterion: at least PHASES["learnCriterion"] correct (a timeout counts
    as not correct) in PHASES["learnCriterionBlocks"] consecutive blocks.
    An abandoned block sets the count back to 0.
    Not met within PHASES["learnMaxBlocks"] blocks -> EndSession, so the
    participant goes to the debrief.
    """
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
        pres.show_pages(SCREEN_TEXT["roundEnd"],
                        fill={"round": block_n,
                              "percent": round(100 * proportion)})

        if in_a_row >= PHASES["learnCriterionBlocks"]:
            eventlog.mark("criterion_met", phase=phase, blocks=block_n)
            return block_n

    eventlog.mark("criterion_not_met", phase=phase,
                  blocks=PHASES["learnMaxBlocks"])
    raise EndSession(f"{phase}: criterion not met in "
                     f"{PHASES['learnMaxBlocks']} blocks")


def run_test(pres, session, phase, stim_set):
    """One test block: one Euler tour, no feedback."""
    run_block_until_done(
        pres, session, phase, 1, stim_set,
        lambda seed: demo_cut(design.trial_sequence(seed, stim_set.objects),
                              "test"),
        feedback=False)


def run_calibration(pres):
    """Calibrate until both eyes pass; return (accuracy, attempts).

    Assumes the tracker is set to raw results and is tracking.

    After a failure the participant sees a waiting screen (4b) and the
    researcher chooses: R recalibrates, Esc ends the session (EndSession,
    so the participant still gets the debrief). No limit on attempts; the
    count is shown in the terminal and saved.
    """
    attempts = 0
    while True:
        attempts += 1
        pres.show_pages(SCREEN_TEXT["calibration"])   # Screen 3
        accuracy = calibrate.gaze_calibration(pres.win)
        if calibrate.report_calibration(pres, accuracy, attempts):
            print(f"PASSED on attempt {attempts}.")
            break
        print(f"FAILED (attempt {attempts}). Adjust the camera or the "
              "participant, then press R to recalibrate, or Esc to end "
              "the session.")
        key = pres.show_waiting(SCREEN_TEXT["calibrationWait"],   # Screen 4b
                                ["r", "escape"])
        if key == "escape":
            raise EndSession("ended after failed calibration")
    pres.show_pages(SCREEN_TEXT["calibrationDone"])   # Screen 4
    return accuracy, attempts


def recalibrate(pres):
    """Calibrate again in the middle of a session, with the data file open.

    Same tracker steps as at the session start: raw results for the
    calibration, then calibrated results again. The samples recorded in
    between are raw (pupil/glint vectors, not screen pixels), so they sit
    between the recalibration_start and recalibration_end markers, where
    the merge step can drop them.

    NOT YET TESTED on the tracker: whether the data file keeps recording
    across StopTracking/StartTracking.
    """
    eventlog.mark("recalibration_start")
    # The marker is written with the next sample (eventlog.py), so let one
    # sample arrive before tracking stops.
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
    calibration = {f"cal_{eye}_deg": f"{entry['accuracy_deg']:.3f}"
                   for eye, entry in accuracy.items()}
    eventlog.mark("recalibration_end", attempts=attempts, **calibration)


def show_ending(pres):
    """Debrief letter and end screen (Screens 13-15).

    Shown after a full session and after End on the pause screen. The data
    are saved by then, so Esc here only skips ahead: it leaves the letter,
    and closes the end screen.
    """
    pres.show_debrief()
    pres.show_pages(SCREEN_TEXT["endOfStudy"], escape_exits=True)


def main():
    geometry.check_feedback_fit()
    geometry.ring_rotation()          # stops here if the setting is invalid
    design.check_design()

    # Stimulus sets for this session. A test order is built once here, so
    # a problem with the Euler tour shows up before anything opens.
    sets = design.stimulus_sets()
    practice_set = sets["practice"]
    phase1_set = sets["phase1"]
    phase2_set = sets["phase2"]
    used_sets = [practice_set, phase1_set, phase2_set]
    # Shown in the terminal so the researcher can check the condition
    print(f"Group cell {COUNTERBALANCE['groupCell']} "
          f"({design.phase2_relation()}):")
    for phase in (phase1_set, phase2_set):
        print(f"  {phase.label}: context {phase.context_label}, "
              f"object set {phase.object_set}")
    test_length = len(design.trial_sequence(1, phase1_set.objects))
    if any(v is not None for v in DEMO_TRIALS.values()):
        print(f"DEMO: blocks cut to {DEMO_TRIALS} (config.DEMO_TRIALS)")
    print(f"Practice {PHASES['practiceTrials']} trials; learning blocks of "
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
    calibration_attempts = 0          # stays 0 if calibration is skipped
    participant = {"sonaID": "debug", "age": "", "gender": ""}
    try:
        # Inside the try, so Esc during the questions still closes the
        # window and the tracker.
        pres.show_pages(SCREEN_TEXT["greeting"])          # Screen 1
        if SESSION["yesDemographics"]:
            participant = ask_demographics(pres)            # Screen 2
        pid = participant["sonaID"]

        pres.show_pages(SCREEN_TEXT["task"])               # Screen 5

        # From here on the cursor must not be on the stimulus screen.
        pres.park_mouse()

        if SESSION["yesCalibration"]:
            accuracy, calibration_attempts = run_calibration(pres)

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

        columns = trialdata.session_columns(
            participant, accuracy,
            datetime.now().isoformat(timespec="seconds"),
            screen_rate, tracker_rate, tracked_eyes, used_sets,
            calibration_attempts)
        print(f"Trials to {trialdata.open_file(path, columns)}")
        session = Session(columns)

        # One marker for everything known at the start. Markers sent close
        # together can collapse into one (seen with the two calibration
        # markers), so these values share a single comment.
        calibration = {f"cal_{eye}_deg": f"{entry['accuracy_deg']:.3f}"
                       for eye, entry in accuracy.items()}
        eventlog.mark("session_start", participant=pid, **calibration)

        pres.show_pages(SCREEN_TEXT["practice"])
        run_practice(pres, session, practice_set)

        pres.show_pages(SCREEN_TEXT["learning"])           # Screen 6
        run_learning(pres, session, "learning1", phase1_set)
        pres.show_pages(SCREEN_TEXT["test"])               # Screen 8
        run_test(pres, session, "test1", phase1_set)

        pres.show_pages(SCREEN_TEXT["learning2"])
        run_learning(pres, session, "learning2", phase2_set)
        pres.show_pages(SCREEN_TEXT["test"])
        run_test(pres, session, "test2", phase2_set)

        eventlog.mark("trials_end")
        posttask_q(pres, path)
        eventlog.mark("session_end")
        show_ending(pres)
    except EndSession as e:
        # Everything written so far is already on disk. The participant
        # still gets the debrief, as after a full session.
        set_trials_running(False)
        eventlog.mark("session_ended_early")    # no-op before recording
        print(f"\nENDED EARLY: {e}")
        show_ending(pres)
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
