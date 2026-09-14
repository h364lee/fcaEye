"""
Window, stimuli, and drawing.
"""

import json
from pathlib import Path

from psychopy import event, visual

from config import DISPLAY, GEOMETRY, NAMES, PATHS


class Presentation:
    """Holds the window and every drawable object.

    One instance is built at startup and passed to the trial code, so nothing
    downstream has to know how stimuli were created.
    """

    def __init__(self):
        """

        Flow:
            1. open the window
            2. build the fixation dot
            3. build the cue text
            4. build the message text
            5. build the feedback highlight
            6. load the object images
            7. decide the ring order
        """
        self.win = visual.Window(
            size=DISPLAY['size'],
            units=DISPLAY['units'],
            color=DISPLAY['background'],
            fullscr=DISPLAY['fullscreen'],
            allowGUI=True,
        )

        self.fixation = visual.Circle(
            self.win,
            radius=GEOMETRY['fixation_px'] / 2, # diameter -> radius
            fillColor="white",
            lineColor="white",
        )

        self.cue_text = visual.TextStim(
            self.win, text="", height=36, color="white", pos=(0, 0)
        )

        self.message = visual.TextStim(
            self.win, text="", height=24, color="white", wrapWidth=850
        )

        self.highlight = visual.Circle(
            self.win,
            radius=GEOMETRY['object_px'] * 0.62,
            fillColor=None,
            lineColor="lime",
            lineWidth=5,
        )

        self.stims = self.load_objects()
        self.ring_order = list(self.stims)

    # --- loading ---------------------------------------------------------

    def load_objects(self):
        """
        Flow:
            1. build the path to stims/manifest.json
            2. read that file into a dictionary
            3. start an empty dictionary for the results
            4. for each object name and its feature code in object_assignment:
                 a. look up that code in manifest["objects"] to get its "file"
                 b. join stim_dir + that file to get the full path
                 c. make an ImageStim and store it under the object name
            5. return the dictionary

        Manifest shape:
            manifest["object_assignment"]  ->  {"g1": "square-dots-sparse", ...}
            manifest["objects"]["square-dots-sparse"]["file"]
                                           ->  "objects/square-dots-sparse.png"

        Returns:
            {object_name: ImageStim}
        """
        stim_dir = Path(PATHS['stim_dir'])
        manifest = json.loads((stim_dir / 'manifest.json').read_text())

        stims = {}
        for name, code in manifest['object_assignment'].items():
            file_path = stim_dir / manifest['objects'][code]['file']
            stims[name] = visual.ImageStim(self.win, image=str(file_path),
                                           size=GEOMETRY['object_px'])
        return stims

    # --- drawing ---------------------------------------------------------

    def draw_fixation(self):
        """Draw the central dot.Does not flip.
        """
        self.fixation.draw()

    def draw_array(self, positions):
        """Place each object at its slot and draw it. Does not flip.

        Flow:
            1. for each object name and position, walked together:
                 a. look up that object's image in self.stims
                 b. set its .pos to that position
                 c. call .draw() on it
        Args:
            positions: output of geometry.ring_positions, in slot order.
        """
        for name, pos in zip(self.ring_order, positions):
            stim = self.stims[name]
            stim.pos = pos
            stim.draw()

    def draw_cue(self, name):
        """Draw the name at the centre, where the dot was. Does not flip.

        Flow:
            1. look up the word for this object in NAMES
            2. put that word into self.cue_text by setting its .text
            3. draw it

        Args:
            name: an object name such as "g1".
        """
        self.cue_text.text = NAMES[name]
        self.cue_text.draw()

    def draw_feedback(self, correct_pos, selected_pos=None):
        """Mark the correct object green; mark a wrong selection red.

        Flow:
            1. if a wrong object was selected:
                 a. set self.highlight.lineColor to red
                 b. set self.highlight.pos to selected_pos
                 c. draw it
            2. set self.highlight.lineColor to green
            3. set self.highlight.pos to correct_pos
            4. draw it

        Args:
            correct_pos: (x, y) of the correct object.
            selected_pos: (x, y) of what was selected, or None if the trial
                timed out or the selection was correct.
        """
        if selected_pos is not None and selected_pos!= correct_pos:
            self.highlight.lineColor = 'red'
            self.highlight.pos = selected_pos
            self.highlight.draw()

        self.highlight.lineColor = 'green'
        self.highlight.pos = correct_pos
        self.highlight.draw()

    # --- screen-level ----------------------------------------------------

    def flip(self):
        """Update the screen. Returns the flip time.
            1. call .flip() on the window and return what it gives back

        Note:
            Everything drawn since the last flip appears now. This is the
            only place the screen changes, and the moment the eye tracker
            marker will attach to later.
        """
        return self.win.flip()

    def show_message(self, text, keys=("space",)):
        """Draw text, flip, and wait for one of `keys`.

        Flow:
            1. put `text` into self.message
            2. draw it
            3. flip
            4. wait for a key press from `keys`
            5. return the first key that came back

        Returns:
            the key that was pressed.
        """
        self.message.text = text
        self.message.draw()
        self.flip()

        pressed = event.waitKeys(keyList=list(keys))
        return pressed[0]

    def close(self):
        """Shut the window down.
            1. call .close() on the window
        """
        self.win.close()
