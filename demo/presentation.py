import json
from pathlib import Path

from psychopy import event, visual

from config import DISPLAY, GEOMETRY, NAMES, PATHS


class QuitRequested(Exception):
    """Escape was pressed. Stop the session."""


def check_quit():
    """Raise QuitRequested if escape has been pressed since the last check.

    Called once per frame from every loop that can run for a while.

    Raising rather than calling core.quit() is deliberate: core.quit() calls
    sys.exit() from inside pyglet's key handler, and pyglet swallows the
    exception, so the script carries on and the caller's cleanup never runs.
    An exception raised here travels up normally, so the finally blocks that
    close LiveTrack and the window still execute.
    """
    if event.getKeys(keyList=['escape']):
        raise QuitRequested("escape pressed")


class Presentation:
    """
    Class for the window and drawable objects
    """

    def __init__(self):
        """
        1. open the window
        2. build the fixation dot
        3. build the cue text
        4. build the message text
        5. build the feedback highlight
        6. load the object images
        7. decide the ring order
        """
        # window parameters from config.py
        self.win = visual.Window(
            size=DISPLAY['size'],
            screen=DISPLAY['screen'],
            units=DISPLAY['units'],
            color=DISPLAY['bgColour'],
            fullscr=DISPLAY['fullscreen'],
            allowGUI=True,
        )


        # fixation dot
        self.fixation = visual.Circle(
            self.win,
            radius=GEOMETRY['centralDotRadius_px'],
            fillColor="white",
            lineColor="white",
        )

        # cue name text
        self.cue_text = visual.TextStim(
            self.win, text="", height=36, color="white", pos=(0, 0)
        )

        # instruction text
        self.message = visual.TextStim(
            self.win, text="", height=24, color="white", wrapWidth=850
        )

        # feedback highlight circle
        self.highlight = visual.Circle(
            self.win,
            radius=GEOMETRY['objSize_px'] * 0.62,
            fillColor=None,
            lineColor="lime",
            lineWidth=5,
        )

        # load object images & decide ring order
        self.stims = self.load_objects()
        self.ring_order = list(self.stims)


    def load_objects(self):
        """
        Take manifest.json and object_assignment and return visual.ImageStim for each object.
        output: {object_name: ImageStim}
        """
        stim_dir = Path(PATHS['stimDir'])
        manifest = json.loads((stim_dir / 'manifest.json').read_text())

        stims = {}
        for name, code in manifest['object_assignment'].items():
            file_path = stim_dir / manifest['objects'][code]['file']
            stims[name] = visual.ImageStim(self.win, image=str(file_path),
                                           size=GEOMETRY['objSize_px'])
        return stims

    def draw_fixation(self):
        """Draw the central dot
        """
        self.fixation.draw()

    def draw_array(self, positions):
        """Place each object at its slot and draw it. 
        """
        for name, pos in zip(self.ring_order, positions):
            stim = self.stims[name]
            stim.pos = pos
            stim.draw()

    def draw_cue(self, name):
        """Draw cue name for the object at the centre.
        """
        self.cue_text.text = NAMES[name]
        self.cue_text.draw()

    def draw_feedback(self, correct_pos, selected_pos=None):
        """Mark the correct object green; mark a wrong selection red.
        """
        if selected_pos is not None and selected_pos!= correct_pos:
            self.highlight.lineColor = 'red'
            self.highlight.pos = selected_pos
            self.highlight.draw()

        self.highlight.lineColor = 'green'
        self.highlight.pos = correct_pos
        self.highlight.draw()


    def flip(self):
        """ just flip() - update the screen
        """
        return self.win.flip()

    def show_message(self, text, keys=("space",)):
        """Draw text, flip, and wait for 'keys' to be pressed.
        """
        self.message.text = text
        self.message.draw()
        self.flip()

        pressed = event.waitKeys(keyList=list(keys) + ['escape'])
        if pressed[0] == 'escape':
            raise QuitRequested("escape pressed")
        return pressed[0]

    def close(self):
        """close the window
        """
        self.win.close()
