"""Central fixation gate, gaze-dwell selection and the live gaze state.

The responder is polled, not blocking, so the trial loop can keep drawing
and checking for Esc.

Gaze point: the midpoint of the two eyes; one eye if only that eye is
tracked. (The tracker's GazeX/GazeY are the left eye; the right eye is
GazeXRight/GazeYRight.)
"""
import sys
sys.path.insert(0, r"C:\Users\Public\Documents\CRS LiveTrack Python Bindings")
import LiveTrack

import eventlog
import geometry
from config import CENTRAL_FIXATION, DWELL_SELECTION, GAZE_STATE
from presentation import check_escape

import math
from psychopy import core


class FixationTimeout(Exception):
    """Central fixation was not held in time.

    Ends the session: the tracker has lost the eye or gaze reads far from
    where the participant looks. A person must fix this.
    """


def gaze_point(s):
    """Gaze of one sample (px from screen centre), or None if both eyes are lost."""
    eyes = []
    if s.Tracked:
        eyes.append((s.GazeX, s.GazeY))
    if s.TrackedRight:
        eyes.append((s.GazeXRight, s.GazeYRight))
    if not eyes:
        return None
    return (sum(x for x, _ in eyes) / len(eyes),
            sum(y for _, y in eyes) / len(eyes))


def read_samples():
    """Read and empty the tracker buffer.

    Every read goes through here, so the live state recorder sees every
    sample, including ones the selection ignores.
    """
    samples = LiveTrack.GetBufferedEyePositions(1, -1, 1)
    STATES.feed(samples)
    return samples


def newest_tracked():
    """Newest gaze position (px from screen centre), or None if lost.

    Shared by the fixation gate and the responder so both treat a lost eye
    the same way.
    """
    for s in reversed(read_samples()):
        pos = gaze_point(s)
        if pos is not None:
            return pos
    return None


def wait_for_central_fixation(pres, hold_ms, positions=None):
    """Wait until gaze has stayed on the central dot for hold_ms.

    positions: name positions to draw as well, or None for the dot alone.
    Leaving the dot resets the count to zero. A loss of gaze up to
    blinkTimeout_ms pauses the count; a longer one resets it.

    Raises FixationTimeout after CENTRAL_FIXATION["centralTimeout_ms"].
    """
    radius_px = CENTRAL_FIXATION['centralRadius_deg'] * geometry.px_per_deg()
    timeout_ms = CENTRAL_FIXATION['centralTimeout_ms']
    blink_gap_ms = DWELL_SELECTION['blinkTimeout_ms']

    read_samples()          # older samples: recorded as states, not judged here
    clock = core.Clock()
    held_ms = 0.0
    last = 0.0
    gap_start = None

    while held_ms < hold_ms:
        now = clock.getTime() * 1000            # PsychoPy clock is in s
        dt = now - last
        last = now

        if now > timeout_ms:
            raise FixationTimeout(
                f"central fixation not held for {hold_ms:.0f} ms "
                f"within the {timeout_ms} ms limit"
            )

        check_escape()
        pos = newest_tracked()

        if pos is None:
            if gap_start is None:
                gap_start = now
            elif now - gap_start > blink_gap_ms:
                held_ms = 0.0
        else:
            gap_start = None
            # Gaze origin is the screen centre.
            if math.hypot(*pos) <= radius_px:
                held_ms += dt
            else:
                held_ms = 0.0

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
        self.dwell_ms = DWELL_SELECTION["dwell_ms"]
        self.blink_gap_ms = DWELL_SELECTION["blinkTimeout_ms"]

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
        self.dwell_accum = 0.0    # ms
        self.last_poll = 0.0
        self.gap_start = None     # start of the current loss of gaze
        read_samples()  # samples before the cue: recorded as states, not judged

    def _restart(self, pos, here):
        self.anchor = pos
        self.dwell_on = here
        self.dwell_accum = 0.0
        self.gap_start = None

    def poll(self):
        """Read the newest gaze sample and update the dwell count."""
        if self.outcome is not None:
            return

        now = self.clock.getTime() * 1000       # PsychoPy clock is in s
        dt = now - self.last_poll
        self.last_poll = now

        pos = newest_tracked()

        # No gaze (e.g. a blink): keep the count unless the loss is too long.
        if pos is None:
            if self.gap_start is None:
                self.gap_start = now
            elif now - self.gap_start > self.blink_gap_ms:
                self.anchor = None
                self.dwell_on = None
                self.dwell_accum = 0.0
            return
        self.gap_start = None

        if (self.first_move_ms is None
                and math.hypot(*pos) > self.central_px):
            self.first_move_ms = now

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
        if self.dwell_on is not None and self.dwell_accum >= self.dwell_ms:
            self.outcome = {
                "selection": self.dwell_on,
                "selection_ms": now,
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


class GazeStateRecorder:
    """Live gaze state during a trial, sent to the tracker file on each change.

    Samples are grouped into GAZE_STATE["interval_ms"] intervals of tracker
    time. Each interval gets one state from its first tracked sample:
        g0-g7   within the selection radius of a name (once names are shown)
        centre  within the central-fixation radius
        other   anywhere else
        lost    no eye tracked in any sample of the interval
    The first tracked sample is used, not the mean: within 10 ms the gaze
    spread is about 0.1 deg against circles of about 2 deg. In session
    000000_20261023_2 the two rules gave a different state in 0.5% of
    intervals, almost all during saccades (state changes up to 10 ms later).
    A loss up to blinkTimeout_ms with the same state before and after is
    given that state (a blink). Longer losses, or a different state after,
    stay "lost".

    Changes go into one marker per frame, e.g.
        event=gaze trial=5 states=g1:12345670;g2:12355670
    with the tracker time (us) each state began. "off" ends the recording.
    merge.py turns these into the whereGaze column, so the late arrival of a
    marker does not change the recorded times.
    """

    def __init__(self):
        self.active = False

    def start(self, trial_n, positions, ring_order, name_radius_px, start_us):
        """Begin a trial's recording at tracker time start_us (dot onset)."""
        self.active = True
        self.trial_n = trial_n
        self.positions = positions
        self.ring_order = ring_order
        self.name_radius_px = name_radius_px
        self.centre_px = (CENTRAL_FIXATION["centralRadius_deg"]
                          * geometry.px_per_deg())
        self.interval_us = GAZE_STATE["interval_ms"] * 1000
        self.blink_us = DWELL_SELECTION["blinkTimeout_ms"] * 1000
        self.start_us = start_us
        self.end_us = None
        self.names_from_us = None     # names count only once they are shown
        self.interval = None          # start (us) of the interval being filled
        self.first_point = None       # first tracked gaze point in that interval
        self.samples = 0              # samples in that interval, lost included
        self.state = None             # last state sent
        self.lost_from = None         # start of a loss not yet settled
        self.lost_sent = False        # that loss is already sent as "lost"
        self.changes = []             # (state, us) not yet sent

    def show_names(self, from_us):
        """Names are on screen from tracker time from_us."""
        self.names_from_us = from_us

    def feed(self, samples):
        """Add tracker samples; send any state changes."""
        if not self.active:
            return
        for s in samples:
            t = s.Timestamp
            if t < self.start_us or (self.end_us is not None and t >= self.end_us):
                continue
            interval = t - t % self.interval_us
            if interval != self.interval:
                self._close_interval()
                self.interval = interval
            self.samples += 1
            pos = gaze_point(s)
            # Only the first tracked sample decides the interval's state.
            if pos is not None and self.first_point is None:
                self.first_point = pos
        self._send()

    def stop(self, end_us):
        """End the recording at tracker time end_us. No-op if not recording."""
        if not self.active:
            return
        self.end_us = end_us
        read_samples()                # the last samples before end_us
        self._close_interval()
        if self.lost_from is not None and not self.lost_sent:
            # Gaze did not come back before the end: not a known blink.
            self._change("lost", self.lost_from)
        self._change("off", end_us)
        self._send()
        self.active = False

    def _classify(self):
        if self.first_point is None:
            return "lost"
        x, y = self.first_point
        if self.names_from_us is not None and self.interval >= self.names_from_us:
            name = geometry.object_at((x, y), self.positions, self.ring_order,
                                      self.name_radius_px)
            if name is not None:
                return name
        return "centre" if math.hypot(x, y) <= self.centre_px else "other"

    def _close_interval(self):
        """Give the filled interval its state and update the changes."""
        if self.interval is None or self.samples == 0:
            return
        state = self._classify()
        begin = max(self.interval, self.start_us)
        end = self.interval + self.interval_us
        self.interval, self.first_point, self.samples = None, None, 0

        if state == "lost":
            if self.lost_from is None:
                self.lost_from = begin
            if not self.lost_sent and end - self.lost_from > self.blink_us:
                self._change("lost", self.lost_from)
                self.lost_sent = True
            return

        if self.lost_from is not None:
            blink = not self.lost_sent and begin - self.lost_from <= self.blink_us
            if not (blink and state == self.state) and not self.lost_sent:
                self._change("lost", self.lost_from)
            self.lost_from, self.lost_sent = None, False
        if state != self.state:
            self._change(state, begin)

    def _change(self, state, us):
        self.state = state
        self.changes.append((state, int(us)))

    def _send(self):
        if not self.changes:
            return
        text = ";".join(f"{state}:{us}" for state, us in self.changes)
        eventlog.mark("gaze", trial=self.trial_n, states=text)
        self.changes = []


# One recorder for the whole session; run_trial starts and stops it.
STATES = GazeStateRecorder()
