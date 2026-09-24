"""Trial data file: one row per trial, with the session values repeated on
every row, so that one file is enough for analysis.

The file sits next to the tracker's file and shares its name:
    data/<id>_<date>_<time>.csv          tracker samples and event markers
    data/<id>_<date>_<time>_trials.csv   this file

Each row is written and flushed as soon as its trial ends, so a crash loses
at most the trial that was running.
"""

import csv
import subprocess

import psychopy

import config
from config import NAMES, OBJECTS, PROJECT_DIR

# Settings groups copied into the file, one column per key, as "GROUP.key".
SETTINGS = ["DISPLAY", "GEOMETRY", "TIMING", "DWELL_SELECTION",
            "CENTRAL_FIXATION", "CALIBRATION"]

# Marker name -> column holding the PsychoPy time (s) the marker was written.
EVENT_TIMES = {
    "dot_on": "dotOn_s",
    "fixation_held": "fixationHeld_s",
    "objects_on": "objectsOn_s",
    "cue_on": "cueOn_s",
    "selection": "response_s",
    "timeout": "response_s",
    "feedback_on": "feedbackOn_s",
    "blank_on": "blankOn_s",
}

_file = None
_writer = None


def code_version():
    """Git commit of the code that is running, e.g. "caa100a".

    "+uncommitted" is added when files differ from that commit, because then
    the commit alone does not describe the code that ran.
    """
    def git(*args):
        return subprocess.run(["git", *args], cwd=PROJECT_DIR, check=True,
                              capture_output=True, text=True).stdout.strip()
    try:
        commit = git("rev-parse", "--short", "HEAD")
        changed = git("status", "--porcelain")
    except (OSError, subprocess.CalledProcessError):
        return "unknown"
    return commit + ("+uncommitted" if changed else "")


def session_columns(participant, accuracy, tracker_path, session_start,
                    refresh_rate, tracker_rate, tracked_eyes, ring_order):
    """Everything that is the same for every trial of the session."""
    columns = dict(participant)
    columns.update({
        "sessionStart": session_start,
        "trackerFile": tracker_path.name,
        "codeVersion": code_version(),
        "psychopyVersion": psychopy.__version__,
        "refreshRate_Hz": refresh_rate,
        "trackerRate_Hz": tracker_rate,
        "trackLeft": tracked_eyes[0],
        "trackRight": tracked_eyes[1],
        "yesCalibration": config.SESSION["yesCalibration"],
    })
    for eye in ("left", "right"):
        entry = accuracy.get(eye, {})
        columns[f"cal_{eye}_deg"] = entry.get("accuracy_deg", "")
        columns[f"cal_{eye}_points"] = entry.get("n_points", "")

    for obj in NAMES:
        columns[f"{obj}Name"] = NAMES[obj]
        columns[f"{obj}Image"] = OBJECTS[obj]
    columns["ringOrder"] = "|".join(ring_order)

    for group in SETTINGS:
        for key, value in getattr(config, group).items():
            columns[f"{group}.{key}"] = value
    return columns


def trial_column_names():
    """Column names of the dict run_trial returns, in file order."""
    names = ["trialN", "target", "name", "targetImage", "rotation_deg"]
    for obj in NAMES:
        names += [f"{obj}X", f"{obj}Y"]
    names += ["previewDur_s", "selection", "outcome", "selection_ms",
              "firstMove_ms"]
    names += list(dict.fromkeys(EVENT_TIMES.values()))   # unique, in order
    return names


def open_file(tracker_path, session):
    """Create the trial file next to the tracker file and write the header."""
    global _file, _writer
    path = tracker_path.with_name(tracker_path.stem + "_trials.csv")
    _file = open(path, "w", newline="", encoding="utf-8")
    # A key that is not in fieldnames raises an error on the first row,
    # so a misspelled column is found at once, not during analysis.
    _writer = csv.DictWriter(_file, fieldnames=list(session) + trial_column_names())
    _writer.writeheader()
    _file.flush()
    return path


def write_row(session, trial):
    """Write one trial, with the session values, and push it to disk now."""
    _writer.writerow({**session, **trial})
    _file.flush()


def close_file():
    """Safe to call if the file was never opened."""
    global _file, _writer
    if _file is not None:
        _file.close()
    _file = None
    _writer = None
