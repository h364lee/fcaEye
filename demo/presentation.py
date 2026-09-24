from psychopy import event, visual

from config import DISPLAY, GEOMETRY, NAMES, OBJECTS, PATHS

# Key names that do not equal the character they type.
KEY_CHARS = {"space": " ", "minus": "-"}
KEY_CHARS.update({f"num_{d}": str(d) for d in range(10)})


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
        Load the image file listed in config.OBJECTS for each object.
        output: {object_name: ImageStim}
        """
        stims = {}
        for name, file_name in OBJECTS.items():
            file_path = PATHS['stimDir'] / file_name
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

    def type_answer(self, question, allowed):
        """Show a question and let the participant type the answer on screen.

        Only characters in `allowed` are added. Backspace deletes one
        character; Enter confirms, but only once something has been typed.
        Letters are typed in lower case.
        """
        answer = ""
        event.clearEvents()
        while True:
            self.message.text = (f"{question}\n\n{answer}_\n\n"
                                 "(Enter to confirm, Backspace to delete)")
            self.message.draw()
            self.flip()

            for key in event.getKeys():
                if key == "escape":
                    raise QuitRequested("escape pressed")
                if key in ("return", "num_enter") and answer:
                    return answer
                char = KEY_CHARS.get(key, key)
                if key == "backspace":
                    answer = answer[:-1]
                elif len(char) == 1 and char in allowed:
                    answer += char

    def choose_option(self, question, options):
        """Show numbered options and return the one whose number is pressed."""
        numbers = [str(i) for i in range(1, len(options) + 1)]
        lines = [f"{n}. {option}" for n, option in zip(numbers, options)]
        self.message.text = (question + "\n\n" + "\n".join(lines)
                             + "\n\n(Press the number)")
        self.message.draw()
        self.flip()

        event.clearEvents()
        pressed = event.waitKeys(keyList=numbers + [f"num_{n}" for n in numbers]
                                 + ["escape"])
        if pressed[0] == "escape":
            raise QuitRequested("escape pressed")
        return options[int(pressed[0].replace("num_", "")) - 1]

    def close(self):
        """close the window
        """
        self.win.close()
