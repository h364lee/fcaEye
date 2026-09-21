"""
Keep all variables here - 2026-09-12
"""
DISPLAY = {
    "size": [1024, 768],
    "fullscreen": True,
    "background": [0, 0, 0],     
    "units": "pix",
    "screen" : 1,
}

GEOMETRY = {
    "ring_radius": 300,
    "n_positions": 5,
    "object_px": 120,
    "fixation_px": 20,            # diameter
    "target_tolerance_px": 100,   # radius for an object (for selection) 
    "random_rotation": False,
}

TIMING = {
    "preview_range": (0.6, 1.0),  # random so cue onset cant be anticipated
    "feedback_dur": 0.8,
    "iti": 1.0,
}

PHASES = {
    "demo": {"responder": "gaze_dwell", "feedback": True, "timeout": 5.0},
}

NAMES = {"g1": "Bala", "g2": "Kopo", "g3": "Vemi", "g4": "Zudo", "g5": "Tora"}


from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent

PATHS = {
    "stim_dir": PROJECT_DIR / "stimObjects" / "stims",
    "data_dir": PROJECT_DIR / "data",
}

CALIBRATION = {
# matched CRS LiveTrack calibrate.py 2026-09-14
    "view_dist_mm": 850, 
    "screen_size_mm": [400, 300],
    "targets_deg": [
        [-9.5,-9.5],[0,-9.5],[9.5,-9.5],
        [-9.5,0],[0,0],[9.5,0],
        [-9.5,9.5],[0,9.5],[9.5,9.5]
        ],
    "setup_delay_ms": 1200.0,
    "min_fix_dur_ms": 1200,
    "fix_timeout_s": 5,
    "fix_threshold_px": 3.1,
    "fix_dot_in_deg": 0.3,
    "fix_dot_out_deg": 0.6,
    "accuracy_threshold_deg": 0.5, # good calibration: < 0.5 degree error
}

# Gaze dwell selection. Pilot values, 2026-09-17.
GAZE_DWELL = {
    "dwell_ms": 1000,         # how long gaze must hold to select
    "stability_deg": 1.5,     # has to remain within 1.5 radius from that fixation
    "blink_gap_ms": 300,      # blinks must be less than 300 ms or else restart.
}

# Central fixation gate. The cue does not appear until the participant has
# held gaze near the dot. Pilot values, 2026-09-17.
FIXATION_GATE = {
    "hold_ms": 2000,          # gaze must stay inside the radius this long
    "radius_deg": 2.5,        # distance from screen centre that counts as on the dot
    "timeout_s": 20,          # give up and abort the session
}
