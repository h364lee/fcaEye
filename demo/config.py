"""
Parameter file.
All variables should live here.
"""
DISPLAY = {
    "size": [1200, 900],
    "fullscreen": False,
    "background": [0, 0, 0],      # PsychoPy rgb space: this is mid grey, not black
    "units": "pix",
}

GEOMETRY = {
    "ring_radius": 350,
    "n_positions": 5,
    "object_px": 140,
    "fixation_px": 20,            # diameter
    "target_tolerance_px": 100,   # must stay well under half the gap between
                                  # adjacent objects -- see geometry.check_tolerance
}

TIMING = {
    "preview_range": (0.6, 1.0),  # jittered, so cue onset cannot be anticipated
    "feedback_dur": 0.8,
    "iti": 1.0,
    "dwell_ms": 400,
}

# What makes one phase differ from another. Trial code reads this instead of
# branching on a phase name.
PHASES = {
    "demo": {"responder": "click", "feedback": True, "timeout": 5.0},
}

NAMES = {"g1": "Bala", "g2": "Kopo", "g3": "Vemi", "g4": "Zudo", "g5": "Tora"}


from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent

PATHS = {
    "stim_dir": PROJECT_DIR / "stims",
}
