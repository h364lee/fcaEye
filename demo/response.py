"""Central fixation gate and gaze-dwell selection.

The responder is polled, not blocking, so the trial loop can keep drawing
and checking for Esc.
"""
import sys
sys.path.insert(0, r"C:\Users\Public\Documents\CRS LiveTrack Python Bindings")
import LiveTrack

import geometry
from config import CENTRAL_FIXATION, DWELL_SELECTION
from presentation import check_escape

import math
from psychopy import core


class FixationTimeout(Exception):
    """Central fixation was not held in time.

    Ends the session: the tracker has lost the eye or gaze reads far from
    where the participant looks. A person must fix this.
    """


def newest_tracked():
    """Newest tracked gaze position (px from screen centre), or None.

    Reads and empties the buffer. Shared by the fixation gate and the
    responder so both treat a lost eye the same way.
    """
    samples = LiveTrack.GetBufferedEyePositions(1, -1, 1)
    for s in reversed(samples):
        if s.Tracked:
            return (s.GazeX, s.GazeY)
    return None


def wait_for_central_fixation(pres, hold_s, positions=None):
    """Wait until gaze has stayed on the central dot for hold_s seconds.

    positions: name positions to draw as well, or None for the dot alone.
    Leaving the dot resets the count to zero. A loss of gaze up to
    blinkTimeout_ms pauses the count; a longer one resets it.

    Raises FixationTimeout after CENTRAL_FIXATION["centralTimeout_s"].
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

        check_escape()
        pos = newest_tracked()

        if pos is None:
            if gap_start is None:
                gap_start = now
            elif now - gap_start > blink_gap_s:
                held_s = 0.0
        else:
            gap_start = None
            # Gaze origin is the screen centre.
            if math.hypot(*pos) <= radius_px:
                held_s += dt
            else:
                held_s = 0.0

        if positions is not None:
            pres.draw_names(positions)
        pres.draw_fixation()
        pres.flip()


class GazeDwellResponder:
    """Selection by holding gaze on one name for dwell_ms.

    The count continues while gaze stays within stability_px of where the
    dwell began and on the same name; otherwise it restarts. A loss of gaze
    up to blinkTimeout_ms pauses the count; a longer one resets it.

    Call start() at cue onset, then poll() and result() every frame.
    """

    def __init__(self, positions, ring_order, radius_px):
        self.positions = positions
        self.ring_order = ring_order
        self.radius_px = radius_px        # selection circle around each name
        self.clock = core.Clock()

        self.stability_px = DWELL_SELECTION["dwellRadius_deg"] * geometry.px_per_deg()
        # Same radius as wait_for_central_fixation, so the two agree.
        self.central_px = CENTRAL_FIXATION["centralRadius_deg"] * geometry.px_per_deg()
        self.dwell_s = DWELL_SELECTION["dwell_ms"] / 1000
        self.blink_gap_s = DWELL_SELECTION["blinkTimeout_ms"] / 1000

        # The rest of the state is set in start(). Not called here, or the
        # buffer would be cleared twice.
        self.outcome = None

    def start(self):
        """Reset the clock and state. Call at cue onset."""
        self.clock.reset()
        self.outcome = None
        self.first_move_ms = None
        self.anchor = None        # gaze position where the current dwell began
        self.dwell_on = None      # name at the anchor
        self.dwell_accum = 0.0    # seconds
        self.last_poll = 0.0
        self.gap_start = None     # start of the current loss of gaze
        LiveTrack.ClearDataBuffer()   # discard samples recorded before the cue

    def _restart(self, pos, here):
        self.anchor = pos
        self.dwell_on = here
        self.dwell_accum = 0.0
        self.gap_start = None

    def poll(self):
        """Read the newest gaze sample and update the dwell count."""
        if self.outcome is not None:
            return

        now = self.clock.getTime()
        dt = now - self.last_poll
        self.last_poll = now

        pos = newest_tracked()

        # No gaze (e.g. a blink): keep the count unless the loss is too long.
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
                and math.hypot(*pos) > self.central_px):
            self.first_move_ms = now * 1000

        here = geometry.object_at(pos, self.positions, self.ring_order,
                                  self.radius_px)

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
        """None until a selection is made, then a dict:
            selection       object name
            selection_ms    ms from start() to selection
            first_move_ms   ms from start() until gaze first left the
                            centre, or None
        """
        return self.outcome
