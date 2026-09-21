"""Event markers in the data file.

Comment format, one event per comment:
    event=cue_on trial=3 target=g2
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


def open_session(participant_id):
    """Start writing tracker data to data/<id>_<YYYYmmdd_HHMMSS>.csv.

    Call before StartTracking(), the order CRS's demos use.

    Returns:
        the file path.
    """
    global _open
    data_dir = PATHS['data_dir']
    data_dir.mkdir(parents=True, exist_ok=True)

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = data_dir / f"{participant_id}_{stamp}.csv"

    if LiveTrack.SetDataFilename(str(path)) != 0:
        raise RuntimeError(f"LiveTrack could not open {path}")
    _open = True
    return path


def mark(event, **fields):
    """Write one event marker. Does nothing if no session is open.

    Fields become key=value pairs after the event name.

    Commas are refused: the comment goes into one CSV column, and a comma
    would split it across two.
    """
    if not _open:
        return

    parts = [f"event={event}"] + [f"{k}={v}" for k, v in fields.items()]
    text = " ".join(parts)
    if "," in text:
        raise ValueError(f"comma in event marker: {text!r}")

    # The binding prints a success line on every call; at eight events a
    # trial that buries real messages. Silence it and check the result.
    with contextlib.redirect_stdout(io.StringIO()):
        result = LiveTrack.SetDataComment(text)
    if result != 0:
        print(f"WARNING: event marker not written: {text}")


def close_session():
    """Stop writing tracker data. Safe to call if no session is open."""
    global _open
    if not _open:
        return

    # A comment attaches to the *next* sample. Wait a few samples so the
    # final marker is not lost when the file closes.
    time.sleep(0.05)
    LiveTrack.CloseDataFile()
    _open = False
