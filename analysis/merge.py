"""Turn one session's tracker file into two analysis files.

Run by hand after a session:
    cd analysis
    python merge.py                                        # newest session in data/
    python merge.py ../data/877787_20260925_132503_trials.csv
    python merge.py 000001 877787                          # every session of these SONA IDs

Inputs, all in data/ and sharing one stem <id>_<date>_<time>:
    <stem>.csv            the LiveTrack file (one row every 2 ms, markers in Comment)
    <stem>_trials.csv     one row per completed trial
    <stem>_session.csv    one row of values that are the same for the whole session

Outputs, next to the inputs:
    <stem>_gaze.csv       one row per tracker sample (every 2 ms)
        participantID, Timestamp, psychopyTime_s,
        trialN, trialRecorded, phase, block, attempt, targetObj, previousObj,
        trialPhase, gazeX, gazeY, region

    <stem>_regions.csv    one row per visit: an unbroken stretch of samples
                          in the same region
        participantID, trialN, phase, block, attempt, trialPhase,
        region, start_s, end_s, duration_ms, samples

Terms
    sample   one row of the tracker file
    marker   text sent to the tracker; it lands in the Comment column of
             the next sample ("event=dot_on trial=3 ...")
    trial window   the samples of one trial (see assign_trials)
    region   g0..g7 (on a name), centre, other, or lost (no gaze from
             either eye)
    visit    consecutive samples in one region; a short loss of gaze
             (a blink) with the same region on both sides does not end it

The tracker file is not changed. Session-wide values are only in
<stem>_session.csv; join on participantID.
"""

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# Marker name -> trial-file column holding the PsychoPy time of that event.
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

# Markers that close an open trial window. Before blank_on, this means
# the trial was interrupted.
TRIAL_ENDERS = {
    "pause_on", "block_start", "block_end", "block_abandoned",
    "section_skipped", "trials_end", "session_end", "session_ended_early",
    "session_aborted", "recalibration_start",
}

OBJECTS = [f"g{i}" for i in range(8)]

# Seconds after blank_on + ITI to close a window that no marker closed.
# About three frames at 60 Hz.
END_GRACE_S = 0.05


# ---------------------------------------------------------------- reading

def read_tracker(path):
    """Tracker samples after the tracker's clock reset.

    About 0.4 s after recording starts, the tracker restarts its timestamps
    (also seen in CRS's demo files). Samples before the last restart are on
    a different clock, so they are dropped.
    """
    raw = pd.read_csv(path, skipinitialspace=True, dtype={"Comment": str})
    raw.columns = raw.columns.str.strip()
    raw["Comment"] = raw["Comment"].fillna("").str.strip()

    restarts = np.where(np.diff(raw["Timestamp"].to_numpy()) < 0)[0]
    dropped = 0
    if len(restarts):
        dropped = restarts[-1] + 1
        raw = raw.iloc[dropped:].reset_index(drop=True)
    return raw, dropped


def read_markers(samples):
    """Every marker as (sample index, event name, {field: value})."""
    markers = []
    for index, text in samples["Comment"].items():
        if not text.startswith("event="):
            continue
        fields = dict(part.split("=", 1) for part in text.split() if "=" in part)
        markers.append((index, fields.pop("event"), fields))
    return markers


# ---------------------------------------------------------------- trials

def assign_trials(samples, markers, trials, iti_s):
    """trialN, trialRecorded, phase ... trialPhase for every sample.

    A trial window starts at the trial's dot_on marker and ends at the
    first of:
      - the next dot_on or a TRIAL_ENDERS marker. After a complete trial
        this comes about one ITI after blank_on. Before blank_on it means
        the trial was interrupted.
      - blank_on + ITI + END_GRACE_S, if no such marker comes (e.g. the
        program stopped). The grace covers the frame or two before the
        next marker, so consecutive trials have no gap.
    Time on the pause screen and between blocks belongs to no trial.

    trialRecorded is True when the trial has a row in the trial file.
    Interrupted trials have no row; their phase, block and attempt come from
    the preceding block_start marker, and targetObj from their dot_on.

    trialPhase inside a window is the latest trial marker. Outside windows
    it is "pause" (pause_on to pause_off), "before_trials",
    "between_trials" or "after_trials".
    """
    n = len(samples)
    time_us = samples["Timestamp"].to_numpy()
    iti_us = iti_s * 1e6

    trial_n = np.full(n, -1)                      # -1 = no trial
    trial_phase = np.full(n, "", dtype=object)
    info = {}                                     # trialN -> columns

    block = {}
    previous_target = None
    open_trial = None                             # [trialN, start index, end time (us)]

    def close(end_index):
        nonlocal open_trial
        if open_trial is None:
            return
        number, start, end_us = open_trial
        stop = min(end_index, np.searchsorted(time_us, end_us, side="left"))
        trial_n[start:stop] = number
        open_trial = None

    for index, event, fields in markers:
        if event == "block_start":
            close(index)
            block = fields
            previous_target = None
        elif event in TRIAL_ENDERS:
            close(index)
        elif event == "dot_on":
            close(index)
            number = int(fields["trial"])
            open_trial = [number, index, np.inf]
            info[number] = {
                "phase": block.get("phase", ""),
                "block": block.get("block", ""),
                "attempt": block.get("attempt", ""),
                "targetObj": fields.get("target", ""),
                "previousObj": previous_target or "",
            }
            previous_target = fields.get("target")
        elif event == "blank_on" and open_trial is not None:
            open_trial[2] = time_us[index] + iti_us + END_GRACE_S * 1e6
        if "trial" in fields:
            trial_phase[index] = event
    close(n)

    # Latest trial marker, carried forward, but only inside its own window.
    marker_trial = np.full(n, -1)
    for index, event, fields in markers:
        if "trial" in fields:
            marker_trial[index] = int(fields["trial"])
    phase_series = pd.Series(trial_phase).replace("", np.nan).ffill()
    owner = pd.Series(np.where(marker_trial >= 0, marker_trial, np.nan)).ffill()
    inside = trial_n >= 0
    in_own = inside & (owner.to_numpy() == trial_n)
    labels = np.where(in_own, phase_series.to_numpy(), "")

    # Outside windows: pause, before, between or after trials.
    paused = np.zeros(n, dtype=bool)
    pause_start = None
    for index, event, _ in markers:
        if event == "pause_on":
            pause_start = index
        elif event == "pause_off" and pause_start is not None:
            paused[pause_start:index + 1] = True
            pause_start = None
    if pause_start is not None:                   # session ended on the pause screen
        paused[pause_start:] = True

    windows = np.where(inside)[0]
    first = windows[0] if len(windows) else n
    trials_end = next((i for i, e, _ in markers if e == "trials_end"), None)
    last = trials_end if trials_end is not None else (windows[-1] + 1 if len(windows) else n)
    position = np.arange(n)
    outside_label = np.where(position < first, "before_trials",
                    np.where(position >= last, "after_trials", "between_trials"))
    outside_label = np.where(paused, "pause", outside_label)
    labels = np.where(inside, labels, outside_label)

    # Trial columns: from the trial file if the trial has a row, else from markers.
    recorded = {int(t): row for t, row in zip(trials["trialN"], trials.to_dict("records"))}
    columns = {c: np.full(n, "", dtype=object)
               for c in ["phase", "block", "attempt", "targetObj", "previousObj"]}
    is_recorded = np.full(n, "", dtype=object)
    for number, from_markers in info.items():
        where = trial_n == number
        source = recorded.get(number, from_markers)
        for c in columns:
            columns[c][where] = source.get(c, "")
        is_recorded[where] = str(number in recorded)

    samples["trialN"] = pd.array(np.where(inside, trial_n, pd.NA), dtype="Int64")
    samples["trialRecorded"] = is_recorded
    for c, values in columns.items():
        samples[c] = values
    samples["trialPhase"] = labels
    interrupted = sorted(t for t in info if t not in recorded)
    return samples, interrupted


# ---------------------------------------------------------------- gaze

def gaze_point(samples):
    """Mean of the two eyes, in screen pixels from the centre.

    The tracker writes (0, 0) for an eye it lost. Such an eye is ignored;
    if both are lost the gaze point is empty (NaN).
    """
    eyes = []
    for side in ("Left", "Right"):
        x = samples[f"{side}ScreenX"].to_numpy(dtype=float)
        y = samples[f"{side}ScreenY"].to_numpy(dtype=float)
        lost = (x == 0) & (y == 0)
        eyes.append(np.where(lost, np.nan, x))
        eyes.append(np.where(lost, np.nan, y))
    # nanmean warns when both eyes are NaN; that case is meant to give NaN.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        gx = np.nanmean([eyes[0], eyes[2]], axis=0)
        gy = np.nanmean([eyes[1], eyes[3]], axis=0)
    return gx, gy


def assign_regions(samples, trials, name_radius_px, centre_radius_px):
    """Region of every sample.

    lost    no gaze from either eye
    g0..g7  within the name-selection radius of that name (only in
            recorded trials: positions come from the trial file)
    centre  within the central-fixation radius of the screen centre
    other   anywhere else
    The name and centre circles do not overlap, so each sample has one region.
    """
    gx, gy = samples["gazeX"].to_numpy(), samples["gazeY"].to_numpy()
    region = np.full(len(samples), "other", dtype=object)
    region[np.hypot(gx, gy) <= centre_radius_px] = "centre"

    trial_n = samples["trialN"].to_numpy(dtype=float, na_value=np.nan)
    for row in trials.to_dict("records"):
        where = np.where(trial_n == int(row["trialN"]))[0]
        if not len(where):
            continue
        for obj in OBJECTS:
            ox, oy = float(row[f"{obj}X"]), float(row[f"{obj}Y"])
            near = np.hypot(gx[where] - ox, gy[where] - oy) <= name_radius_px
            region[where[near]] = obj
    region[np.isnan(gx)] = "lost"
    return region


def visits(samples, blink_ms):
    """One row per visit.

    A visit never crosses a change of trialN. A run of "lost" samples
    joins the visit around it if the region is the same on both sides and
    the run lasts at most blink_ms. Longer losses are their own "lost" visit.

    start_s is the PsychoPy time of the first sample; end_s is the time of
    the next sample after the visit, so durations add up without gaps.
    """
    time_s = samples["psychopyTime_s"].to_numpy()
    step = np.median(np.diff(time_s))
    next_time = np.append(time_s[1:], time_s[-1] + step)
    region = samples["region"].to_numpy().copy()

    trial_key = samples["trialN"].astype("float").fillna(-1).to_numpy()
    part = np.concatenate([[0], np.cumsum(trial_key[1:] != trial_key[:-1])])

    # Fill short losses that sit inside one visit.
    change = np.concatenate([[True], (region[1:] != region[:-1]) | (part[1:] != part[:-1])])
    run_start = np.where(change)[0]
    run_end = np.append(run_start[1:], len(region))
    for k in range(1, len(run_start) - 1):
        s, e = run_start[k], run_end[k]
        if region[s] != "lost":
            continue
        before, after = s - 1, e
        if (part[before] == part[s] == part[after]
                and region[before] == region[after] != "lost"
                and (time_s[after] - time_s[s]) * 1000 <= blink_ms):
            region[s:e] = region[before]

    change = np.concatenate([[True], (region[1:] != region[:-1]) | (part[1:] != part[:-1])])
    starts = np.where(change)[0]
    ends = np.append(starts[1:], len(region)) - 1

    out = samples.iloc[starts][["participantID", "trialN", "phase", "block",
                                "attempt", "trialPhase"]].reset_index(drop=True)
    out["region"] = region[starts]
    out["start_s"] = time_s[starts]
    out["end_s"] = next_time[ends]
    out["duration_ms"] = (out["end_s"] - out["start_s"]) * 1000
    out["samples"] = ends - starts + 1
    return out


# ---------------------------------------------------------------- clocks

def event_pairs(samples, markers, trials, column_for):
    """(marker timestamp, trial-file value) for every trial marker of a recorded trial."""
    by_trial = {int(t): row for t, row in zip(trials["trialN"], trials.to_dict("records"))}
    pairs = []
    for index, event, fields in markers:
        if "trial" not in fields or event not in EVENT_TIMES:
            continue
        row = by_trial.get(int(fields["trial"]))
        column = column_for(EVENT_TIMES[event])
        if row is None or column not in row:
            continue
        value = pd.to_numeric(row[column], errors="coerce")
        if pd.notna(value):
            pairs.append((samples["Timestamp"].iat[index], value))
    return np.array(pairs, dtype=float).reshape(-1, 2)


def fit_clock(samples, markers, trials):
    """Straight line from tracker time (s) to PsychoPy time (s).

    Each trial event has a marker timestamp and a PsychoPy time in the
    trial file. The clocks run at slightly different speeds, so the fit
    has a rate as well as an offset.
    """
    pairs = event_pairs(samples, markers, trials, lambda c: c)
    tracker_s, psychopy_s = pairs[:, 0] / 1e6, pairs[:, 1]
    rate, offset = np.polyfit(tracker_s, psychopy_s, 1)
    residual_ms = (psychopy_s - (offset + rate * tracker_s)) * 1000
    return offset, rate, residual_ms


def check_lag(samples, markers, trials):
    """How far GetLastResult's timestamp trails the marker, per event (ms)."""
    pairs = event_pairs(samples, markers, trials,
                        lambda c: c.removesuffix("_s") + "Tracker_us")
    return (pairs[:, 0] - pairs[:, 1]) / 1000


# ---------------------------------------------------------------- main

def merge(trials_path):
    trials_path = Path(trials_path)
    stem = trials_path.name.removesuffix("_trials.csv")
    tracker_path = trials_path.with_name(stem + ".csv")
    session_path = trials_path.with_name(stem + "_session.csv")
    gaze_path = trials_path.with_name(stem + "_gaze.csv")
    regions_path = trials_path.with_name(stem + "_regions.csv")

    # Read as text so values are copied exactly as written (ID "000001").
    trials = pd.read_csv(trials_path, dtype=str, keep_default_na=False)
    if "participantID" not in trials.columns or not session_path.exists():
        sys.exit(f"{trials_path.name}: recorded before the session file existed; "
                 "not supported")
    session = pd.read_csv(session_path, dtype=str, keep_default_na=False).iloc[0]
    iti_s = float(session["TIMING.iti"])
    name_radius_px = float(session["nameSelectRadius_px"])
    centre_radius_px = (float(session["CENTRAL_FIXATION.centralRadius_deg"])
                        * float(session["px_per_deg"]))
    blink_ms = float(session["DWELL_SELECTION.blinkTimeout_ms"])
    participant = session["participantID"]

    samples, dropped = read_tracker(tracker_path)
    markers = read_markers(samples)
    samples, interrupted = assign_trials(samples, markers, trials, iti_s)

    offset, rate, residual_ms = fit_clock(samples, markers, trials)
    samples["psychopyTime_s"] = offset + rate * samples["Timestamp"] / 1e6
    samples["gazeX"], samples["gazeY"] = gaze_point(samples)
    samples["region"] = assign_regions(samples, trials, name_radius_px, centre_radius_px)
    samples["participantID"] = participant

    gaze = samples[["participantID", "Timestamp", "psychopyTime_s", "trialN",
                    "trialRecorded", "phase", "block", "attempt", "targetObj",
                    "previousObj", "trialPhase", "gazeX", "gazeY", "region"]]
    gaze.to_csv(gaze_path, index=False, float_format="%.4f")
    regions = visits(samples, blink_ms)
    regions.to_csv(regions_path, index=False, float_format="%.4f")

    in_trials = samples["trialN"].notna()
    print(f"session:  {stem}")
    print(f"dropped:  {dropped} samples before the tracker's clock reset")
    print(f"samples:  {len(samples)}  (in trial windows: {in_trials.sum()})")
    print(f"trials:   {samples['trialN'].nunique()} with samples; "
          f"interrupted (no trial-file row): {interrupted or 'none'}")
    print(f"clock:    PsychoPy = {offset:.4f} + {rate:.7f} x tracker  "
          f"(drift {(rate - 1) * 1e6:.1f} ppm)")
    print(f"fit:      {len(residual_ms)} events, residual sd "
          f"{residual_ms.std():.2f} ms, largest {abs(residual_ms).max():.2f} ms")
    lags = check_lag(samples, markers, trials)
    if len(lags):
        print(f"lag:      GetLastResult trails the marker by median "
              f"{np.median(lags):.2f} ms (range {lags.min():.2f} to "
              f"{lags.max():.2f} ms, {len(lags)} events)")
    shares = samples.loc[in_trials, "region"].value_counts(normalize=True) * 100
    print("regions:  in trial windows: "
          + ", ".join(f"{r} {p:.1f}%" for r, p in shares.items()))

    # Check: at each selection marker the gaze should be on the selected name.
    hits = total = 0
    for index, event, fields in markers:
        if event == "selection" and samples["trialRecorded"].iat[index] == "True":
            total += 1
            hits += samples["region"].iat[index] == fields.get("object")
    if total:
        print(f"check:    gaze on the selected name at {hits} of {total} selection markers")
    print(f"visits:   {len(regions)}  (blinks up to {blink_ms:.0f} ms bridged)")
    print(f"written:  {gaze_path.name}, {regions_path.name}")
    return gaze_path


def sessions_for(sona_id):
    """Trial files of one participant: data/<sona_id>_<date>_<time>_trials.csv."""
    return sorted(DATA_DIR.glob(f"{sona_id}_*_trials.csv"))


def merge_if_new(trials_path):
    """Merge one session unless its _gaze.csv exists (delete it to redo)."""
    trials_path = Path(trials_path)
    stem = trials_path.name.removesuffix("_trials.csv")
    out_path = trials_path.with_name(stem + "_gaze.csv")
    if out_path.exists():
        print(f"skipped:  {out_path.name} already exists")
        return
    merge(trials_path)
    print()


if __name__ == "__main__":
    # Arguments: trial file paths or SONA IDs. None: newest session in data/.
    arguments = sys.argv[1:]
    if not arguments:
        newest = max(DATA_DIR.glob("*_trials.csv"), key=lambda p: p.stat().st_mtime)
        arguments = [str(newest)]

    for argument in arguments:
        if argument.endswith(".csv"):
            merge_if_new(argument)
            continue
        found = sessions_for(argument)
        if not found:
            known = sorted({p.name.split("_")[0] for p in DATA_DIR.glob("*_trials.csv")})
            print(f"no sessions for SONA ID {argument}; IDs in data/: {', '.join(known)}")
        for trials_path in found:
            merge_if_new(trials_path)
