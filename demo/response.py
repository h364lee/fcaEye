"""Collecting a response.

wait_for_central_fixation holds the trial until gaze stays on the central dot.
GazeDwellResponder decides which object is selected after the cue.

The responder is polled, not blocking, because the trial loop also has to
keep drawing and checking for quit.
"""
import sys
sys.path.insert(0, r"C:\Users\Public\Documents\CRS LiveTrack Python Bindings")
import LiveTrack

import geometry
from config import CENTRAL_FIXATION, DWELL_SELECTION, GEOMETRY
from presentation import check_quit

import math
from psychopy import core


class FixationTimeout(Exception):
    """Central fixation was never held for long enough.

    Raised rather than handled locally, because the session cannot continue:
    either the tracker has lost the eye, or gaze is reading far enough from
    where the participant is actually looking that the criterion cannot be
    met. Both need a person to intervene.
    """


def newest_tracked():
    """Newest tracked gaze position, or None if every reading was lost.

    Draining the buffer keeps it small; we only want the latest reading.
    Shared by the fixation gate and the dwell responder so both treat a
    lost eye the same way.
    """
    samples = LiveTrack.GetBufferedEyePositions(1, -1, 1)
    for s in reversed(samples):
        if s.Tracked:
            return (s.GazeX, s.GazeY)
    return None


def wait_for_central_fixation(pres, hold_s, positions=None):
    """Hold here until gaze has stayed near the screen centre for hold_s.

    Without positions, only the dot is on screen. With positions, the objects
    are drawn too, so gaze must stay on the dot while the objects are visible.
    If gaze leaves the dot, the count starts again from zero.

    The screen is redrawn every frame, because flipping is what advances the
    frame and the screen has to keep refreshing while we wait.

    A blink pauses the count rather than resetting it, using the same gap
    limit as the dwell responder -- a blink is missing information, not
    evidence that the eye moved.

    Args:
        pres: a Presentation.
        hold_s: how long gaze must stay on the dot, in seconds.
        positions: object positions to draw, or None for the dot alone.

    Raises:
        FixationTimeout: the hold was never achieved within timeout_s.
    """
    radius_px = CENTRAL_FIXATION['centralRadius_deg'] * geometry.px_per_deg()
    timeout_s = CENTRAL_FIXATION['centralTimeout_s']
    blink_gap_s = DWELL_SELECTION['blinkTimeout_ms'] / 1000

    LiveTrack.ClearDataBuffer()
    clock = core.Clock()
    held_s = 0.0
    last = 0.0
    gap_start = None

    while held_s < hold_s:
        now = clock.getTime()
        dt = now - last
        last = now

        if now > timeout_s:
            raise FixationTimeout(
                f"central fixation not held for {hold_s} s "
                f"within the {timeout_s} s limit"
            )

        check_quit()
        pos = newest_tracked()

        if pos is None:
            if gap_start is None:
                gap_start = now
            elif now - gap_start > blink_gap_s:
                held_s = 0.0
        else:
            gap_start = None
            # math.hypot(x, y) is the distance from the screen centre,
            # since gaze coordinates have their origin there.
            if math.hypot(*pos) <= radius_px:
                held_s += dt
            else:
                held_s = 0.0

        if positions is not None:
            pres.draw_array(positions)
        pres.draw_fixation()
        pres.flip()


class GazeDwellResponder:
    """Selection by holding gaze on an object.

    Two conditions must both hold for the count to continue:
      1. gaze is within stability_px of the anchor (where this dwell began)
      2. gaze is on the same object it was on at the anchor

    A blink pauses the count rather than resetting it, up to blinkTimeout_ms.

    Lifecycle:
        start()   once, at cue onset
        poll()    once per frame
        result()  each frame; returns None until a selection is made
    """

    def __init__(self, positions, ring_order):
        self.positions = positions
        self.ring_order = ring_order
        self.clock = core.Clock()

        # degrees -> pixels, same formula calibrate.py uses
        self.stability_px = DWELL_SELECTION["dwellRadius_deg"] * geometry.px_per_deg()
        self.dwell_s = DWELL_SELECTION["dwell_ms"] / 1000
        self.blink_gap_s = DWELL_SELECTION["blinkTimeout_ms"] / 1000

        # State is set up in start(), which the trial calls at cue onset.
        # Not called here as well, or the buffer would be cleared twice.
        self.outcome = None

    def start(self):
        """Reset clock and internal state. Called at cue onset."""
        self.clock.reset()
        self.outcome = None
        self.first_move_ms = None
        self.anchor = None        # gaze position where the current dwell began
        self.dwell_on = None      # object at the anchor
        self.dwell_accum = 0.0    # seconds counted so far
        self.last_poll = 0.0
        self.gap_start = None     # when the current untracked gap began
        LiveTrack.ClearDataBuffer()   # discard samples recorded before the cue

    def _restart(self, pos, here):
        self.anchor = pos
        self.dwell_on = here
        self.dwell_accum = 0.0
        self.gap_start = None

    def poll(self):
        """Read the newest gaze sample once and update the dwell count."""
        if self.outcome is not None:
            return

        now = self.clock.getTime()
        dt = now - self.last_poll
        self.last_poll = now

        pos = newest_tracked()

        # No usable reading. Hold everything; the eye has not moved,
        # we just cannot see it.
        if pos is None:
            if self.gap_start is None:
                self.gap_start = now
            elif now - self.gap_start > self.blink_gap_s:
                self.anchor = None
                self.dwell_on = None
                self.dwell_accum = 0.0
            return
        self.gap_start = None

        if (self.first_move_ms is None
                and math.hypot(*pos) > GEOMETRY['objSelectRadius_px']):
            self.first_move_ms = now * 1000

        here = geometry.object_at(pos, self.positions, self.ring_order)

        if self.anchor is None:
            self._restart(pos, here)
            return

        drifted = math.dist(pos, self.anchor) > self.stability_px
        if drifted or here != self.dwell_on:
            self._restart(pos, here)
            return

        self.dwell_accum += dt
        if self.dwell_on is not None and self.dwell_accum >= self.dwell_s:
            self.outcome = {
                "selection": self.dwell_on,
                "selection_ms": now * 1000,
                "first_move_ms": self.first_move_ms,
            }

    def result(self):
        """The outcome so far.

        Returns:
            None while no selection has been made, otherwise a dict with
                selection       object name
                selection_ms    time from start() to selection
                first_move_ms   time gaze first left the centre, or
                                None if it has not
        """
        return self.outcome
