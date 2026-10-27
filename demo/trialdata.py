# AI usage: code co-written with Claude Opus 5.5.
# Research questions, experimental design and program requirements came from Caleb and Britt.

"""Session and trial data files.

    data/<name>/<name>.csv                tracker samples and markers
                                          (LiveTrack, eventlog.py)
    data/<name>/<name>_session.csv        one row of session-wide values
    data/<name>/<name>_trials.csv         one row per trial
name = <id>_<date> (YYYYmmdd; a second session that day adds _2, _3 ...)

Join on participantID. The session file is written after recording starts.
Each trial row is saved when its trial ends, so a crash loses at most the
running trial.
"""

import csv
import platform
from importlib.metadata import version

import config
import design
from config import NAMES, OBJECT_SETS

# Config groups copied to the session file as "GROUP.key" columns.
SETTINGS = ["DISPLAY", "GEOMETRY", "TIMING", "ORDER", "EULER_TOUR", "PHASES",
            "COUNTERBALANCE", "DEMO_TRIALS",
            "DWELL_SELECTION", "CENTRAL_FIXATION", "GAZE_STATE",
            "CALIBRATION"]

# Marker name -> column holding the PsychoPy time (ms) the marker was written.
EVENT_TIMES = {
    "dot_on": "dotOn_ms",
    "fixation_held": "fixationHeld_ms",
    "names_on": "namesOn_ms",
    "object_on": "objectOn_ms",
    "selection": "response_ms",
    "timeout": "response_ms",
    "feedback_on": "feedbackOn_ms",
    "blank_on": "blankOn_ms",
}


def tracker_column(column):
    """Tracker-clock column of an event: "objectOn_ms" -> "objectOnTracker_us"."""
    return column.removesuffix("_ms") + "Tracker_us"

_file = None
_writer = None
_participant_id = None


def session_columns(participant, accuracy, screen_rate,
                    tracker_rate, tracked_eyes, stim_sets,
                    calibration_attempts):
    """Session-wide values, except the config settings.

    Each design.StimulusSet in stim_sets gets its own columns, e.g.
    "phase1_context", "phase1_g0Name".
    """
    columns = dict(participant)
    columns.update({
        "groupCell": config.COUNTERBALANCE["groupCell"],
        "phase2Relation": design.phase2_relation(),     # isom or shift
    })
    columns.update({
        # To trace version differences later
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
    # phase: practice, learning1, test1 (learning2, test2 are off for now)
    # attempt: 2+ if the block was abandoned and run again; keep the last.
    # blockSeed: rebuilds the trial order (design.shuffled_sequence for
    #   practice and learning, design.trial_sequence for test)
    names = ["phase", "block", "attempt", "stimSet", "blockSeed", "feedback",
             "trialN", "targetObj", "previousObj", "name", "targetImage",
             "rotation_deg"]
    for obj in NAMES:
        names += [f"{obj}X", f"{obj}Y"]
    names += ["previewDur_ms", "selected", "outcome", "selection_ms",
              "firstMove_ms"]
    event_columns = list(dict.fromkeys(EVENT_TIMES.values()))   # unique, in order
    names += event_columns
    names += [tracker_column(c) for c in event_columns]
    return names


# Post-task answers: columns of the session file, empty until answered.
POSTTASK_COLUMNS = ["q1Pattern", "q2Strategy", "q3Features", "q4Difficulty"]

_session_path = None
_session_row = None


def _write_session():
    with open(_session_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(_session_row))
        writer.writeheader()
        writer.writerow(_session_row)     # None is written as an empty cell


def open_files(tracker_path, participant_id, session):
    """Write the session file and open the trial file next to the tracker
    file. Returns (session_path, trials_path).

    Session file columns: participantID, session, the post-task answers
    (empty until update_session), then "GROUP.key" settings.
    """
    global _file, _writer, _participant_id, _session_path, _session_row
    _participant_id = participant_id

    _session_path = tracker_path.with_name(tracker_path.stem + "_session.csv")
    _session_row = {"participantID": participant_id, **session,
                    **{column: None for column in POSTTASK_COLUMNS},
                    **settings_columns()}
    _write_session()
    session_path = _session_path

    trials_path = tracker_path.with_name(tracker_path.stem + "_trials.csv")
    _file = open(trials_path, "w", newline="", encoding="utf-8")
    # An unknown key raises an error on the first row, so a misspelled
    # column is found at once, not during analysis.
    _writer = csv.DictWriter(_file,
                             fieldnames=["participantID"] + trial_column_names())
    _writer.writeheader()
    _file.flush()
    return session_path, trials_path


def update_session(values):
    """Fill in session-file columns (e.g. the post-task answers); return its path.

    The file is written again whole: it is one row, so this is quick, and
    the file is complete at every moment.
    """
    unknown = set(values) - set(_session_row)
    if unknown:
        raise KeyError(f"not session-file columns: {sorted(unknown)}")
    _session_row.update(values)
    _write_session()
    return _session_path


def write_row(trial):
    """Write one trial row and flush it to disk."""
    _writer.writerow({"participantID": _participant_id, **trial})
    _file.flush()


def close_file():
    """Close the trial file. Safe if it was never opened."""
    global _file, _writer
    if _file is not None:
        _file.close()
    _file = None
    _writer = None
