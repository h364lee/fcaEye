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
    "target_tolerance_px": 100,   # must stay well under half the gap between
                                  # adjacent objects -- see geometry.check_tolerance
}

TIMING = {
    "preview_range": (0.6, 1.0),  # jittered, so cue onset cannot be anticipated
    "feedback_dur": 0.8,
    "iti": 1.0,
    "dwell_ms": 400,
}

PHASES = {
    "demo": {"responder": "click", "feedback": True, "timeout": 5.0},
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
    "setup_delay_ms": 1000.0,
    "min_fix_dur_ms": 1200,
    "fix_timeout_s": 5,
    "fix_threshold_px": 3.1,
    "fix_dot_in_deg": 0.3,
    "fix_dot_out_deg": 0.6,
    "accuracy_threshold_deg": 0.5, # good calibration criterion < 0.5 degree error
}