"""Trial data file: one row per trial, with the session values repeated on
every row, so that one file is enough for analysis.

The file sits next to the tracker's file and shares its name:
    data/<id>_<date>_<time>.csv          tracker samples and event markers
    data/<id>_<date>_<time>_trials.csv   this file

Column order: participant, session, mappings, trial, event times, settings.

Each row is written and flushed as soon as its trial ends, so a crash loses
at most the trial that was running.
"""

import csv

import config
import design
from config import NAMES

# Settings groups copied into the file, one column per key, as "GROUP.key".
SETTINGS = ["DISPLAY", "GEOMETRY", "TIMING", "DWELL_SELECTION",
            "CENTRAL_FIXATION", "CALIBRATION"]

# Marker name -> column holding the PsychoPy time (s) the marker was written.
EVENT_TIMES = {
    "dot_on": "dotOn_s",
    "fixation_held": "fixationHeld_s",
    "objects_on": "objectsOn_s",
    "name_on": "nameOn_s",
    "selection": "response_s",
    "timeout": "response_s",
    "feedback_on": "feedbackOn_s",
    "blank_on": "blankOn_s",
}

_file = None
_writer = None
_settings = None


def session_columns(participant, accuracy, session_start, screen_rate,
                    tracker_rate, tracked_eyes, ring_order):
    """Everything that is the same for every trial, except the settings."""
    columns = dict(participant)
    columns.update({
        "sessionStart": session_start,
        "screenRate_Hz": screen_rate,
        "trackerRate_Hz": tracker_rate,
        "trackLeft": tracked_eyes[0],
        "trackRight": tracked_eyes[1],
        "yesCalibration": config.SESSION["yesCalibration"],
        "calibrationErrorLeft_deg": accuracy.get("left", {}).get("accuracy_deg", ""),
        "calibrationErrorRight_deg": accuracy.get("right", {}).get("accuracy_deg", ""),
    })
    for obj in NAMES:
        columns[f"{obj}Name"] = NAMES[obj]
    columns["attributes"] = design.attributes_text()
    for obj in NAMES:
        columns[f"{obj}Image"] = design.image_code(obj)
    columns["ringOrder"] = "|".join(ring_order)
    return columns


def settings_columns():
    """Every key of the SETTINGS groups in config, as "GROUP.key"."""
    columns = {}
    for group in SETTINGS:
        for key, value in getattr(config, group).items():
            columns[f"{group}.{key}"] = value
    return columns


def trial_column_names():
    """Column names of the dict run_trial returns, in file order."""
    names = ["trialN", "targetObj", "name", "targetImage", "rotation_deg"]
    for obj in NAMES:
        names += [f"{obj}X", f"{obj}Y"]
    names += ["previewDur_s", "selected", "outcome", "selection_ms",
              "firstMove_ms"]
    names += list(dict.fromkeys(EVENT_TIMES.values()))   # unique, in order
    return names


def open_file(tracker_path, session):
    """Create the trial file next to the tracker file and write the header."""
    global _file, _writer, _settings
    _settings = settings_columns()
    path = tracker_path.with_name(tracker_path.stem + "_trials.csv")
    _file = open(path, "w", newline="", encoding="utf-8")
    # A key that is not in fieldnames raises an error on the first row,
    # so a misspelled column is found at once, not during analysis.
    fieldnames = list(session) + trial_column_names() + list(_settings)
    _writer = csv.DictWriter(_file, fieldnames=fieldnames)
    _writer.writeheader()
    _file.flush()
    return path


def write_row(session, trial):
    """Write one trial with the session values and settings; save it now."""
    _writer.writerow({**session, **trial, **_settings})
    _file.flush()


def close_file():
    """Safe to call if the file was never opened."""
    global _file, _writer
    if _file is not None:
        _file.close()
    _file = None
    _writer = None
