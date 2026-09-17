"""
Gaze calibration - 2026-09-14
"""

import sys
sys.path.insert(0, r"C:\Users\Public\Documents\CRS LiveTrack Python Bindings")
import LiveTrack

import math
import time

import numpy as np
from psychopy import visual

from config import CALIBRATION, DISPLAY
from presentation import check_quit


def gaze_calibration(win):
    """Run one calibration pass and report the accuracy achieved.

    Assumes LiveTrack.Init(), SetResultsTypeRaw() and StartTracking()
    have already been called, and that raw results are still selected --
    the fixation check reads pupil/glint vectors, not gaze coordinates.

    Args:
        win: an open psychopy.visual.Window. Not created or closed here.

    Returns:
        dict with one entry per eye that was calibrated, e.g.
            {"left":  {"accuracy_deg": 0.34, "n_points": 9},
             "right": {"accuracy_deg": 0.41, "n_points": 8}}
        An eye that is not tracked, or that acquired no fixations at
        all, is left out of the dict entirely.
    """
    targets_deg = np.array(CALIBRATION["targets_deg"])
    n_targets = targets_deg.shape[0]

    # --- 1. degrees -> pixels -------------------------------------------
    screen_res_px = DISPLAY["size"]                  # [width_px, height_px]
    screen_size_mm = CALIBRATION["screen_size_mm"]   # [width_mm, height_mm]
    view_dist_mm = CALIBRATION["view_dist_mm"]

    px_per_mm = screen_res_px[0] / screen_size_mm[0]      # assumes square pixels
    mm_per_deg = math.tan(math.radians(1)) * view_dist_mm
    px_per_deg = mm_per_deg * px_per_mm

    target_pos_px = targets_deg * px_per_deg

    # --- 2. shuffle target order ----------------------------------------
    order = np.arange(n_targets)
    np.random.shuffle(order)
    target_pos_px = target_pos_px[order]

    # --- 3. acquire a fixation at each target ---------------------------
    fix_dot_in_px = CALIBRATION["fix_dot_in_deg"] * px_per_deg
    fix_dot_out_px = CALIBRATION["fix_dot_out_deg"] * px_per_deg
    min_dur_s = CALIBRATION["min_fix_dur_ms"] / 1000
    setup_delay_s = CALIBRATION["setup_delay_ms"] / 1000
    fix_timeout_s = CALIBRATION["fix_timeout_s"]
    fix_threshold_px = CALIBRATION["fix_threshold_px"]

    _, _, sample_rate, _, _ = LiveTrack.GetCaptureConfig()
    fix_dur_samples = round(min_dur_s * sample_rate)

    track_left, track_right = LiveTrack.GetTracking()

    vect_x_left = [None] * n_targets
    vect_y_left = [None] * n_targets
    glint_x_left = [None] * n_targets
    glint_y_left = [None] * n_targets
    vect_x_right = [None] * n_targets
    vect_y_right = [None] * n_targets
    glint_x_right = [None] * n_targets
    glint_y_right = [None] * n_targets

    outer = visual.Circle(win, units="pix", radius=fix_dot_out_px / 2,
                          fillColor=[-1, -1, -1], lineColor=[-1, -1, -1])
    inner = visual.Circle(win, units="pix", radius=fix_dot_in_px / 2,
                          fillColor=[1, 1, 1], lineColor=[-1, -1, -1])

    for i, (tx, ty) in enumerate(target_pos_px):
        outer.pos = [tx, ty]
        inner.pos = [tx, ty]
        outer.draw()
        inner.draw()
        win.flip()

        got_fix_left = False
        got_fix_right = False
        t0 = time.time()

        while True:
            check_quit()
            elapsed = time.time() - t0
            d = LiveTrack.GetBufferedEyePositions(0, fix_dur_samples, 0)

            # Only judge a full window. Guards max()/min() against an
            # empty buffer, which would raise ValueError.
            if len(d) >= fix_dur_samples:
                vect_x = LiveTrack.GetFieldAsList(d, "VectX")
                vect_y = LiveTrack.GetFieldAsList(d, "VectY")
                glint_x = LiveTrack.GetFieldAsList(d, "GlintX")
                glint_y = LiveTrack.GetFieldAsList(d, "GlintY")
                tracked = LiveTrack.GetFieldAsList(d, "Tracked")
                vect_x_r = LiveTrack.GetFieldAsList(d, "VectXRight")
                vect_y_r = LiveTrack.GetFieldAsList(d, "VectYRight")
                glint_x_r = LiveTrack.GetFieldAsList(d, "GlintXRight")
                glint_y_r = LiveTrack.GetFieldAsList(d, "GlintYRight")
                tracked_r = LiveTrack.GetFieldAsList(d, "TrackedRight")

                pg_dist_left = max(max(vect_x) - min(vect_x),
                                   max(vect_y) - min(vect_y))
                pg_dist_right = max(max(vect_x_r) - min(vect_x_r),
                                    max(vect_y_r) - min(vect_y_r))

                settled = elapsed > setup_delay_s

                if (not got_fix_left and settled
                        and pg_dist_left <= fix_threshold_px and all(tracked)):
                    vect_x_left[i] = np.median(vect_x)
                    vect_y_left[i] = np.median(vect_y)
                    glint_x_left[i] = np.median(glint_x)
                    glint_y_left[i] = np.median(glint_y)
                    got_fix_left = True
                    print(f"Target {i + 1}: left eye fixation acquired")

                if (not got_fix_right and settled
                        and pg_dist_right <= fix_threshold_px and all(tracked_r)):
                    vect_x_right[i] = np.median(vect_x_r)
                    vect_y_right[i] = np.median(vect_y_r)
                    glint_x_right[i] = np.median(glint_x_r)
                    glint_y_right[i] = np.median(glint_y_r)
                    got_fix_right = True
                    print(f"Target {i + 1}: right eye fixation acquired")

            # Every enabled eye has a fixation -- blank the dot and move on.
            if (got_fix_left or not track_left) and (got_fix_right or not track_right):
                win.flip()
                break

            if elapsed > fix_timeout_s:
                if not got_fix_left and track_left:
                    print(f"Target {i + 1}: left eye timed out")
                if not got_fix_right and track_right:
                    print(f"Target {i + 1}: right eye timed out")
                win.flip()
                break

    # --- 4. drop targets where no fixation was acquired -----------------
    # Done per eye, so a target one eye missed does not discard the
    # other eye's good data.
    idx_left = [i for i in range(n_targets) if vect_x_left[i] is not None]
    idx_right = [i for i in range(n_targets) if vect_x_right[i] is not None]

    # --- 5 & 6. fit, then convert the error to degrees ------------------
    def calibrate_eye(eye_index, idx, vx, vy, gx, gy):
        """Fit one eye. eye_index is 0 for left, 1 for right."""
        if not idx:
            return None

        tgt_x = [float(target_pos_px[i][0]) for i in idx]
        tgt_y = [float(target_pos_px[i][1]) for i in idx]
        vect_x = [float(vx[i]) for i in idx]
        vect_y = [float(vy[i]) for i in idx]
        glint_x = [float(gx[i]) for i in idx]
        glint_y = [float(gy[i]) for i in idx]

        # The fit itself happens inside the compiled CRS library. The
        # glint reference is the median across the whole calibration,
        # not per target.
        cal_err = LiveTrack.CalibrateDevice(
            eye_index, len(idx), tgt_x, tgt_y, vect_x, vect_y,
            view_dist_mm, np.median(glint_x), np.median(glint_y),
        )

        # cal_err is a summed squared error in pixels; per-point RMS is
        # sqrt(err / n), then pixels -> degrees.
        accuracy_px = math.sqrt(float(cal_err) / len(idx))
        return {"accuracy_deg": accuracy_px / px_per_deg,
                "n_points": len(idx)}

    result = {}

    if track_left:
        entry = calibrate_eye(0, idx_left, vect_x_left, vect_y_left,
                              glint_x_left, glint_y_left)
        if entry is not None:
            result["left"] = entry

    if track_right:
        entry = calibrate_eye(1, idx_right, vect_x_right, vect_y_right,
                              glint_x_right, glint_y_right)
        if entry is not None:
            result["right"] = entry

    win.flip()
    return result