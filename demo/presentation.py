import sys

from psychopy import core, event, visual

import design
from config import CONTEXT, DISPLAY, GEOMETRY, NAMES, PATHS

# Key names that do not equal the character they type.
KEY_CHARS = {"space": " ", "minus": "-"}
KEY_CHARS.update({f"num_{d}": str(d) for d in range(10)})

# Question screens. PsychoPy colours run from -1 (black) to 1 (white);
# 0 is the mid-grey background.
DIM_TEXT = [0.6, 0.6, 0.6]
BOX_FILL = [-0.2, -0.2, -0.2]
OPTION_FILL = [-0.3, -0.3, -0.3]
CHOSEN_FILL = [-0.45, -0.1, -0.45]
CHOSEN_LINE = [-0.05, 0.75, -0.05]


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
        5. build the feedback highlight and feedback name text
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
            radius=GEOMETRY['feedbackCircleRadius_px'],
            fillColor=None,
            lineColor="lime",
            lineWidth=5,
        )

        # feedback name text, placed under the correct object
        self.feedback_name = visual.TextStim(
            self.win, text="", height=GEOMETRY['feedbackNameHeight_px'], color="white"
        )

        # load object images & decide ring order
        self.stims = self.load_objects()
        self.ring_order = list(self.stims)


    def load_objects(self):
        """
        Load each object's image, as worked out by design.object_image.
        output: {object_name: ImageStim}
        """
        stims = {}
        for name in CONTEXT:
            file_path = PATHS['stimDir'] / design.object_image(name)
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

    def draw_feedback(self, target, selection, positions):
        """Draw only the correct object and, after an error, the chosen one.

        correct:   correct object, its name under it, green circle around it
        incorrect: correct object with its name under it, and the chosen
                   object with a red circle around it
        timeout:   correct object with its name under it, no circle
        """
        correct_pos = positions[self.ring_order.index(target)]
        correct_stim = self.stims[target]
        correct_stim.pos = correct_pos
        correct_stim.draw()

        self.feedback_name.text = NAMES[target]
        self.feedback_name.pos = (correct_pos[0],
                                  correct_pos[1] - GEOMETRY['feedbackNameOffset_px'])
        self.feedback_name.draw()

        if selection == target:
            self.highlight.lineColor = 'lime'
            self.highlight.pos = correct_pos
            self.highlight.draw()
        elif selection is not None:
            selected_pos = positions[self.ring_order.index(selection)]
            selected_stim = self.stims[selection]
            selected_stim.pos = selected_pos
            selected_stim.draw()
            self.highlight.lineColor = 'red'
            self.highlight.pos = selected_pos
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

    def _label(self, text, y, height, color="white", bold=False, x=0,
               align="center"):
        """A text line for the question screens."""
        return visual.TextStim(self.win, text=text, pos=(x, y), height=height,
                               color=color, bold=bold, wrapWidth=900,
                               anchorHoriz=align, alignText=align)

    def type_answer(self, question, allowed, progress, hint, max_len=20,
                    is_valid=None):
        """One question with a typing box; returns what was typed.

        Only characters in `allowed` are added, up to max_len. Backspace
        deletes one character. Enter confirms once something is typed and,
        if is_valid is given, is_valid(answer) is True; otherwise Enter is
        ignored and the hint line states the rule.
        A letter is upper case when Shift or Caps Lock is on (not both).
        """
        labels = [self._label(progress, 234, 18, DIM_TEXT),
                  self._label(question, 124, 34, bold=True),
                  self._label(hint, -86, 18, DIM_TEXT),
                  self._label("Press Enter to continue", -256, 20, DIM_TEXT)]
        box = visual.Rect(self.win, width=400, height=70, pos=(0, 19),
                          fillColor=BOX_FILL, lineColor="white", lineWidth=2)
        typed = self._label("", 19, 30, x=-180, align="left")

        answer = ""
        event.clearEvents()
        while True:
            box.draw()
            typed.text = answer + "|"        # "|" marks where typing goes
            typed.draw()
            for label in labels:
                label.draw()
            self.flip()

            for key, mods in event.getKeys(modifiers=True):
                if key == "escape":
                    raise QuitRequested("escape pressed")
                if key in ("return", "num_enter") and answer:
                    if is_valid is None or is_valid(answer):
                        return answer
                    continue
                if key == "backspace":
                    answer = answer[:-1]
                    continue
                char = KEY_CHARS.get(key, key)
                if len(char) != 1:
                    continue                 # Shift, Tab, arrows, ...
                if char.isalpha() and mods.get("shift") != mods.get("capslock"):
                    char = char.upper()
                if char in allowed and len(answer) < max_len:
                    answer += char

    def choose_option(self, question, options, progress):
        """Options in stacked boxes; returns the one pressed or clicked.

        Chosen by its number key or by a mouse click. The chosen box turns
        green for 0.3 s so the participant sees what was recorded.
        """
        labels = [self._label(progress, 264, 18, DIM_TEXT),
                  self._label(question, 184, 34, bold=True),
                  self._label("Press a number or click an option", -296, 20,
                              DIM_TEXT)]
        boxes = []
        for i, option in enumerate(options):
            y = 87 - 70 * i
            boxes.append(visual.Rect(self.win, width=460, height=55, pos=(0, y),
                                     fillColor=OPTION_FILL, lineColor="white",
                                     lineWidth=1))
            labels.append(self._label(str(i + 1), y, 22, DIM_TEXT, bold=True,
                                      x=-205, align="left"))
            labels.append(self._label(option, y, 24, x=-165, align="left"))

        numbers = [str(i) for i in range(1, len(options) + 1)]
        mouse = event.Mouse(win=self.win, visible=True)
        self.win.mouseVisible = True
        event.clearEvents()

        choice = None
        while choice is None:
            for box in boxes:
                box.draw()
            for label in labels:
                label.draw()
            self.flip()

            for key in event.getKeys(keyList=numbers + ["num_" + n for n in numbers]
                                     + ["escape"]):
                if key == "escape":
                    raise QuitRequested("escape pressed")
                choice = int(key.replace("num_", "")) - 1
            for i, box in enumerate(boxes):
                if mouse.isPressedIn(box, buttons=[0]):
                    choice = i

        boxes[choice].fillColor = CHOSEN_FILL
        boxes[choice].lineColor = CHOSEN_LINE
        boxes[choice].lineWidth = 3
        for box in boxes:
            box.draw()
        for label in labels:
            label.draw()
        self.flip()
        core.wait(0.3)
        return options[choice]

    def park_mouse(self):
        """Hide the cursor and move it to the experimenter's screen.

        Moving it off the stimulus screen keeps it from sitting on the
        stimuli, even if the window shows it again. Screen 0 (the primary
        monitor) starts at (0, 0) in Windows' desktop coordinates, so its
        centre is half its width and half its height.
        """
        self.win.mouseVisible = False
        if sys.platform == "win32":
            import ctypes
            user32 = ctypes.windll.user32
            user32.SetCursorPos(user32.GetSystemMetrics(0) // 2,
                                user32.GetSystemMetrics(1) // 2)

    def close(self):
        """close the window
        """
        self.win.close()
