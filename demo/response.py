"""Collecting a response.

One interface, several implementations. The trial code holds a Responder and
never knows which kind it is -- that is what will let the eye tracker replace
the mouse by changing one line in a factory rather than editing trial code.

The interface is polled, not blocking, because the trial loop also has to
keep drawing and checking for quit.
"""

import math

from psychopy import core, event

import geometry
from config import GEOMETRY, TIMING


class Responder:
    """Base interface.

    Lifecycle:
        start()   once, at cue onset
        poll()    once per frame
        result()  each frame; returns None until a selection is made
    """

    def start(self):
        """Reset clock and internal state. Called at cue onset."""
        raise NotImplementedError

    def poll(self):
        """Read the input device once and update internal state."""
        raise NotImplementedError

    def result(self):
        """The outcome so far.

        Returns:
            None while no selection has been made, otherwise a dict with
                selection       object name
                selection_ms    time from start() to selection
                first_move_ms   time the pointer first left the centre, or
                                None if it has not
        """
        raise NotImplementedError


class ClickResponder(Responder):
    """Selection by clicking an object. Used in training.

    Free viewing: looking at an object costs nothing, so participants can
    inspect before answering.
    """

    def __init__(self, window, positions, ring_order):
        """Store what every poll will need.

        Flow:
            1. build a mouse attached to this window
            2. store positions and ring_order for the hit test
            3. build a clock
            4. set outcome to None -- no selection yet

        Note:
            positions and ring_order are stored, not recomputed. They are
            facts about this trial that the caller already decided.
        """
        self.mouse = event.Mouse(win=window)
        self.positions = positions
        self.ring_order = ring_order
        self.clock = core.Clock()
        self.outcome = None

    def start(self):
        """Reset for a new trial.

        Flow:
            1. reset the clock to zero
            2. clear any click that happened before now
            3. clear the stored outcome
        """
        self.clock.reset()
        self.mouse.clickReset()
        self.outcome = None

    def poll(self):
        """Read the mouse once.

        Flow:
            1. if an outcome already exists, do nothing
            2. if the left button is down:
                 a. ask geometry which object the pointer is on
                 b. if it is on one, store the outcome

        Note:
            getPressed() returns one entry per button; [0] is the left one.
            getTime() is in seconds, so multiply by 1000 for milliseconds.
        """
        if self.outcome is not None:
            return

        if self.mouse.getPressed()[0]:
            hit = geometry.object_at(self.mouse.getPos(), self.positions, self.ring_order)
            if hit is not None:
                self.outcome = {
                    "selection": hit,
                    "selection_ms": self.clock.getTime() * 1000,
                    "first_move_ms": None,
                }

    def result(self):
        """Return the stored outcome, or None if there is not one yet."""
        return self.outcome


class DwellResponder(Responder):
    """Selection by resting the pointer on an object for dwell_ms.

    Stands in for gaze dwell while there is no tracker.

    State carried between polls:
        dwell_on       the object the pointer is currently sitting on
        dwell_start    the time it arrived there
        first_move_ms  when the pointer first left the centre

    Decision recorded here: leaving an object before the dwell completes
    RESETS the dwell. Time does not accumulate across separate visits.
    """

    def __init__(self, window, positions, ring_order):
        """Same as ClickResponder, plus the dwell threshold.

        Flow:
            1. mouse, positions, ring_order, clock
            2. read dwell_ms from TIMING
            3. set outcome, dwell_on, dwell_start, first_move_ms to None
        """
        self.mouse = event.Mouse(win=window)
        self.positions = positions
        self.ring_order = ring_order
        self.clock = core.Clock()
        self.dwell_ms = TIMING['dwell_ms']

        self.outcome = None
        self.dwell_on = None
        self.dwell_start = None
        self.first_move_ms = None

    def start(self):
        """Reset for a new trial.

        Flow:
            1. reset the clock
            2. clear outcome, dwell_on, dwell_start, first_move_ms
        """
        self.clock.reset()
        self.outcome = None
        self.dwell_on = None
        self.dwell_start = None
        self.first_move_ms = None

    def poll(self):
        """Read the pointer once and update the dwell.

        Flow:
            1. if an outcome already exists, do nothing
            2. read the pointer position and the current time
            3. if the pointer has left the centre and first_move_ms is not
               set yet, record it
            4. ask geometry which object the pointer is on (may be None)
            5. if that is different from dwell_on:
                 the pointer just moved somewhere new -- store the new
                 object and restart the dwell clock
               otherwise, if it is on an object and enough time has passed:
                 store the outcome

        Note:
            math.hypot(x, y) is the distance from the centre.
            Step 5 is the reset decision: arriving somewhere new always
            restarts the timer, so time never accumulates across visits.
        """
        if self.outcome is not None:
            return

        pos = self.mouse.getPos()
        now = self.clock.getTime()

        if self.first_move_ms is None and math.hypot(pos[0], pos[1]) > GEOMETRY['target_tolerance_px']:
            self.first_move_ms = now * 1000

        here = geometry.object_at(pos, self.positions, self.ring_order)

        if here != self.dwell_on:
            self.dwell_on = here
            self.dwell_start = now
        elif here is not None and (now - self.dwell_start) * 1000 >= self.dwell_ms:
            self.outcome = {
                "selection": here,
                "selection_ms": now * 1000,
                "first_move_ms": self.first_move_ms,
            }

    def result(self):
        """Return the stored outcome, or None if there is not one yet."""
        return self.outcome


def make_responder(kind, window, positions, ring_order):
    """Build the responder named in the phase config.

    The single place that knows which class goes with which name. Adding the
    gaze version later means adding one line here.

    Flow:
        1. if kind is "click", build a ClickResponder
        2. if kind is "dwell", build a DwellResponder
        3. otherwise raise an error naming the unknown kind

    Args:
        kind: the string from PHASES[...]["responder"].

    Returns:
        a Responder.
    """
    if kind == 'click':
        return ClickResponder(window, positions, ring_order)
    if kind == 'dwell':
        return DwellResponder(window, positions, ring_order)
    raise ValueError(f"unknown responder kind: {kind}")
