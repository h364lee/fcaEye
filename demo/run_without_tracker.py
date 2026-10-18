"""TEMPORARY: run experiment.py without the eye tracker. Delete when done.

The mouse position stands in for gaze: hold the mouse on the dot to pass
the fixation check, and hold it on a name to select it.

How it works: experiment.py, response.py, eventlog.py and calibrate.py all
do `import LiveTrack`. Python checks sys.modules before it searches for a
module, so putting a stand-in module there first makes every one of those
imports get the stand-in. No project file is changed.

Run from the demo folder:  python run_without_tracker.py
"""

import sys
import time
import types

# --- 1. stand-in LiveTrack module ---------------------------------------
# Must be in sys.modules before experiment is imported.
fake = types.ModuleType("LiveTrack")
_start = time.perf_counter()
_marker_file = None
_mouse = None


class _Sample:
    """One reading, with the fields the project reads from real samples."""

    def __init__(self, x, y):
        self.Tracked = True
        self.GazeX = x
        self.GazeY = y
        # tracker clock in microseconds
        self.Timestamp = int((time.perf_counter() - _start) * 1e6)


def _mouse_sample():
    # Created on first use, because the window must exist first.
    # presentation._pres is set when the window opens.
    global _mouse
    if _mouse is None:
        import presentation
        from psychopy import event
        _mouse = event.Mouse(win=presentation._pres.win, visible=True)
    x, y = _mouse.getPos()          # window units: pixels, centre at 0,0
    return _Sample(float(x), float(y))


def _do_nothing(*args, **kwargs):
    return 0


for name in ("Init", "Close", "StartTracking", "StopTracking",
             "SetResultsTypeRaw", "SetResultsTypeCalibrated",
             "ClearDataBuffer"):
    setattr(fake, name, _do_nothing)

fake.GetCaptureConfig = lambda: (0, 0, 500, 0, 0)   # [2] = sample rate
fake.GetTracking = lambda: (True, True)             # (left, right)
fake.GetLastResult = _mouse_sample
fake.GetBufferedEyePositions = lambda *args: [_mouse_sample()]


def _set_data_filename(path):
    # No tracker file. The markers go to a text file instead, so you can
    # check that each event is marked where you expect.
    global _marker_file
    _marker_file = open(str(path).replace(".csv", "_markers.txt"), "w")
    return 0


def _set_data_comment(text):
    t = time.perf_counter() - _start
    _marker_file.write(f"{t:10.3f}  {text}\n")
    _marker_file.flush()
    return 0


def _close_data_file():
    if _marker_file is not None:
        _marker_file.close()


fake.SetDataFilename = _set_data_filename
fake.SetDataComment = _set_data_comment
fake.CloseDataFile = _close_data_file
sys.modules["LiveTrack"] = fake

# --- 2. settings for running on the laptop ------------------------------
# These dicts are shared with every module that imported them, so changing
# them here changes them everywhere.
import config

config.DISPLAY["screen"] = 0              # the laptop has one screen
config.DISPLAY["fullscreen"] = False      # keep the terminal visible
# Separate folder, so test files never mix with real data.
# merge.py only looks directly inside data/, not in subfolders.
config.PATHS["dataDir"] = config.PROJECT_DIR / "data" / "no_tracker"

# --- 3. calibration and the cursor --------------------------------------
import calibrate
import presentation


def _fake_calibration(win):
    print("(no tracker: calibration skipped, reported as perfect)")
    return {"left": {"accuracy_deg": 0.0, "n_points": 0},
            "right": {"accuracy_deg": 0.0, "n_points": 0}}


calibrate.gaze_calibration = _fake_calibration
# park_mouse normally hides the cursor; here the cursor is the gaze.
presentation.Presentation.park_mouse = lambda self: None

# --- 4. run -------------------------------------------------------------
import experiment

print("NO TRACKER: the mouse stands in for gaze.")
experiment.main()
