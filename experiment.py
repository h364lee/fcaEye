"""
Experiment skeleton. Runs end to end with the mouse standing in for the eye
tracker, so it can be tested without hardware.

Phases:
    1. instructions
    2. training 1      name-object association to criterion, click response, feedback
    3. practice        dwell selection rule, no data kept
    4. test 1          saccade after central name cue, dwell selection, no feedback
    5. training 2      second attribute set, same criterion  (this is the 5.2 measure)
    6. test 2

Mouse stands in for gaze:
    click        -> training response
    hover-dwell  -> test response (stands in for fixation dwell)
Every place the tracker replaces the mouse is marked TRACKER SEAM.

Run from the folder containing stims/:  python experiment.py
Escape quits at any point. Data is written to data/<subject>_<timestamp>.csv
"""

import csv
import json
import math
import random
from datetime import datetime
from pathlib import Path

from psychopy import core, event, visual

# ---------------------------------------------------------------------------
# PARAMETERS  (arbitrary for now; to be grounded later)
# ---------------------------------------------------------------------------

SUBJECT = "test01"

WINDOW_SIZE = [1200, 900]
FULLSCREEN = False
BACKGROUND = [0, 0, 0]          # mid grey in PsychoPy's -1..1 scale

RING_RADIUS = 350
N_POSITIONS = 5
OBJECT_PX = 140
FIX_SIZE = 20
NAME_HEIGHT = 36
TOLERANCE = 100                 # px, selection radius around an object

PREVIEW_RANGE = (0.6, 1.0)      # jittered, so cue onset cannot be anticipated
RESPONSE_TIMEOUT = 8.0
FEEDBACK_DUR = 0.8
ITI = 1.0
DWELL_MS = 400                  # how long the eye must rest on a target to select it

BLOCK_REPEATS = 2               # each object cued this many times per block
CRITERION = 0.90
CRITERION_BLOCKS = 3            # consecutive blocks at criterion
MAX_BLOCKS = 30                 # give up rather than run forever
PRACTICE_TRIALS = 5
TEST_TRIALS = 20

NAMES_A = {"g1": "Bala", "g2": "Kopo", "g3": "Vemi", "g4": "Zudo", "g5": "Tora"}
NAMES_B = {"g1": "Daxi", "g2": "Fepo", "g3": "Mura", "g4": "Sani", "g5": "Zelo"}

STIM_DIR = Path("stims_geo/set1")
DATA_DIR = Path("data")

# ---------------------------------------------------------------------------
# SETUP
# ---------------------------------------------------------------------------

manifest = json.loads((STIM_DIR / "manifest.json").read_text())

win = visual.Window(size=WINDOW_SIZE, units="pix", color=BACKGROUND,
                    fullscr=FULLSCREEN, allowGUI=True)
mouse = event.Mouse(win=win)

fixation = visual.Circle(win, radius=FIX_SIZE / 2, fillColor="white", lineColor="white")
cue_text = visual.TextStim(win, text="", height=NAME_HEIGHT, color="white")
message = visual.TextStim(win, text="", height=24, color="white", wrapWidth=850)
feedback_text = visual.TextStim(win, text="", height=28, color="white",
                                pos=(0, -RING_RADIUS - 120))
highlight = visual.Circle(win, radius=OBJECT_PX * 0.62, fillColor=None,
                          lineColor="lime", lineWidth=5)

# Both phases use the same images for now; phase 2 needs its own attribute set.
stims = {name: visual.ImageStim(win, image=str(STIM_DIR / manifest["objects"][code]["file"]),
                                size=OBJECT_PX)
         for name, code in manifest["object_assignment"].items()}

# Object order around the ring: fixed for this participant, random across
# participants. Index i occupies ring position i.
ring_order = list(stims)
random.shuffle(ring_order)

trials_log = []


# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------

def check_quit():
    if "escape" in event.getKeys(["escape"]):
        save_data()
        win.close()
        core.quit()


def show_message(text, keys=("space",)):
    message.text = text + "\n\n(press space)"
    message.draw()
    win.flip()
    if "escape" in event.waitKeys(keyList=list(keys) + ["escape"]):
        save_data()
        win.close()
        core.quit()


def ring_positions(rotation_deg):
    """Five equally spaced positions, the whole ring turned by rotation_deg.

    Rotation is drawn from 0-72 degrees because five equally spaced positions
    repeat every 72 degrees; beyond that adds nothing.
    """
    out = []
    for i in range(N_POSITIONS):
        a = math.radians(rotation_deg + i * 360 / N_POSITIONS)
        out.append((RING_RADIUS * math.cos(a), RING_RADIUS * math.sin(a)))
    return out


def draw_objects(positions):
    for name, pos in zip(ring_order, positions):
        stims[name].pos = pos
        stims[name].draw()


def object_under(point, positions):
    """Which object contains this point, or None.

    Adjacent objects are ~411 px apart and the tolerance is 100 px, so a point
    cannot be inside two of them.
    """
    for name, pos in zip(ring_order, positions):
        if math.hypot(point[0] - pos[0], point[1] - pos[1]) < TOLERANCE:
            return name
    return None


def block_sequence():
    """One block: every object cued BLOCK_REPEATS times, shuffled."""
    seq = list(stims) * BLOCK_REPEATS
    random.shuffle(seq)
    return seq


# ---------------------------------------------------------------------------
# RESPONSE COLLECTION
# ---------------------------------------------------------------------------

def collect_click(positions, timeout):
    """Training response. TRACKER SEAM: unchanged, training stays mouse-based."""
    clock = core.Clock()
    mouse.clickReset()
    while clock.getTime() < timeout:
        check_quit()
        if mouse.getPressed()[0]:
            hit = object_under(mouse.getPos(), positions)
            if hit is not None:
                return hit, clock.getTime() * 1000
    return None, None


def collect_dwell(positions, timeout):
    """Test response, by resting the pointer on an object.

    TRACKER SEAM: replace mouse.getPos() with the tracker's latest gaze sample.
    Returns (selection, selection_time_ms, first_move_ms), where first_move_ms
    is the time the pointer first left the centre. With the tracker that is the
    saccade latency for the 5.1 model, which is a separate measure from which
    object ends up selected.
    """
    clock = core.Clock()
    dwell_start, dwell_on = None, None
    first_move = None

    while clock.getTime() < timeout:
        check_quit()
        pos = mouse.getPos()
        t = clock.getTime()

        if first_move is None and math.hypot(pos[0], pos[1]) > TOLERANCE:
            first_move = t * 1000

        here = object_under(pos, positions)
        if here is None or here != dwell_on:
            dwell_on, dwell_start = here, t      # reset on leaving a target
        elif (t - dwell_start) * 1000 >= DWELL_MS:
            return here, t * 1000, first_move

    return None, None, first_move


# ---------------------------------------------------------------------------
# TRIAL
# ---------------------------------------------------------------------------

def run_trial(target, names, gaze_selection, feedback, phase, block, index):
    """One trial of any phase. Returns a log row."""
    rotation = random.uniform(0, 360 / N_POSITIONS)
    positions = ring_positions(rotation)

    # --- 1. fixation, objects not yet shown -------------------------------
    # TRACKER SEAM: replace the keypress with wait_for_central_fixation().
    fixation.draw()
    win.flip()
    event.clearEvents()
    if "escape" in event.waitKeys(keyList=["space", "escape"]):
        save_data()
        win.close()
        core.quit()

    # --- 2. preview: objects appear, fixation still held ------------------
    # TRACKER SEAM: fixation must be maintained here; recycle the trial if the
    # eye leaves the boundary. Nothing enforces it with the mouse.
    draw_objects(positions)
    fixation.draw()
    win.flip()
    core.wait(random.uniform(*PREVIEW_RANGE))

    # --- 3. cue: the dot becomes the name. No gap, so no express saccades --
    cue_text.text = names[target]
    draw_objects(positions)
    cue_text.draw()
    win.flip()

    if gaze_selection:
        response, rt, first_move = collect_dwell(positions, RESPONSE_TIMEOUT)
    else:
        response, rt = collect_click(positions, RESPONSE_TIMEOUT)
        first_move = None

    # --- 4. feedback (training only), corrective --------------------------
    if feedback:
        highlight.pos = positions[ring_order.index(target)]
        feedback_text.text = ("correct" if response == target
                              else f"{names[target]}" if response
                              else f"too slow  -  {names[target]}")
        draw_objects(positions)
        highlight.draw()
        feedback_text.draw()
        win.flip()
        core.wait(FEEDBACK_DUR)

    # --- 5. inter-trial interval ------------------------------------------
    # The interval over which a prime from trial N decays before trial N+1.
    win.flip()
    core.wait(ITI)

    return {
        "subject": SUBJECT, "phase": phase, "block": block, "trial": index,
        "cue": names[target], "target": target, "response": response,
        "correct": int(response == target),
        "rt_ms": None if rt is None else round(rt, 1),
        "first_move_ms": None if first_move is None else round(first_move, 1),
        "rotation_deg": round(rotation, 2),
        "ring_order": " ".join(ring_order),
    }


# ---------------------------------------------------------------------------
# PHASES
# ---------------------------------------------------------------------------

def run_training(phase, names):
    """Blocks until CRITERION_BLOCKS consecutive blocks reach CRITERION.

    Returns trials to criterion, which is the dependent measure for the
    transfer analysis in section 5.2.
    """
    consecutive, total, block = 0, 0, 0

    while consecutive < CRITERION_BLOCKS and block < MAX_BLOCKS:
        block += 1
        rows = [run_trial(t, names, gaze_selection=False, feedback=True,
                          phase=phase, block=block, index=i)
                for i, t in enumerate(block_sequence(), 1)]
        trials_log.extend(rows)
        total += len(rows)

        accuracy = sum(r["correct"] for r in rows) / len(rows)
        consecutive = consecutive + 1 if accuracy >= CRITERION else 0
        show_message(f"Block {block} complete.  Accuracy {accuracy:.0%}.")

    return total


def run_practice(names):
    """Exposes the dwell selection rule before anything is measured."""
    for i in range(1, PRACTICE_TRIALS + 1):
        run_trial(random.choice(list(stims)), names, gaze_selection=True,
                  feedback=True, phase="practice", block=0, index=i)


def run_test(phase, names):
    """Dwell selection, no feedback. Trial order is random here; the Direction
    conditions of section 5.1 are derived afterwards from consecutive pairs,
    so `prev_target` is what the analysis needs and it is in the log."""
    prev = None
    for i in range(1, TEST_TRIALS + 1):
        target = random.choice(list(stims))
        row = run_trial(target, names, gaze_selection=True, feedback=False,
                        phase=phase, block=1, index=i)
        row["prev_target"] = prev
        trials_log.append(row)
        prev = target


# ---------------------------------------------------------------------------
# DATA
# ---------------------------------------------------------------------------

def save_data():
    if not trials_log:
        return
    DATA_DIR.mkdir(exist_ok=True)
    path = DATA_DIR / f"{SUBJECT}_{datetime.now():%Y%m%d_%H%M%S}.csv"
    fields = sorted({k for row in trials_log for k in row})
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(trials_log)
    print(f"saved {len(trials_log)} trials to {path}")


# ---------------------------------------------------------------------------
# RUN
# ---------------------------------------------------------------------------

show_message(
    "Fixate the central dot and press SPACE to start each trial.\n\n"
    "Objects appear. Keep looking at the dot.\n\n"
    "When the dot turns into a name, choose the object it belongs to.\n\n"
    "In the learning blocks you click. In the test blocks you select by "
    "resting the pointer on an object.")

show_message("Learning block 1.\nClick the object that matches the name.")
n1 = run_training("training_1", NAMES_B)

show_message("Practice.\nNow select by resting the pointer on an object "
             "instead of clicking.")
run_practice(NAMES_B)

show_message("Test block 1.\nNo feedback from here.")
run_test("test_1", NAMES_B)

show_message("Learning block 2.\nNew objects and new names.")
n2 = run_training("training_2", NAMES_B)

show_message("Test block 2.")
run_test("test_2", NAMES_B)

show_message(f"Finished.\n\nTrials to criterion: {n1} then {n2}.")
save_data()
win.close()
core.quit()
