"""Turn one session's tracker file into one analysis file, _gaze.csv.

Run by hand after a session:
    cd analysis
    python merge.py                                        # newest session in data/
    python merge.py ../data/877787_20260925/877787_20260925_trials.csv
    python merge.py 000001 877787                          # every session of these SONA IDs

Each session has its own folder, data/<stem>/, with stem <id>_<date>
(YYYYmmdd; a second session that day has _2, _3 ...). Inputs in it:
    <stem>.csv            the LiveTrack file (one row every 2 ms, markers in Comment)
    <stem>_trials.csv     one row per completed trial
    <stem>_session.csv    one row of values that are the same for the whole session

Output, in the same folder:
    <stem>_gaze.csv       one row per tracker sample (every 2 ms)
        participantID, Timestamp, psychopyTime_s,
        trialN, trialRecorded, phase, block, attempt, blockStatus,
        targetObj, previousObj, trialPhase, gazeX, gazeY, gazeUnits, region,
        whereGaze

Visits (one row per unbroken stretch of samples in one region) are not
saved; load_visits(gaze_path) builds them from _gaze.csv when needed:
        participantID, trialN, phase, block, attempt, blockStatus,
        trialPhase, region, start_s, end_s, duration_ms, samples

Terms
    sample   one row of the tracker file
    marker   text sent to the tracker; it lands in the Comment column of
             the next sample ("event=dot_on trial=3 ...")
    trial window   the samples of one trial (see assign_trials)
    region   g0..g7 (on a name), centre, other, or lost (no gaze from
             either eye); computed here from each 2-ms sample
    Timestamp  the tracker's clock (us). It may restart after a
             recalibration; psychopyTime_s is one clock for the session
             (empty in a clock segment with no trial events to fit: the
             recalibration itself)
    blockStatus  complete, interrupted_break, interrupted_recalibration,
             skipped or session_ended (see block_status)
    gazeUnits  screen_px, or raw (camera values during a recalibration,
             from the tracker file's LeftGazeX header; no region, no visits)
    whereGaze  the live state the experiment recorded during the trial
             (10-ms intervals, blinks filled; see response.GazeStateRecorder);
             empty outside dot_on to feedback (or blank)
    visit    consecutive samples in one region; a short loss of gaze
             (a blink) with the same region on both sides does not end it

The tracker file is not changed. Session-wide values are only in
<stem>_session.csv; join on participantID.
"""

import io
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_DIR / "data"

# Marker name -> trial-file column of that event's PsychoPy time. Taken from
# the experiment's own trialdata.py, so the two can never disagree.
sys.path.insert(0, str(PROJECT_DIR / "demo"))
from trialdata import EVENT_TIMES, tracker_column  # noqa: E402

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

# Raw-mode column names (written during a recalibration) -> the usual names
RAW_COLUMNS = {"LeftGazeX": "LeftScreenX", "LeftGazeY": "LeftScreenY",
               "RightGazeX": "RightScreenX", "RightGazeY": "RightScreenY"}


def read_blocks(path):
    """Read the tracker file, which can hold several header lines.

    The tracker writes a new header line each time the results type
    changes (a recalibration): "LeftGazeX ..." for raw camera values, then
    "LeftScreenX ..." again for screen pixels. Each block is read with its
    own header. gazeUnits is "raw" in raw blocks and "screen_px" otherwise.
    """
    with open(path, encoding="utf-8") as f:
        lines = f.read().splitlines()
    starts = [i for i, line in enumerate(lines) if line.startswith("Timestamp")]
    blocks = []
    for k, start in enumerate(starts):
        end = starts[k + 1] if k + 1 < len(starts) else len(lines)
        if end - start < 2:
            continue                    # header with no samples
        block = pd.read_csv(io.StringIO("\n".join(lines[start:end])),
                            skipinitialspace=True, dtype={"Comment": str})
        block.columns = block.columns.str.strip()
        raw_units = "LeftGazeX" in block.columns
        block = block.rename(columns=RAW_COLUMNS)
        block["gazeUnits"] = "raw" if raw_units else "screen_px"
        blocks.append(block)
    raw = pd.concat(blocks, ignore_index=True)
    raw["Comment"] = raw["Comment"].fillna("").str.strip()
    return raw


def read_tracker(path):
    """Tracker samples, with clock segments.

    The tracker restarts its timestamps about 0.4 s after recording starts
    (also seen in CRS's demo files). Samples before that first restart
    (before any marker) are dropped.

    Later restarts (StopTracking/StartTracking during a recalibration) are
    kept. Each run of samples on one clock is a clock segment
    (clockSegment, 0, 1, ...). t_us is a continuous time for ordering only:
    each segment is placed 2 ms after the one before, so the real length
    of the gap is not in it.

    Returns (samples, dropped, number of later restarts).
    """
    raw = read_blocks(path)

    time_us = raw["Timestamp"].to_numpy()
    restarts = np.where(np.diff(time_us) < 0)[0] + 1   # first row of a new clock
    marked = np.where(raw["Comment"] != "")[0]
    first_marker = marked[0] if len(marked) else len(raw)
    early = restarts[restarts <= first_marker]
    dropped = int(early[-1]) if len(early) else 0
    raw = raw.iloc[dropped:].reset_index(drop=True)
    later = restarts[restarts > first_marker] - dropped

    segment = np.zeros(len(raw), dtype=int)
    t_us = raw["Timestamp"].to_numpy(dtype=float).copy()
    for k, start in enumerate(later, start=1):
        segment[start:] = k
        t_us[start:] += t_us[start - 1] + 2000 - t_us[start]
    raw["clockSegment"] = segment
    raw["t_us"] = t_us
    return raw, dropped, len(later)


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
    time_us = samples["t_us"].to_numpy()
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
        if event in EVENT_TIMES:
            trial_phase[index] = event
    close(n)

    # Latest trial marker, carried forward, but only inside its own window.
    marker_trial = np.full(n, -1)
    for index, event, fields in markers:
        if event in EVENT_TIMES:
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


def label_recalibration(samples, markers):
    """trialPhase "recalibration" from recalibration_start to recalibration_end.

    (Which of these rows are raw camera values is in gazeUnits, from the
    tracker file's header lines; see read_blocks.)
    """
    phase = samples["trialPhase"].to_numpy().copy()
    recal_from = None
    for index, event, _ in markers:
        if event == "recalibration_start":
            recal_from = index
        elif event == "recalibration_end" and recal_from is not None:
            phase[recal_from:index + 1] = "recalibration"
            recal_from = None
    if recal_from is not None:              # session ended during it
        phase[recal_from:] = "recalibration"
    samples["trialPhase"] = phase
    return samples


def block_status(samples, markers):
    """blockStatus for every sample in a trial window.

    One value per block attempt (phase, block, attempt):
        complete                    the block ran to its end
        interrupted_break           pause screen, Continue
        interrupted_recalibration   pause screen, Recalibrate
        skipped                     pause screen, Skip to next section
        session_ended               the session ended during the block
    """
    status, current = {}, None
    for _, event, fields in markers:
        if event == "block_start":
            current = (fields.get("phase", ""), fields.get("block", ""),
                       fields.get("attempt", ""))
            status[current] = "session_ended"   # until something else is seen
        elif current is None:
            continue
        elif event == "block_end":
            status[current], current = "complete", None
        elif event == "block_abandoned":
            reason = fields.get("reason")
            if reason is None:                  # sessions before "reason"
                reason = ("recalibration" if fields.get("recalibrate") == "True"
                          else "break")
            status[current], current = f"interrupted_{reason}", None
        elif event == "section_skipped":
            status[current], current = "skipped", None

    keys = zip(samples["phase"], samples["block"].astype(str),
               samples["attempt"].astype(str))
    in_trial = samples["trialN"].notna().to_numpy()
    return np.array([status.get(key, "") if inside else ""
                     for key, inside in zip(keys, in_trial)], dtype=object)


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

    A visit never crosses a change of trialN. Raw rows (recalibration) have
    no region and no visits. A run of "lost" samples
    joins the visit around it if the region is the same on both sides and
    the run lasts at most blink_ms. Longer losses are their own "lost" visit.

    start_s is the PsychoPy time of the first sample; end_s is the time of
    the next sample after the visit, so durations add up without gaps.
    """
    time_s = samples["psychopyTime_s"].to_numpy()
    step = np.nanmedian(np.diff(time_s))
    next_time = np.append(time_s[1:], time_s[-1] + step)
    # Next sample in another clock segment or without a time: end one step on.
    next_time = np.where(np.isnan(next_time), time_s + step, next_time)
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
                                "attempt", "blockStatus",
                                "trialPhase"]].reset_index(drop=True)
    out["region"] = region[starts]
    out["start_s"] = time_s[starts]
    out["end_s"] = next_time[ends]
    out["duration_ms"] = (out["end_s"] - out["start_s"]) * 1000
    out["samples"] = ends - starts + 1
    return out[out["region"] != ""].reset_index(drop=True)   # raw rows: no region


def where_gaze(samples, markers):
    """whereGaze for every sample, from the experiment's gaze markers.

    Each marker lists changes as state:tracker_us. A state holds from its
    time until the next change of the same trial; "off" ends it. Only
    samples in that trial's window get a value.
    """
    changes = {}
    for _, event, fields in markers:
        if event != "gaze":
            continue
        for part in fields["states"].split(";"):
            state, us = part.split(":")
            changes.setdefault(int(fields["trial"]), []).append((int(us), state))

    time_us = samples["Timestamp"].to_numpy()
    trial_n = samples["trialN"].to_numpy(dtype=float, na_value=np.nan)
    out = np.full(len(samples), "", dtype=object)
    for trial, items in changes.items():
        items.sort()
        where = np.where(trial_n == trial)[0]
        if not len(where):
            continue
        starts = np.array([us for us, _ in items])
        states = np.array([st for _, st in items] + [""], dtype=object)
        k = np.searchsorted(starts, time_us[where], side="right") - 1
        values = states[np.where(k >= 0, k, -1)]     # before the first: ""
        values[values == "off"] = ""
        out[where] = values
    return out


# ---------------------------------------------------------------- clocks

def event_pairs(samples, markers, trials, column_for):
    """(marker timestamp, trial-file value, clock segment) per trial marker
    of a recorded trial."""
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
            pairs.append((samples["Timestamp"].iat[index], value,
                          samples["clockSegment"].iat[index]))
    return np.array(pairs, dtype=float).reshape(-1, 3)


def fit_clock(samples, markers, trials):
    """PsychoPy time (s) for every sample, from a line per clock segment.

    Each trial event has a marker timestamp and a PsychoPy time in the
    trial file. The clocks run at slightly different speeds, so each
    segment gets an offset and a rate. A segment with one event uses the
    rate of the segment with the most events; a segment with none (e.g.
    raw samples during a recalibration) gets no PsychoPy time.

    Returns (psychopy_s, fits {segment: (offset, rate, n events)}, residuals ms).
    """
    pairs = event_pairs(samples, markers, trials, lambda c: c)
    segments = pairs[:, 2].astype(int)
    fits, residuals = {}, []
    for seg in np.unique(segments):
        p = pairs[segments == seg]
        if len(p) >= 2:
            rate, offset = np.polyfit(p[:, 0] / 1e6, p[:, 1], 1)
            fits[seg] = (offset, rate, len(p))
            residuals.extend((p[:, 1] - (offset + rate * p[:, 0] / 1e6)) * 1000)
    if fits:
        main_rate = max(fits.values(), key=lambda f: f[2])[1]
        for seg in np.unique(segments):
            if seg not in fits:
                p = pairs[segments == seg]
                fits[seg] = (p[0, 1] - main_rate * p[0, 0] / 1e6, main_rate, 1)

    psychopy_s = np.full(len(samples), np.nan)
    time_s = samples["Timestamp"].to_numpy() / 1e6
    seg_of = samples["clockSegment"].to_numpy()
    for seg, (offset, rate, _) in fits.items():
        here = seg_of == seg
        psychopy_s[here] = offset + rate * time_s[here]
    return psychopy_s, fits, np.array(residuals)


def check_lag(samples, markers, trials):
    """How far GetLastResult's timestamp trails the marker, per event (ms)."""
    pairs = event_pairs(samples, markers, trials, tracker_column)
    return (pairs[:, 0] - pairs[:, 1]) / 1000   # same clock segment


# ---------------------------------------------------------------- main

def merge(trials_path):
    trials_path = Path(trials_path)
    stem = trials_path.name.removesuffix("_trials.csv")
    tracker_path = trials_path.with_name(stem + ".csv")
    session_path = trials_path.with_name(stem + "_session.csv")
    gaze_path = trials_path.with_name(stem + "_gaze.csv")

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

    samples, dropped, restarts = read_tracker(tracker_path)
    markers = read_markers(samples)
    samples, interrupted = assign_trials(samples, markers, trials, iti_s)
    samples = label_recalibration(samples, markers)
    samples["blockStatus"] = block_status(samples, markers)

    samples["psychopyTime_s"], fits, residual_ms = fit_clock(samples, markers, trials)
    samples["gazeX"], samples["gazeY"] = gaze_point(samples)
    region = assign_regions(samples, trials, name_radius_px, centre_radius_px)
    samples["region"] = np.where(samples["gazeUnits"] == "raw", "", region)
    samples["whereGaze"] = where_gaze(samples, markers)
    samples["participantID"] = participant

    gaze = samples[["participantID", "Timestamp", "psychopyTime_s", "trialN",
                    "trialRecorded", "phase", "block", "attempt",
                    "blockStatus", "targetObj", "previousObj", "trialPhase",
                    "gazeX", "gazeY", "gazeUnits", "region", "whereGaze"]]
    gaze.to_csv(gaze_path, index=False, float_format="%.4f")
    regions = visits(samples, blink_ms)       # for the report only

    in_trials = samples["trialN"].notna()
    print(f"session:  {stem}")
    print(f"dropped:  {dropped} samples before the tracker's clock reset")
    if restarts:
        print(f"restarts: tracker clock restarted {restarts} more time(s) "
              f"(recalibration); {len(fits)} clock segment(s) with events")
    raw_n = (samples["gazeUnits"] == "raw").sum()
    if raw_n:
        print(f"raw:      {raw_n} samples in raw camera values (recalibration)")
    statuses = samples.drop_duplicates(["phase", "block", "attempt"])
    statuses = statuses[statuses["blockStatus"] != ""]
    if (statuses["blockStatus"] != "complete").any():
        print("blocks:   " + ", ".join(
            f"{r.phase} {r.block}/{r.attempt} {r.blockStatus}"
            for r in statuses.itertuples() if r.blockStatus != "complete"))
    print(f"samples:  {len(samples)}  (in trial windows: {in_trials.sum()})")
    print(f"trials:   {samples['trialN'].nunique()} with samples; "
          f"interrupted (no trial-file row): {interrupted or 'none'}")
    for seg, (offset, rate, n_events) in sorted(fits.items()):
        print(f"clock:    segment {seg}: PsychoPy = {offset:.4f} + {rate:.7f} "
              f"x tracker  (drift {(rate - 1) * 1e6:.1f} ppm, {n_events} events)")
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
    live = samples["whereGaze"] != ""
    if live.any():
        both = live & (samples["region"] != "lost")
        same = (samples.loc[both, "whereGaze"] == samples.loc[both, "region"]).mean()
        print(f"live:     whereGaze on {live.sum()} samples; same as region on "
              f"{same * 100:.1f}% of them (region not lost)")
    print(f"written:  {gaze_path.name}")
    return gaze_path


def load_visits(gaze_path):
    """The visit table of one session, built from its _gaze.csv.

    Uses the blink limit saved in the session file next to it.
    """
    gaze_path = Path(gaze_path)
    stem = gaze_path.name.removesuffix("_gaze.csv")
    session = pd.read_csv(gaze_path.with_name(stem + "_session.csv"),
                          dtype=str, keep_default_na=False).iloc[0]
    samples = pd.read_csv(gaze_path, dtype={"participantID": str,
                                            "phase": str, "block": str,
                                            "attempt": str},
                          keep_default_na=False, na_values={"psychopyTime_s": [""]})
    samples["trialN"] = pd.to_numeric(samples["trialN"]).astype("Int64")
    return visits(samples, float(session["DWELL_SELECTION.blinkTimeout_ms"]))


def trial_files():
    """Every trial file in data/: one folder per session (and older files
    saved directly in data/)."""
    return [*DATA_DIR.glob("*/*_trials.csv"), *DATA_DIR.glob("*_trials.csv")]


def sessions_for(sona_id):
    """Trial files of one participant."""
    return sorted(p for p in trial_files() if p.name.startswith(f"{sona_id}_"))


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
        newest = max(trial_files(), key=lambda p: p.stat().st_mtime)
        arguments = [str(newest)]

    for argument in arguments:
        if argument.endswith(".csv"):
            merge_if_new(argument)
            continue
        found = sessions_for(argument)
        if not found:
            known = sorted({p.name.split("_")[0] for p in trial_files()})
            print(f"no sessions for SONA ID {argument}; IDs in data/: {', '.join(known)}")
        for trials_path in found:
            merge_if_new(trials_path)
