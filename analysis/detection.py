# AI usage: code co-written with Claude Opus 5.5.
# Research questions, experimental design and program requirements came from Caleb and Britt.

"""Gaze-based measures for one session, from the live state (whereGaze).

Run by hand:
    cd analysis
    python detection.py 000000_20261023_2

Terms
    state    one value of whereGaze: g0..g7, centre, other or lost
    visit    a run of consecutive samples with the same state in one trial
    arrive   the first visit to a name (g0..g7) that starts at or after
             object_on
    leave    the end of the last centre visit before arrive: the start of
             the eye movement that reached the name (the saccade onset,
             as far as whereGaze can show it; gaze crosses the 2 deg
             circle a few ms after the eye starts to move)

Times are tracker time (us). A trial lies inside one tracker clock segment,
so differences within a trial need no clock conversion.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_DIR / "data"

SAMPLE_US = 2000          # one tracker sample at 500 Hz
NAMES = [f"g{i}" for i in range(8)]


# ---------------------------------------------------------------- loading

def load_session(stem):
    """Gaze samples and trial rows of one session.

    gaze:   rows of <stem>_gaze.csv where whereGaze has a value and the
            trial has a row in the trial file (all recorded trials;
            timeouts and incorrect selections are kept).
    trials: <stem>_trials.csv, one row per recorded trial.
    """
    folder = DATA_DIR / stem

    # Read as text, so "" stays "" (not NaN) and IDs keep their zeros.
    gaze = pd.read_csv(folder / f"{stem}_gaze.csv", dtype=str,
                       keep_default_na=False,
                       usecols=["Timestamp", "trialN", "trialRecorded",
                                "phase", "block", "targetObj",
                                "previousObj", "whereGaze"])
    trials = pd.read_csv(folder / f"{stem}_trials.csv",
                         dtype={"participantID": str})

    # 1. Keep only samples that have a live state and belong to a
    #    recorded trial. 
    keep = (gaze["whereGaze"] != "") & (gaze["trialRecorded"] == "True")
    gaze = gaze[keep].copy()

    # 2. Turn the two numeric columns back into numbers
    gaze["Timestamp"] = gaze["Timestamp"].astype("int64")
    gaze["trialN"] = gaze["trialN"].astype("int64")

    return gaze.reset_index(drop=True), trials


# ---------------------------------------------------------------- visits

def visits(gaze):
    """One row per visit: trialN, state, start_us, end_us, duration_ms.

    A new visit starts where the state changes, or where the trial
    changes. start_us is the Timestamp of the visit's first sample;
    end_us is the Timestamp of the next visit's first sample (or one
    sample after the last one, at the end of a trial), so the durations
    of a trial add up without gaps.
    """
    state = gaze["whereGaze"]
    trial = gaze["trialN"]

    # 1. True on the first sample of every visit.
    #    Compare each row with the row before it: .shift() moves a column
    #    down by one row. A visit starts where the state differs from the
    #    previous row's state, OR the trial differs from the previous row's
    #    trial (join with |). The first row is always a start; .shift()
    #    gives NaN there, which compares as "different", so it is True.
    is_start = (state != state.shift()) | (trial != trial.shift())

    starts = gaze[is_start]

    # 2. End of each visit = start of the next visit in the same trial.
    #    Within a trial, the next start is the next row of `starts`.
    #    The last visit of a trial has no next visit; use its last
    #    sample + SAMPLE_US instead (done below with last_sample_us).
    next_start = starts["Timestamp"].shift(-1)
    same_trial_next = starts["trialN"].shift(-1) == starts["trialN"]
    last_sample_us = gaze.groupby("trialN")["Timestamp"].max() + SAMPLE_US

    out = pd.DataFrame({
        "trialN": starts["trialN"].to_numpy(),
        "state": starts["whereGaze"].to_numpy(),
        "start_us": starts["Timestamp"].to_numpy(),
    })
    # Where the next visit is in the same trial, end there; otherwise
    # end at the trial's last sample + one sample. np.where(cond, a, b)
    # picks a where cond is True, b elsewhere.
    out["end_us"] = np.where(same_trial_next.to_numpy(),
                             next_start.to_numpy(),
                             last_sample_us.loc[out["trialN"]].to_numpy())
    out["end_us"] = out["end_us"].astype("int64")

    # 3. Duration in ms (us -> ms: divide by 1000).
    out["duration_ms"] = (out["end_us"] - out["start_us"]) / 1000
    return out


# ---------------------------------------------------------------- latency

def o1_latency(visit_table, trials):
    """One row per recorded trial: saccade latency to the first name.

    Columns
        trialN, phase, block, targetObj, previousObj, outcome
        leave_ms     object_on -> leave (the main measure: cue onset to
                     saccade onset)
        arrive_ms    object_on -> arrive
        firstObj     state of the arrive visit (g0..g7)
        firstCorrect firstObj == targetObj
        firstMove_ms from the trial file (live, once per frame), to
                     check leave_ms against

    leave is the LAST departure from centre before arrive, so a brief
    excursion that returns to centre is not taken as the saccade.
    A trial with no visit to a name after object_on gets NaN times.
    """
    rows = []
    for t in trials.itertuples():
        # Time zero: the object onset, in tracker time (us).
        zero_us = t.objectOnTracker_us
        v = visit_table[visit_table["trialN"] == t.trialN]

        # arrive: first visit to a name that starts at or after time zero.
        arrived = v[(v["start_us"] >= zero_us) & v["state"].isin(NAMES)]

        leave_ms = arrive_ms = np.nan
        first_obj = ""
        if len(arrived):
            arrive_us = arrived["start_us"].iloc[0]
            first_obj = arrived["state"].iloc[0]
            # leave: end of the last centre visit before arrive. This
            # visit may have started before time zero (the central
            # fixation), so the search is over all of the trial's visits.
            centre_before = v[(v["start_us"] < arrive_us) & (v["state"] == "centre")]
            if len(centre_before):
                leave_ms = (centre_before["end_us"].iloc[-1] - zero_us) / 1000
            arrive_ms = (arrive_us - zero_us) / 1000

        rows.append({
            "trialN": t.trialN, "phase": t.phase, "block": t.block,
            "targetObj": t.targetObj, "previousObj": t.previousObj,
            "outcome": t.outcome,
            "leave_ms": leave_ms,
            "arrive_ms": arrive_ms,
            "firstObj": first_obj,
            "firstCorrect": first_obj == t.targetObj if first_obj else np.nan,
            "firstMove_ms": t.firstMove_ms,
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- main

if __name__ == "__main__":
    stem = sys.argv[1] if len(sys.argv) > 1 else "000000_20261023_2"
    gaze, trials = load_session(stem)
    visit_table = visits(gaze)
    latency = o1_latency(visit_table, trials)

    print(f"session: {stem}")
    print(f"samples with a live state: {len(gaze)};  visits: {len(visit_table)};  "
          f"trials: {len(latency)}")
    print(latency.groupby("phase")[["leave_ms", "arrive_ms"]]
          .describe().T.round(1).to_string())

    # Check: leave_ms (whereGaze, 10-ms grid) vs firstMove_ms (live, per frame).
    # Expect a difference of about one frame (17 ms) or less.
    diff = latency["leave_ms"] - latency["firstMove_ms"]
    print(f"leave_ms - firstMove_ms: median {diff.median():.1f} ms, "
          f"range {diff.min():.1f} to {diff.max():.1f} ms")

    out_path = DATA_DIR / stem / f"{stem}_latency.csv"
    latency.to_csv(out_path, index=False, float_format="%.1f")
    print(f"written: {out_path.name}")
