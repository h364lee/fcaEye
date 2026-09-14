"""
Five trials of the stimulus presentation sequence, without the eye tracker.

Trial sequence:
    1. central dot, participant fixates          (tracker seam: spacebar here)
    2. objects appear, dot still shown, preview  (tracker seam: no fixation check)
    3. dot becomes the name, participant responds(tracker seam: mouse click here)
    4. corrective feedback
    5. blank inter-trial interval

Object order around the ring is fixed for a participant; the whole ring rotates
each trial so screen positions cannot be learned. Rotation is drawn from 0-72
degrees because five equally spaced positions repeat every 72 degrees.

Run from the folder containing stims/:  python demo_trials.py
Escape quits at any point.
"""

import json
import math
import random
from pathlib import Path

from psychopy import core, event, visual

# ---------------------------------------------------------------------------
# PARAMETERS  (arbitrary for now; to be grounded later)
# ---------------------------------------------------------------------------

N_TRIALS = 5
WINDOW_SIZE = [1200, 900]      # windowed so it is easy to escape; fullscreen for real runs
BACKGROUND = [0, 0, 0]         # mid grey in PsychoPy's -1..1 scale

RING_RADIUS = 350              # px from centre to each object
N_POSITIONS = 5
OBJECT_PX = 140                # displayed size; adjacent objects are ~411 px apart

FIX_SIZE = 20
NAME_HEIGHT = 36

PREVIEW_RANGE = (0.6, 1.0)     # jittered, so cue onset cannot be anticipated
RESPONSE_TIMEOUT = 2.0
FEEDBACK_DUR = 0.8
ITI = 1.0

CLICK_TOLERANCE = 100          # stands in for TARGET_TOLERANCE_PIX

NAMES = {"g1": "Bala", "g2": "Kopo", "g3": "Vemi", "g4": "Zudo", "g5": "Tora"}

STIM_DIR = Path("stims")


# ---------------------------------------------------------------------------
# SETUP
# ---------------------------------------------------------------------------

manifest = json.loads((STIM_DIR / "manifest.json").read_text())

# g1..g5 -> image path, via the assignment table in the manifest
object_files = {
    name: STIM_DIR / manifest["objects"][code]["file"]
    for name, code in manifest["object_assignment"].items()
}

win = visual.Window(size=WINDOW_SIZE, units="pix", color=BACKGROUND,
                    fullscr=False, allowGUI=True)
mouse = event.Mouse(win=win)

fixation = visual.Circle(win, radius=FIX_SIZE / 2, fillColor="white", lineColor="white")
cue_text = visual.TextStim(win, text="", height=NAME_HEIGHT, color="white")
feedback_text = visual.TextStim(win, text="", height=28, color="white", pos=(0, -RING_RADIUS - 120))
highlight = visual.Circle(win, radius=OBJECT_PX * 0.62, fillColor=None,
                          lineColor="lime", lineWidth=5)

stims = {name: visual.ImageStim(win, image=str(path), size=OBJECT_PX)
         for name, path in object_files.items()}

# Order of objects around the ring: fixed for this participant, random across
# participants. Index i in this list occupies ring position i.
ring_order = list(NAMES)
random.shuffle(ring_order)


# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------

def ring_positions(rotation_deg):
    """Five equally spaced positions, the whole ring turned by rotation_deg."""
    positions = []
    for i in range(N_POSITIONS):
        angle = math.radians(rotation_deg + i * 360 / N_POSITIONS)
        positions.append((RING_RADIUS * math.cos(angle), RING_RADIUS * math.sin(angle)))
    return positions


def check_quit():
    if "escape" in event.getKeys(["escape"]):
        win.close()
        core.quit()


def draw_objects(positions):
    for name, pos in zip(ring_order, positions):
        stims[name].pos = pos
        stims[name].draw()


def nearest_object(click_pos, positions):
    """Which object was clicked, or None if the click was not near any.

    Stands in for first-landing scoring. The ring geometry means a click near
    one object cannot be near another: adjacent objects are ~411 px apart and
    the tolerance is 100 px.
    """
    for name, pos in zip(ring_order, positions):
        if math.hypot(click_pos[0] - pos[0], click_pos[1] - pos[1]) < CLICK_TOLERANCE:
            return name
    return None


# ---------------------------------------------------------------------------
# TRIAL
# ---------------------------------------------------------------------------

def run_trial(target):
    """One trial. Returns a dict of what happened."""
    positions = ring_positions(random.uniform(0, 360 / N_POSITIONS))

    # --- 1. fixation, objects not yet shown -------------------------------
    # EYE TRACKER SEAM: replace with wait_for_central_fixation().
    fixation.draw()
    win.flip()
    event.clearEvents()
    keys = event.waitKeys(keyList=["space", "escape"])
    if "escape" in keys:
        win.close()
        core.quit()

    # --- 2. preview: objects appear, fixation still required --------------
    # EYE TRACKER SEAM: fixation must be held throughout here, trial recycled
    # if the eye leaves the boundary. Nothing enforces it without the tracker.
    draw_objects(positions)
    fixation.draw()
    win.flip()
    core.wait(random.uniform(*PREVIEW_RANGE))

    # --- 3. cue: the dot becomes the name; no gap, so no express saccades --
    cue_text.text = NAMES[target]
    draw_objects(positions)
    cue_text.draw()
    win.flip()

    clock = core.Clock()
    mouse.clickReset()
    response, latency = None, None

    # EYE TRACKER SEAM: replace this loop with first-landing detection.
    while clock.getTime() < RESPONSE_TIMEOUT:
        check_quit()
        if mouse.getPressed()[0]:
            hit = nearest_object(mouse.getPos(), positions)
            if hit is not None:
                response, latency = hit, clock.getTime() * 1000
                break

    # --- 4. corrective feedback -------------------------------------------
    # Corrective, not just right/wrong, because Phase 1 trains the name-object
    # mapping to criterion and "wrong" alone does not teach it.
    correct_pos = positions[ring_order.index(target)]
    highlight.pos = correct_pos
    if response is None:
        feedback_text.text = f"too slow  -  {NAMES[target]}"
    elif response == target:
        feedback_text.text = "correct"
    else:
        feedback_text.text = f"incorrect  -  {NAMES[target]}"

    draw_objects(positions)
    highlight.draw()
    feedback_text.draw()
    win.flip()
    core.wait(FEEDBACK_DUR)

    # --- 5. inter-trial interval ------------------------------------------
    # This is the interval over which a prime from trial N decays before N+1.
    win.flip()
    core.wait(ITI)

    return {"target": target, "response": response,
            "correct": response == target,
            "latency_ms": None if latency is None else round(latency, 1)}


# ---------------------------------------------------------------------------
# RUN
# ---------------------------------------------------------------------------

instructions = visual.TextStim(
    win, height=24, wrapWidth=800, color="white",
    text=("Fixate the central dot and press SPACE.\n\n"
          "Objects will appear. Keep looking at the dot.\n\n"
          "When the dot turns into a name, click the object it belongs to.\n\n"
          "Press SPACE to begin."))
instructions.draw()
win.flip()
if "escape" in event.waitKeys(keyList=["space", "escape"]):
    win.close()
    core.quit()

# All five objects cued once, in random order.
targets = list(NAMES)
random.shuffle(targets)

results = [run_trial(t) for t in targets[:N_TRIALS]]

win.close()

print(f"ring order: {ring_order}")
for i, r in enumerate(results, 1):
    print(f"trial {i}: cue={NAMES[r['target']]:<5} response={r['response']} "
          f"correct={r['correct']} latency={r['latency_ms']}")

core.quit()
