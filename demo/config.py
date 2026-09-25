"""
Keep all variables here - 2026-09-12
"""
SESSION = {
    "yesDemographics": True,     # False: skip the questions, ID becomes "debug"
    "yesCalibration": True,      # False: use the calibration stored in the tracker
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
    "objCount": 5,  
    "objSize_px": 120,
    "centralDotRadius_px": 5,        # center fixation dot radius
    "objSelectRadius_px": 100,       # radius for an object for selection 
    "feedbackCircleRadius_px": 68,   # circle around an object, in feedback
    "feedbackNameOffset_px": 80,    # object centre to name centre, in feedback
    "feedbackNameHeight_px": 24,     # letter height of the name, in feedback
    "randomRotation": False,
}

TIMING = {
    "previewDurRange": (0.6, 1.0),    # random from this range to prevent anticipation
    "feedbackDur": 1.5,
    "iti": 1.0,
    "responseTimeout_s": 5.0,         # no selection by then -> trial ends as a timeout
}

# ======================================================================
# COUNTERBALANCING -- change values here only.
# The image each object shows is worked out from CONTEXT and ATTRIBUTES
# (design.py), so it is never typed by hand.
# ======================================================================

# Formal context: which attributes (m1 m2 m3) each object has.
# Provisional: these rows reproduce the five images used so far.
CONTEXT = {
    "g1": [1, 1, 0],
    "g2": [1, 1, 1],
    "g3": [1, 0, 0],
    "g4": [1, 0, 1],
    "g5": [0, 1, 0],
}

# Which visual feature stands for each attribute, and which of its levels
# means the object has the attribute (1) or does not (0).
ATTRIBUTES = {
    "m1": {"feature": "size", 1: "big", 0: "small"},
    "m2": {"feature": "colour", 1: "black", 0: "white"},
    "m3": {"feature": "shape", 1: "tri", 0: "square"},
}

# The made-up word taught for each object.
NAMES = {
    "g1": "Bala",
    "g2": "Kopo",
    "g3": "Vemi",
    "g4": "Zudo",
    "g5": "Tora",
}

# ======================================================================


from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent

PATHS = {
    "stimDir": PROJECT_DIR / "stimObj",
    "dataDir": PROJECT_DIR / "data",
}

# Order of the feature words in the image file names, as objectGen.py
# writes them: <size>_<colour>_<shape>.png
IMAGE_NAME_ORDER = ["size", "colour", "shape"]

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
