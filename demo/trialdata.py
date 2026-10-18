"""Trial data file
    data/<id>_<date>_<time>.csv          tracker samples and event markers
    data/<id>_<date>_<time>_trials.csv   this file

Column order: participant, session, mappings, trial, event times, settings.

Each row is written as soon as its trial ends, so a crash loses
at most the trial that was running.
"""

import csv
import platform
from importlib.metadata import version

import config
import design
from config import NAMES, OBJECT_SETS

# Settings groups copied into the file, one column per key, as "GROUP.key".
SETTINGS = ["DISPLAY", "GEOMETRY", "TIMING", "ORDER", "EULER_TOUR", "PHASES",
            "COUNTERBALANCE", "DEMO_TRIALS",
            "DWELL_SELECTION", "CENTRAL_FIXATION", "CALIBRATION"]

# Marker name -> column holding the PsychoPy time (s) the marker was written.
EVENT_TIMES = {
    "dot_on": "dotOn_s",
    "fixation_held": "fixationHeld_s",
    "names_on": "namesOn_s",
    "object_on": "objectOn_s",
    "selection": "response_s",
    "timeout": "response_s",
    "feedback_on": "feedbackOn_s",
    "blank_on": "blankOn_s",
}


def tracker_column(column):
    """Tracker-clock of an event column: "objectOn_s" -> "objectOnTracker_us"."""
    return column.removesuffix("_s") + "Tracker_us"

_file = None
_writer = None
_settings = None


def session_columns(participant, accuracy, session_start, screen_rate,
                    tracker_rate, tracked_eyes, stim_sets,
                    calibration_attempts):
    """Everything that is the same for every trial, except the settings.

    stim_sets: the design.StimulusSets this session uses. Each gets its
    own columns, e.g. "phase1_context", "phase1_g0Name".
    """
    columns = dict(participant)
    columns.update({
        "groupCell": config.COUNTERBALANCE["groupCell"],
        "phase2Relation": design.phase2_relation(),     # isom or shift
    })
    columns.update({
        "sessionStart": session_start,
        # Software that ran this session, to trace version differences later
        "pythonVersion": platform.python_version(),
        "psychopyVersion": version("psychopy"),
        "os": platform.platform(),
        "screenRate_Hz": screen_rate,
        "trackerRate_Hz": tracker_rate,
        "trackLeft": tracked_eyes[0],
        "trackRight": tracked_eyes[1],
        "yesCalibration": config.SESSION["yesCalibration"],
        "calibrationAttempts": calibration_attempts,
        "calibrationErrorLeft_deg": accuracy.get("left", {}).get("accuracy_deg", ""),
        "calibrationErrorRight_deg": accuracy.get("right", {}).get("accuracy_deg", ""),
    })
    for stim_set in stim_sets:
        label = stim_set.label
        if stim_set.context is not None:
            columns[f"{label}_context"] = stim_set.context_label
            columns[f"{label}_objectSet"] = stim_set.object_set
            columns[f"{label}_attributes"] = design.attributes_text(
                OBJECT_SETS[stim_set.object_set]["attributes"])
        for obj in stim_set.objects:
            columns[f"{label}_{obj}Name"] = stim_set.names[obj]
        if stim_set.context is not None:
            for obj in stim_set.objects:
                columns[f"{label}_{obj}Image"] = stim_set.image_code(obj)
        columns[f"{label}_ringOrder"] = "|".join(stim_set.ring_order)
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
    # phase: practice, learning1, test1, learning2, test2
    # stimSet: practice, phase1 or phase2 (the design table's phases)
    # attempt: 1, or 2+ if the block was abandoned (pause screen) and run
    #   again; keep the last attempt of each block.
    # blockSeed: rebuilds the block's trial order (design.shuffled_sequence
    #   for practice and learning, design.trial_sequence for test)
    names = ["phase", "block", "attempt", "stimSet", "blockSeed", "feedback",
             "trialN", "targetObj", "previousObj", "name", "targetImage",
             "rotation_deg"]
    for obj in NAMES:
        names += [f"{obj}X", f"{obj}Y"]
    names += ["previewDur_s", "selected", "outcome", "selection_ms",
              "firstMove_ms"]
    event_columns = list(dict.fromkeys(EVENT_TIMES.values()))   # unique, in order
    names += event_columns
    names += [tracker_column(c) for c in event_columns]
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
