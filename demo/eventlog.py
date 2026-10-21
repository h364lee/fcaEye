"""Event markers in the tracker data file, one per comment:
    event=object_on trial=3
"""

import contextlib
import io
import sys
import time
from datetime import datetime

sys.path.insert(0, r"C:\Users\Public\Documents\CRS LiveTrack Python Bindings")
import LiveTrack

from config import PATHS

_open = False
_last_sent = 0.0

# The tracker holds one comment and writes it on its next sample (every
# 2 ms). A second comment sent before that sample replaces the first, and
# the call still reports success. So markers are kept this far apart.
# Trial markers have a screen flip between them, so only markers sent back
# to back are delayed.
MIN_GAP_S = 0.004


def open_session(participant_id):
    """Start writing tracker data to data/<id>_<YYYYmmdd_HHMMSS>.csv.

    Call before StartTracking() (the order CRS's demos use). Returns the path.
    """
    global _open
    data_dir = PATHS['dataDir']
    data_dir.mkdir(parents=True, exist_ok=True)

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = data_dir / f"{participant_id}_{stamp}.csv"

    if LiveTrack.SetDataFilename(str(path)) != 0:
        raise RuntimeError(f"LiveTrack could not open {path}")
    _open = True
    return path


def tracker_time_us():
    """Tracker timestamp (us) of the newest sample that has reached the PC.

    Gives a screen change's tracker time without a marker. It trails the
    true moment by the transfer delay; merge.py measures that delay
    against the marker's sample.
    """
    return LiveTrack.GetLastResult().Timestamp


def mark(event, **fields):
    """Write one event marker. No-op if no session is open.

    Commas are refused: the comment is one CSV column, and a comma would
    split it in two.
    """
    if not _open:
        return

    parts = [f"event={event}"] + [f"{k}={v}" for k, v in fields.items()]
    text = " ".join(parts)
    if "," in text:
        raise ValueError(f"comma in event marker: {text!r}")

    # Busy-wait rather than sleep: on Windows, sleep can overshoot by
    # several milliseconds.
    global _last_sent
    while time.perf_counter() - _last_sent < MIN_GAP_S:
        pass

    # The binding prints a success line on every call, which hides real
    # messages. Silence it and check the result instead.
    with contextlib.redirect_stdout(io.StringIO()):
        result = LiveTrack.SetDataComment(text)
    _last_sent = time.perf_counter()
    if result != 0:
        print(f"WARNING: event marker not written: {text}")


def close_session():
    """Stop writing tracker data. Safe to call if no session is open."""
    global _open
    if not _open:
        return

    # A comment lands on the next sample. Wait so the last marker is written.
    time.sleep(0.05)
    LiveTrack.CloseDataFile()
    _open = False
