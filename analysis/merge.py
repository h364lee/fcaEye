"""Merge one session's tracker file and trial file into one file.

    cd analysis
    python merge.py                                        # newest session in data/
    python merge.py ../data/877787_20260925_132503_trials.csv
    python merge.py 000001 877787                          # every session of these SONA IDs

Output, next to the two inputs:
    <id>_<date>_<time>_merged.csv    one row per tracker sample (every 2 ms)

Each row = the tracker sample, unchanged
         + trialN          trial the sample belongs to (empty before trial 1)
         + trialPhase      the latest marker, i.e. what was on screen
         + psychopyTime_s  the sample's time on PsychoPy's clock
         + every column of the trial file for that trial
           (session and settings columns on every row)

Nothing in the gaze data is changed: lost samples stay as (0, 0), so any
cleaning is a separate, visible step.
"""

import sys
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


def read_tracker(path):
    """Tracker samples after the tracker's own clock reset.

    About 0.4 s after recording starts, the tracker restarts its timestamps
    once (also in CRS's own demo files). Samples before that point are on a
    different clock, so they are dropped.
    """
    raw = pd.read_csv(path, skipinitialspace=True, dtype={"Comment": str})
    raw["Comment"] = raw["Comment"].fillna("").str.strip()

    restarts = np.where(np.diff(raw["Timestamp"].to_numpy()) < 0)[0]
    dropped = 0
    if len(restarts):
        dropped = restarts[-1] + 1
        raw = raw.iloc[dropped:].reset_index(drop=True)
    return raw, dropped


def add_trial_and_phase(samples):
    """trialN and trialPhase for every sample, read from the markers.

    A sample belongs to the trial of the most recent dot_on marker, until
    session_end or session_aborted. Within a trial, its phase is the most
    recent trial marker. Outside trials the phase is "before_trials" or
    "after_trials" (instructions, or the end of the session).
    """
    event = samples["Comment"].str.extract(r"event=(\w+)")[0]
    trial = samples["Comment"].str.extract(r"trial=(\d+)")[0].astype(float)

    starts = trial.where(event == "dot_on")
    starts[event.isin(["session_end", "session_aborted"])] = 0   # 0 = no trial
    samples["trialN"] = starts.ffill().replace(0, np.nan).astype("Int64")

    phase = event.where(trial.notna()).ffill()
    before = samples.index < starts.first_valid_index()
    phase[samples["trialN"].isna() & before] = "before_trials"
    phase[samples["trialN"].isna() & ~before] = "after_trials"
    samples["trialPhase"] = phase
    return samples


def fit_clock(samples, trials):
    """Straight line from tracker time (s) to PsychoPy time (s).

    Every event has a time on both clocks: its marker's tracker timestamp,
    and the PsychoPy time in the trial file. The two clocks run at slightly
    different speeds, so a line (offset + rate) fits better than an offset.
    """
    marked = samples[samples["Comment"].str.contains("trial=")]
    tracker_s, psychopy_s = [], []
    for _, row in marked.iterrows():
        event = row["Comment"].split()[0].removeprefix("event=")
        match = trials.loc[trials["trialN"] == row["trialN"], EVENT_TIMES[event]]
        value = pd.to_numeric(match, errors="coerce")
        if len(value) and pd.notna(value.iloc[0]):
            tracker_s.append(row["Timestamp"] / 1e6)
            psychopy_s.append(value.iloc[0])

    tracker_s, psychopy_s = np.array(tracker_s), np.array(psychopy_s)
    rate, offset = np.polyfit(tracker_s, psychopy_s, 1)
    residual_ms = (psychopy_s - (offset + rate * tracker_s)) * 1000
    return offset, rate, residual_ms


def check_lag(samples, trials):
    """How far GetLastResult's timestamp trails the marker, per event (ms).

    The marker lands on the tracker's next sample after it is sent; the
    GetLastResult timestamp is the newest sample that had reached the PC at
    that moment. The difference is the transfer delay plus up to one sample.
    Returns an empty list for sessions recorded before these columns existed.
    """
    lags = []
    for _, row in samples[samples["Comment"].str.contains("trial=")].iterrows():
        event = row["Comment"].split()[0].removeprefix("event=")
        column = EVENT_TIMES[event].removesuffix("_s") + "Tracker_us"
        if column not in trials.columns:
            return []
        match = trials.loc[trials["trialN"] == row["trialN"], column]
        value = pd.to_numeric(match, errors="coerce")
        if len(value) and pd.notna(value.iloc[0]):
            lags.append((row["Timestamp"] - value.iloc[0]) / 1000)
    return lags


def merge(trials_path):
    trials_path = Path(trials_path)
    stem = trials_path.name.removesuffix("_trials.csv")
    tracker_path = trials_path.with_name(stem + ".csv")
    out_path = trials_path.with_name(stem + "_merged.csv")

    # Every trial-file column is read as text, so values are copied exactly
    # as written (e.g. SONA ID "000001", image code "0 1 0"). Only trialN,
    # used for the join, is made a number; the time columns are converted
    # where they are calculated with.
    trials = pd.read_csv(trials_path, dtype=str, keep_default_na=False)
    trials["trialN"] = trials["trialN"].astype("Int64")
    samples, dropped = read_tracker(tracker_path)
    samples = add_trial_and_phase(samples)

    offset, rate, residual_ms = fit_clock(samples, trials)
    samples["psychopyTime_s"] = offset + rate * samples["Timestamp"] / 1e6

    # Session and settings columns are the same on every trial row, so
    # they go on every sample, including those outside trials.
    # Trial columns run from trialN up to the first settings column; the
    # settings are the columns named "GROUP.key".
    first_setting = next(i for i, c in enumerate(trials.columns) if "." in c)
    trial_columns = trials.columns[trials.columns.get_loc("trialN"):first_setting]
    session_columns = [c for c in trials.columns if c not in trial_columns]
    merged = samples.merge(trials[list(trial_columns)], on="trialN", how="left")
    for column in session_columns:
        merged[column] = trials[column].iloc[0]
    merged = merged[list(samples.columns)
                    + [c for c in trials.columns if c != "trialN"]]
    merged.to_csv(out_path, index=False)

    print(f"session:  {stem}")
    print(f"dropped:  {dropped} samples before the tracker's clock reset")
    print(f"samples:  {len(merged)}  (in trials: {merged['trialN'].notna().sum()})")
    print(f"clock:    PsychoPy = {offset:.4f} + {rate:.7f} x tracker  "
          f"(drift {(rate - 1) * 1e6:.1f} ppm)")
    print(f"fit:      {len(residual_ms)} events, residual sd "
          f"{residual_ms.std():.2f} ms, largest {abs(residual_ms).max():.2f} ms")
    lags = check_lag(samples, trials)
    if lags:
        print(f"lag:      GetLastResult trails the marker by median "
              f"{np.median(lags):.2f} ms (range {min(lags):.2f} to "
              f"{max(lags):.2f} ms, {len(lags)} events)")
    print(f"written:  {out_path}")
    return out_path


def sessions_for(sona_id):
    """Trial files of one participant: data/<sona_id>_<date>_<time>_trials.csv."""
    return sorted(DATA_DIR.glob(f"{sona_id}_*_trials.csv"))


def merge_if_new(trials_path):
    """Merge one session, unless its merged file already exists.

    To merge a session again, delete its _merged.csv first.
    """
    trials_path = Path(trials_path)
    stem = trials_path.name.removesuffix("_trials.csv")
    out_path = trials_path.with_name(stem + "_merged.csv")
    if out_path.exists():
        print(f"skipped:  {out_path.name} already exists")
        return
    merge(trials_path)
    print()


if __name__ == "__main__":
    # Each argument is either a trial file path or a SONA ID.
    # No argument: the newest session in data/.
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
