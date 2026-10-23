"""TEMPORARY test script: runs experiment.py with a fake tracker; mouse = gaze.

Delete when done. Run from the demo folder:  python run_without_tracker.py
"""

import sys
import time
import types

# Fake LiveTrack module. It must be in sys.modules before experiment is
# imported, so every `import LiveTrack` in the project gets it.
fake = types.ModuleType("LiveTrack")
_start = time.perf_counter()
_marker_file = None
_mouse = None


class _Sample:
    """Fake sample with the fields the project reads (both eyes = mouse)."""

    def __init__(self, x, y, timestamp=None):
        self.Tracked = self.TrackedRight = True
        self.GazeX = self.GazeXRight = x
        self.GazeY = self.GazeYRight = y
        # microseconds, like the tracker clock
        if timestamp is None:
            timestamp = int((time.perf_counter() - _start) * 1e6)
        self.Timestamp = timestamp


def _mouse_sample():
    # Mouse is created on first use: it needs the window (presentation._pres).
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
_last_us = None


def _buffered(*args):
    """Every 2-ms sample since the last read, like the real buffer."""
    global _last_us
    now = _mouse_sample()
    if _last_us is None or now.Timestamp - _last_us > 2_000_000:
        _last_us = now.Timestamp - 2000      # keep at most about 2 s
    samples = []
    while _last_us + 2000 <= now.Timestamp:
        _last_us += 2000
        samples.append(_Sample(now.GazeX, now.GazeY, _last_us))
    return samples


fake.GetBufferedEyePositions = _buffered


def _set_data_filename(path):
    # No tracker file; event markers go to a text file for checking.
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

# Laptop settings. The config dicts are shared, so changes apply everywhere.
import config

config.DISPLAY["screen"] = 0              # the laptop has one screen
config.DISPLAY["fullscreen"] = False      # keep the terminal visible
# Subfolder, so merge.py (reads data/ only) never picks up test files
config.PATHS["dataDir"] = config.PROJECT_DIR / "data" / "no_tracker"

import calibrate
import presentation


def _fake_calibration(win):
    print("(no tracker: calibration skipped, reported as perfect)")
    return {"left": {"accuracy_deg": 0.0, "n_points": 0},
            "right": {"accuracy_deg": 0.0, "n_points": 0}}


calibrate.gaze_calibration = _fake_calibration
# park_mouse normally hides the cursor; here the cursor is the gaze.
presentation.Presentation.park_mouse = lambda self: None

import experiment

print("NO TRACKER: the mouse stands in for gaze.")
experiment.main()
