"""
Keep all variables here - 2026-09-12
"""
SESSION = {
    "yesDemographics": False,     # False: skip the questions, ID becomes "debug"
    "yesCalibration": False,      # False: use the calibration stored in the tracker
}

GENDER_OPTIONS = [
    "Woman",
    "Man",
    "Non-binary",
    "Prefer to self-describe",
    "Prefer not to answer",
]

DISPLAY = {
    "size": [1024, 768],
    "fullscreen": True,
    "bgColour": [0, 0, 0],     
    "units": "pix",
    "screen" : 1,   # display monitor
}

GEOMETRY = {
    "ringRadius": 255,               # ring radius 
    "objCount": 8,  
    "objSize_px": 120,
    "centralDotRadius_px": 5,        # center fixation dot radius
    "objSelectRadius_px": 100,       # radius for an object for selection 
    "feedbackCircleRadius_px": 68,   # circle around an object, in feedback
    "feedbackWrongMark": "o",        # mark on a wrong choice: "x" or "o"
    "feedbackNameOffset_px": 80,     # object centre to name centre, in feedback
    "feedbackNameHeight_px": 24,     # letter height of the name, in feedback
    "ringRotation": 0,               # degrees, or "random" for a new rotation each trial
}

TIMING = {
    "previewDurRange": (0.6, 1.0),    # random from this range to prevent anticipation
    "feedbackDur": 2.0,
    "iti": 1.0,
    "responseTimeout_s": 5.0,         # no selection by then -> trial ends as a timeout
}

# COUNTERBALANCING

# The context (objects x attributes) is in context.py, not here.

# Which visual feature stands for each attribute, and what 0 and 1 mean.
# Keys must be m0, m1, ... in column order of CONTEXT. Counterbalance by
# changing which feature each attribute gets. 1 always = feature present.
# PLACEHOLDER features, from the octagon illustration.
ATTRIBUTES = {
    "m0": {"feature": "fill", 1: "orange", 0: "gray"},
    "m1": {"feature": "disk", 1: "disk", 0: "none"},
    "m2": {"feature": "stripes", 1: "stripes", 0: "none"},
    "m3": {"feature": "dots", 1: "dots", 0: "none"},
    "m4": {"feature": "outline", 1: "thick", 0: "none"},
    "m5": {"feature": "notch", 1: "notch", 0: "none"},
}

# PLACEHOLDER: g5-g7 names are temporary, not yet matched to the others.
NAMES = {
    "g0": "Guli",
    "g1": "Domu",
    "g2": "Vemi",
    "g3": "Zudo",
    "g4": "Tora",
    "g5": "Kesa",
    "g6": "Pino",
    "g7": "Ruba",
}

# Where each object sits on the ring. Edit before each session.
ORDER = {
    # Slot 1 is at 3 o'clock (before ringRotation); later slots go
    # counter-clockwise. Each object exactly once.
    "ringOrder": ["g0", "g1", "g2", "g3", "g4", "g5", "g6", "g7"],
}

# Trial order: an Euler tour over the objects (design.trial_sequence), so
# every transition i -> j between consecutive trials appears equally often.
# A new random seed (1-9999) each session; it is saved in the data file.
EULER_TOUR = {
    "stay_trial": False,    # allow i -> i (same object twice in a row)
    "tour_repeats": 1,      # full tours joined end to end; each i -> j
                            # appears this many times. 8 objects, no stay:
                            # 56 transitions per tour, so 56 * repeats + 1 trials
}



from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent

PATHS = {
    "stimDir": PROJECT_DIR / "stimObj",
    "dataDir": PROJECT_DIR / "data",
}

# Fixed feature order of the digits in the image file names, as
# stimuli.py writes them. 1 = present. E.g. 110000.png = fill + disk.
# Does not change with counterbalancing.
IMAGE_NAME_ORDER = ["fill", "disk", "stripes", "dots", "outline", "notch"]

CALIBRATION = {
# matched CRS LiveTrack calibrate.py 2026-09-14
    "viewDist_mm": 850, 
    "screenSize_mm": [400, 300],
    "targets_deg": [
        [-9.5,-9.5],[0,-9.5],[9.5,-9.5],
        [-9.5,0],[0,0],[9.5,0],
        [-9.5,9.5],[0,9.5],[9.5,9.5]
        ],
    "setupDelay_ms": 1200.0,
    "minFixDur_ms": 1200,
    "fixTimeout_s": 5,
    "fixThreshold_px": 3.1,
    "fixInDot_deg": 0.3,
    "fixOutDot_deg": 0.6,
    "calibrationCriterion_deg": 0.5, # < 0.5 degree error
}

# Gaze dwell selection
DWELL_SELECTION = {
    "dwell_ms": 1000,           # how long gaze must hold to select
    "dwellRadius_deg": 1.5,     # remain within 1.5 deg radius from that fixation
    "blinkTimeout_ms": 300,   # if blinks > 300 ms, then restart.
}

# Central fixation criterion for cue presentation.
CENTRAL_FIXATION = {
    "centralHold_ms": 2000,      # how long gaze must stay inside the radius
    "centralRadius_deg": 1.25,   # distance from screen centre that counts as on the dot
    "centralTimeout_s": 20,      # give up and abort the session
}
