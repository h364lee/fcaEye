"""Merge one session's tracker file and trial file into one file.

    cd analysis
    python merge.py                                        # newest session in data/
    python merge.py ../data/877787_20260925_132503_trials.csv

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
    "objects_on": "objectsOn_s",
    "name_on": "nameOn_s",
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
        if len(match) and pd.notna(match.iloc[0]):
            tracker_s.append(row["Timestamp"] / 1e6)
            psychopy_s.append(match.iloc[0])

    tracker_s, psychopy_s = np.array(tracker_s), np.array(psychopy_s)
    rate, offset = np.polyfit(tracker_s, psychopy_s, 1)
    residual_ms = (psychopy_s - (offset + rate * tracker_s)) * 1000
    return offset, rate, residual_ms


def merge(trials_path):
    trials_path = Path(trials_path)
    stem = trials_path.name.removesuffix("_trials.csv")
    tracker_path = trials_path.with_name(stem + ".csv")
    out_path = trials_path.with_name(stem + "_merged.csv")

    # Read the image codes as text, so "0 1 0" is kept as written.
    trials = pd.read_csv(trials_path, dtype={c: str for c in
                         pd.read_csv(trials_path, nrows=0).columns
                         if c.endswith("Image")})
    samples, dropped = read_tracker(tracker_path)
    samples = add_trial_and_phase(samples)

    offset, rate, residual_ms = fit_clock(samples, trials)
    samples["psychopyTime_s"] = offset + rate * samples["Timestamp"] / 1e6

    # Session and settings columns are the same on every trial row, so
    # they go on every sample, including those outside trials.
    trial_columns = trials.columns[trials.columns.get_loc("trialN"):
                                   trials.columns.get_loc("blankOn_s") + 1]
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
    print(f"written:  {out_path}")
    return out_path


if __name__ == "__main__":
    if len(sys.argv) > 1:
        merge(sys.argv[1])
    else:
        newest = max(DATA_DIR.glob("*_trials.csv"), key=lambda p: p.stat().st_mtime)
        merge(newest)
