"""Detect fixations in one LiveTrack session and plot each trial.

    cd analysis
    python fixations.py                      # newest file in data/
    python fixations.py ../data/000003_20260921_091737.csv

Output goes to data/analysis/<session>/, which is already in .gitignore:
    fixations.csv       one row per fixation
    trial_<n>.png       one figure per trial

Pipeline:
    1. clean the tracker file   (our code -- pymovements cannot do these)
    2. pixels -> degrees -> speed, then I-VT fixation detection (pymovements)
    3. one figure per trial
"""

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")           # write files; no window needed
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pymovements as pm

# Screen and layout values come from the experiment's own config, so the
# analysis can never disagree with what was shown.
DEMO_DIR = Path(__file__).resolve().parent.parent / "demo"
sys.path.insert(0, str(DEMO_DIR))
import geometry                                         # noqa: E402
from config import CALIBRATION, DISPLAY, GEOMETRY, PATHS  # noqa: E402

SAMPLING_RATE_HZ = 500          # measured from the tracker's timestamps
EYE = "Left"                    # column prefix: "Left" or "Right"

# I-VT: a sample belongs to a fixation when eye speed is below the threshold,
# and a fixation must last at least the minimum duration. pymovements' defaults.
IVT_VELOCITY_THRESHOLD = 20.0   # degrees per second
IVT_MINIMUM_DURATION = 100      # ms


# --- 1. clean the tracker file ------------------------------------------

def read_session(path):
    """Read a tracker file and return (samples, markers, ring_order).

    samples:    time_ms, trial, x, y   -- one row per sample, trials 1..n only
    markers:    time_ms, trial, event, plus any key=value fields
    ring_order: object names in slot order, from the session_start marker
    """
    raw = pd.read_csv(path, skipinitialspace=True, dtype={"Comment": str})

    # session_start sits before the clock restart, so read it first.
    start = raw["Comment"].fillna("").str.contains("event=session_start")
    ring_order = ["g1", "g2", "g3", "g4", "g5"]
    if start.any():
        fields = dict(kv.split("=", 1) for kv in raw.loc[start, "Comment"].iloc[0].split())
        ring_order = fields["ring_order"].split("|")

    # The tracker's clock restarts once, shortly after recording begins.
    # Keep only what comes after the last restart.
    t = raw["Timestamp"].to_numpy()
    resets = np.where(np.diff(t) < 0)[0]
    if len(resets):
        raw = raw.iloc[resets[-1] + 1:]

    df = pd.DataFrame({
        # Microseconds -> milliseconds. pymovements needs whole milliseconds;
        # rounding moves each sample by at most 0.5 ms, well under the 2 ms
        # between samples.
        "time_ms": (raw["Timestamp"] / 1000).round().astype("int64"),
        "x": raw[f"{EYE}ScreenX"],
        "y": raw[f"{EYE}ScreenY"],
        "comment": raw["Comment"].fillna("").str.strip(),
    })

    # A lost sample is written as exactly (0, 0) -- the screen centre, where
    # the fixation dot is. Left in, every blink would look like a fixation
    # on the dot.
    lost = (df["x"] == 0) & (df["y"] == 0)
    df.loc[lost, ["x", "y"]] = np.nan

    # Trial n runs from its dot_on marker up to the next one.
    df["trial"] = df["comment"].str.startswith("event=dot_on").cumsum()
    df = df[df["trial"] > 0]

    # Each marker takes the trial it falls in. session_end has no trial=
    # field of its own, so reading it from the comment would leave a gap.
    markers = []
    for _, row in df[df["comment"] != ""].iterrows():
        fields = dict(kv.split("=", 1) for kv in row["comment"].split())
        fields["trial"] = row["trial"]
        markers.append({"time_ms": row["time_ms"], **fields})
    markers = pd.DataFrame(markers)

    samples = df[["time_ms", "trial", "x", "y"]].reset_index(drop=True)
    return samples, markers, ring_order


# --- 2. fixation detection ---------------------------------------------

def detect_fixations(samples):
    """Build a pymovements Gaze object and run I-VT on each trial."""
    experiment = pm.Experiment(
        screen_width_px=DISPLAY["size"][0],
        screen_height_px=DISPLAY["size"][1],
        screen_width_cm=CALIBRATION["screen_size_mm"][0] / 10,
        screen_height_cm=CALIBRATION["screen_size_mm"][1] / 10,
        distance_cm=CALIBRATION["view_dist_mm"] / 10,
        origin="center",        # our (0, 0) is the screen centre
        sampling_rate=SAMPLING_RATE_HZ,
    )

    # trial_columns makes pymovements treat each trial separately, so speed
    # is never computed across the gap between two trials.
    gaze = pm.gaze.from_pandas(
        samples, experiment,
        trial_columns="trial",
        time_column="time_ms", time_unit="ms",
        pixel_columns=["x", "y"],
    )
    gaze.pix2deg()              # pixels  -> degrees
    gaze.pos2vel()              # degrees -> degrees per second
    gaze.detect("ivt",
                velocity_threshold=IVT_VELOCITY_THRESHOLD,
                minimum_duration=IVT_MINIMUM_DURATION)
    gaze.compute_event_properties([("location", {"position_column": "pixel"})])
    return gaze


def fixation_table(gaze):
    """Fixations as a flat pandas table: trial, onset, offset, duration, x, y."""
    ev = gaze.events.frame.to_pandas()
    ev[["x", "y"]] = pd.DataFrame(ev["location"].tolist(), index=ev.index)
    return ev.drop(columns=["location", "name"])


# --- 3. one figure per trial ---------------------------------------------

def plot_trial(trial, samples, fix, markers, ring_order, savepath):
    """Left: gaze path and fixations over the layout. Right: x, y over time."""
    s = samples[samples["trial"] == trial]
    f = fix[fix["trial"] == trial]
    m = markers[markers["trial"] == trial]
    info = m[m["event"] == "dot_on"].iloc[0]
    t0 = info["time_ms"]

    fig, (ax_space, ax_time) = plt.subplots(
        1, 2, figsize=(14, 6), gridspec_kw={"width_ratios": [1, 1.4]})

    # -- layout: objects, dot, gaze path, fixations --------------------------
    positions = geometry.ring_positions(float(info["rotation_deg"]))
    tol = GEOMETRY["target_tolerance_px"]
    for name, (ox, oy) in zip(ring_order, positions):
        is_target = name == info["target"]
        ax_space.add_patch(plt.Circle((ox, oy), tol, fill=False,
                                      lw=2 if is_target else 1,
                                      color="green" if is_target else "grey"))
        ax_space.text(ox, oy, name, ha="center", va="center", fontsize=11)
    ax_space.plot(0, 0, "k+", ms=12)

    ax_space.plot(s["x"], s["y"], lw=0.6, color="steelblue", alpha=0.6,
                  label="gaze (left eye)")
    ax_space.scatter(f["x"], f["y"], s=f["duration"] / 2, color="orange",
                     edgecolor="k", zorder=3, label="fixation (size = duration)")

    half_w, half_h = DISPLAY["size"][0] / 2, DISPLAY["size"][1] / 2
    ax_space.set_xlim(-half_w, half_w)
    ax_space.set_ylim(-half_h, half_h)     # y up, as on screen
    ax_space.set_aspect("equal")
    ax_space.set_xlabel("x (px)")
    ax_space.set_ylabel("y (px)")
    ax_space.legend(loc="lower left", fontsize=8)
    ax_space.set_title(f"trial {trial}: cue {info['cue']} ({info['target']})")

    # -- time: x and y, fixations shaded, event markers as lines --------------
    ax_time.plot(s["time_ms"] - t0, s["x"], lw=0.8, label="x")
    ax_time.plot(s["time_ms"] - t0, s["y"], lw=0.8, label="y")
    for _, row in f.iterrows():
        ax_time.axvspan(row["onset"] - t0, row["offset"] - t0,
                        color="orange", alpha=0.25, lw=0)
    # Labels are staggered in height: some markers are only ~16 ms apart
    # and would otherwise print on top of each other.
    y_top, y_bottom = ax_time.get_ylim()[1], ax_time.get_ylim()[0]
    step = (y_top - y_bottom) * 0.25
    for i, (_, row) in enumerate(m.iterrows()):
        ax_time.axvline(row["time_ms"] - t0, color="k", lw=0.6, ls="--")
        ax_time.text(row["time_ms"] - t0, y_top - (i % 3) * step, row["event"],
                     rotation=90, va="top", ha="right", fontsize=7,
                     backgroundcolor="white")
    ax_time.set_xlabel("time from dot_on (ms)")
    ax_time.set_ylabel("position (px)")
    ax_time.legend(loc="lower left", fontsize=8)
    ax_time.set_title("shaded = fixation")

    fig.tight_layout()
    fig.savefig(savepath, dpi=120)
    plt.close(fig)


# --- main ------------------------------------------------------------------

def main():
    if len(sys.argv) > 1:
        path = Path(sys.argv[1])
    else:
        path = max(Path(PATHS["data_dir"]).glob("*.csv"),
                   key=lambda p: p.stat().st_mtime)
    print(f"session: {path.name}")

    samples, markers, ring_order = read_session(path)
    gaze = detect_fixations(samples)
    fix = fixation_table(gaze)

    out_dir = Path(PATHS["data_dir"]) / "analysis" / path.stem
    out_dir.mkdir(parents=True, exist_ok=True)
    fix.to_csv(out_dir / "fixations.csv", index=False)

    lost = samples["x"].isna().mean() * 100
    print(f"samples: {len(samples)}   lost: {lost:.1f}%   fixations: {len(fix)}")
    for trial in sorted(samples["trial"].unique()):
        plot_trial(trial, samples, fix, markers, ring_order,
                   out_dir / f"trial_{trial}.png")
        print(f"  trial {trial}: {sum(fix['trial'] == trial)} fixations")
    print(f"written to {out_dir}")


if __name__ == "__main__":
    main()
