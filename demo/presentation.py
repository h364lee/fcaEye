import sys

from psychopy import core, event, visual

import design
import geometry
from config import DISPLAY, GEOMETRY, NAMES, ORDER, PATHS, SCREEN_TEXT
from context import CONTEXT

# Key names that do not equal the character they type.
KEY_CHARS = {"space": " ", "minus": "-", "period": ".", "comma": ",",
             "apostrophe": "'", "slash": "/", "semicolon": ";"}
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
        3. build the message text
        4. build the feedback circles and wrong mark
        5. load the object images and build the name texts
        6. decide the ring order
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

        # instruction text
        self.message = visual.TextStim(
            self.win, text="", height=24, color="white", wrapWidth=850
        )

        # feedback: green circle around the correct name and its object
        self.pair_circle = visual.Circle(
            self.win,
            radius=geometry.pair_circle_radius(),
            fillColor=None,
            lineColor="lime",
            lineWidth=5,
        )

        # feedback: red circle around a wrong name (feedbackWrongMark "o")
        self.wrong_circle = visual.Circle(
            self.win,
            radius=GEOMETRY['feedbackCircleRadius_px'],
            fillColor=None,
            lineColor="red",
            lineWidth=5,
        )

        # feedback X over a wrong choice: two crossing lines whose ends
        # touch the feedback circle's edge, so both marks are the same size
        arm = GEOMETRY['feedbackCircleRadius_px'] / 2 ** 0.5
        self.wrong_mark = [
            visual.Line(self.win, start=(-arm, -arm), end=(arm, arm),
                        lineColor="red", lineWidth=5),
            visual.Line(self.win, start=(-arm, arm), end=(arm, -arm),
                        lineColor="red", lineWidth=5),
        ]

        if GEOMETRY['feedbackWrongMark'] not in ("x", "o"):
            raise ValueError("GEOMETRY['feedbackWrongMark'] must be \"x\" or "
                             f"\"o\"; it is {GEOMETRY['feedbackWrongMark']!r}")

        # object images (centre cue, feedback) and name texts (ring)
        self.obj_images = self.load_objects()
        self.name_texts = {
            obj: visual.TextStim(self.win, text=NAMES[obj],
                                 height=GEOMETRY['height_name_px'],
                                 color="white")
            for obj in NAMES
        }
        # Selection circle around each name, from the names' real size on
        # screen (boundingBox: width, height in px). Checked here rather than
        # at startup because the size is only known once the text exists.
        sizes = [text.boundingBox for text in self.name_texts.values()]
        self.name_radius_px = geometry.name_select_radius_px(sizes)
        print(f"Name selection radius: {self.name_radius_px:.0f} px "
              f"({self.name_radius_px / geometry.px_per_deg():.2f} deg)")
        try:
            geometry.check_tolerance(self.name_radius_px)
        except ValueError:
            self.win.close()
            raise
        # slot order on the ring comes from config
        self.ring_order = list(ORDER["ringOrder"])


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

    def draw_names(self, positions):
        """Draw each object's name centred on its ring slot.
        """
        for obj, pos in zip(self.ring_order, positions):
            text = self.name_texts[obj]
            text.pos = pos
            text.draw()

    def draw_object(self, target):
        """Draw the target object in the centre (the go signal).
        """
        image = self.obj_images[target]
        image.pos = (0, 0)
        image.draw()

    def draw_feedback(self, target, selection, positions):
        """Draw the correct name with its object; all other names disappear.

        The object goes below the correct name, or above it near the
        bottom of the screen (geometry.feedback_obj_pos).

        correct:   correct name + object, green circle around the pair
        incorrect: correct name + object, green circle around the pair, and
                   the chosen name with a red X over it ("x") or a red
                   circle around it ("o") (GEOMETRY['feedbackWrongMark'])
        timeout:   correct name + object, no circle, no mark
        """
        name_pos = positions[self.ring_order.index(target)]
        obj_pos = geometry.feedback_obj_pos(name_pos)

        self.name_texts[target].pos = name_pos
        self.name_texts[target].draw()
        image = self.obj_images[target]
        image.pos = obj_pos
        image.draw()

        if selection is None:          # timeout
            return

        # halfway between name and object
        self.pair_circle.pos = ((name_pos[0] + obj_pos[0]) / 2,
                                (name_pos[1] + obj_pos[1]) / 2)
        self.pair_circle.draw()

        if selection != target:
            selected_pos = positions[self.ring_order.index(selection)]
            self.name_texts[selection].pos = selected_pos
            self.name_texts[selection].draw()
            if GEOMETRY['feedbackWrongMark'] == "x":
                for line in self.wrong_mark:
                    line.pos = selected_pos
                    line.draw()
            else:
                self.wrong_circle.pos = selected_pos
                self.wrong_circle.draw()

    def flip(self):
        """ just flip() - update the screen
        """
        return self.win.flip()

    def show_message(self, text, keys=("return", "num_enter")):
        """Draw text, flip, and wait for 'keys' to be pressed (Enter by default).
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

    def type_answer(self, question, allowed, progress="", hint="", max_len=20,
                    is_valid=None, optional=False):
        """One question with a typing box; returns what was typed.

        Only characters in `allowed` are added, up to max_len. Backspace
        deletes one character. Enter confirms once something is typed and,
        if is_valid is given, is_valid(answer) is True; otherwise Enter is
        ignored and the hint line states the rule.
        A letter is upper case when Shift or Caps Lock is on (not both).
        optional=True: Enter with nothing typed skips the question and
        returns None.
        """
        draw = self._answer_screen(question, progress, hint)
        answer = ""
        event.clearEvents()
        while True:
            draw(answer)
            self.flip()

            for key, mods in event.getKeys(modifiers=True):
                if key == "escape":
                    raise QuitRequested("escape pressed")
                if key in ("return", "num_enter") and not answer and optional:
                    return None
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

    def _answer_screen(self, question, progress="", hint=""):
        """Build the type_answer screen; returns draw(answer).

        Separate from the key loop so mockups.py can draw the screen
        without waiting for keys.
        """
        labels = [self._label(question, 124, 34, bold=True),
                  self._label("Press Enter to continue", -256, 20, DIM_TEXT)]
        if progress:
            labels.append(self._label(progress, 234, 18, DIM_TEXT))
        if hint:
            labels.append(self._label(hint, -86, 18, DIM_TEXT))
        box = visual.Rect(self.win, width=400, height=70, pos=(0, 19),
                          fillColor=BOX_FILL, lineColor="white", lineWidth=2)
        typed = self._label("", 19, 30, x=-180, align="left")

        def draw(answer):
            box.draw()
            typed.text = answer + "|"        # "|" marks where typing goes
            typed.draw()
            for label in labels:
                label.draw()
        return draw

    def choose_option(self, question, options, progress=""):
        """Options in stacked boxes; returns the one pressed or clicked.

        Chosen by its number key or by a mouse click. The chosen box turns
        green for 0.3 s so the participant sees what was recorded.
        """
        draw, boxes = self._option_screen(question, options, progress)
        numbers = [str(i) for i in range(1, len(options) + 1)]
        mouse = event.Mouse(win=self.win, visible=True)
        self.win.mouseVisible = True
        event.clearEvents()

        choice = None
        while choice is None:
            draw()
            self.flip()

            for key in event.getKeys(keyList=numbers + ["num_" + n for n in numbers]
                                     + ["escape"]):
                if key == "escape":
                    raise QuitRequested("escape pressed")
                choice = int(key.replace("num_", "")) - 1
            for i, box in enumerate(boxes):
                if mouse.isPressedIn(box, buttons=[0]):
                    choice = i

        draw(choice)
        self.flip()
        core.wait(0.3)
        return options[choice]

    def _option_screen(self, question, options, progress=""):
        """Build the choose_option screen; returns (draw(chosen=None), boxes).

        draw(i) shows box i as chosen. boxes are returned for mouse clicks.
        """
        labels = [self._label(question, 184, 34, bold=True),
                  self._label("Press a number", -296, 20, DIM_TEXT)]
        if progress:
            labels.append(self._label(progress, 264, 18, DIM_TEXT))
        boxes = []
        for i, option in enumerate(options):
            y = 87 - 70 * i
            boxes.append(visual.Rect(self.win, width=460, height=55, pos=(0, y),
                                     fillColor=OPTION_FILL, lineColor="white",
                                     lineWidth=1))
            labels.append(self._label(str(i + 1), y, 22, DIM_TEXT, bold=True,
                                      x=-205, align="left"))
            labels.append(self._label(option, y, 24, x=-165, align="left"))

        def draw(chosen=None):
            for i, box in enumerate(boxes):
                box.fillColor = CHOSEN_FILL if i == chosen else OPTION_FILL
                box.lineColor = CHOSEN_LINE if i == chosen else "white"
                box.lineWidth = 3 if i == chosen else 1
                box.draw()
            for label in labels:
                label.draw()
        return draw, boxes

    # --- post-task questions --------------------------------------------
    # All three screens are answered with the keyboard only, and all use the
    # same rule: Enter confirms; Enter with no answer skips (returns None).

    SKIP_HINT = ("Press Enter to continue. "
                 "You can press Enter without answering to skip")

    def _posttask_keys(self, keys):
        """Raise QuitRequested on Esc; return the other keys pressed."""
        if any(key == "escape" for key, _ in keys):
            raise QuitRequested("escape pressed")
        return keys

    def type_long_answer(self, question, progress="", max_len=300):
        """Open question with a large box; returns the text, or None if skipped.

        Letters, digits, space and . , ' - ; / ? can be typed, up to max_len.
        Backspace deletes one character.
        """
        draw = self._long_answer_screen(question, progress)
        answer = ""
        event.clearEvents()
        while True:
            draw(answer)
            self.flip()
            for key, mods in self._posttask_keys(event.getKeys(modifiers=True)):
                if key in ("return", "num_enter"):
                    return answer.strip() or None
                if key == "backspace":
                    answer = answer[:-1]
                    continue
                shift = mods.get("shift")
                if key == "slash" and shift:
                    char = "?"
                else:
                    char = KEY_CHARS.get(key, key)
                if len(char) != 1:
                    continue                 # Shift, Tab, arrows, ...
                if char.isalpha() and shift != mods.get("capslock"):
                    char = char.upper()
                if len(answer) < max_len:
                    answer += char

    def _long_answer_screen(self, question, progress=""):
        """Build the type_long_answer screen; returns draw(answer)."""
        labels = [self._label(question, 220, 30, bold=True),
                  self._label(self.SKIP_HINT, -290, 18, DIM_TEXT)]
        if progress:
            labels.append(self._label(progress, 300, 18, DIM_TEXT))
        box = visual.Rect(self.win, width=800, height=300, pos=(0, -20),
                          fillColor=BOX_FILL, lineColor="white", lineWidth=2)
        # top-left of the box; long answers wrap onto new lines
        typed = visual.TextStim(self.win, text="", pos=(-385, 120), height=24,
                                color="white", wrapWidth=770,
                                anchorHoriz="left", anchorVert="top",
                                alignText="left")

        def draw(answer):
            box.draw()
            typed.text = answer + "|"
            typed.draw()
            for label in labels:
                label.draw()
        return draw

    def choose_images(self, question, images, progress=""):
        """Images in a row; returns the labels chosen, or None if skipped.

        images: list of (image_path, label). Number key i turns choice i on
        or off; any number of images can be chosen.
        """
        draw = self._images_screen(question, images, progress)
        numbers = [str(i) for i in range(1, len(images) + 1)]
        chosen = set()
        event.clearEvents()
        while True:
            draw(chosen)
            self.flip()
            for key, _ in self._posttask_keys(event.getKeys(modifiers=True)):
                if key in ("return", "num_enter"):
                    if not chosen:
                        return None
                    return [images[i][1] for i in sorted(chosen)]
                digit = key.replace("num_", "")
                if digit in numbers:
                    chosen ^= {int(digit) - 1}   # on if off, off if on

    def _images_screen(self, question, images, progress=""):
        """Build the choose_images screen; returns draw(chosen)."""
        n = len(images)
        labels = [self._label(question, 220, 30, bold=True),
                  self._label(f"Press 1-{n} to choose or unchoose. "
                              "You can choose more than one.", 170, 20, DIM_TEXT),
                  self._label(self.SKIP_HINT, -290, 18, DIM_TEXT)]
        if progress:
            labels.append(self._label(progress, 300, 18, DIM_TEXT))
        stims, frames = [], []
        for i, (path, label) in enumerate(images):
            x = (i - (n - 1) / 2) * 150      # centred row, 150 px apart
            stims.append(visual.ImageStim(self.win, image=str(path),
                                          pos=(x, 0),
                                          size=GEOMETRY['objSize_px']))
            frames.append(visual.Rect(self.win, width=140, height=140,
                                      pos=(x, 0), fillColor=None,
                                      lineColor=CHOSEN_LINE, lineWidth=5))
            labels.append(self._label(str(i + 1), 95, 22, DIM_TEXT, bold=True, x=x))
            labels.append(self._label(label, -95, 20, x=x))

        def draw(chosen):
            for i, stim in enumerate(stims):
                stim.draw()
                if i in chosen:
                    frames[i].draw()
            for label in labels:
                label.draw()
        return draw

    def rate_scale(self, question, low_label, high_label, n_points=7,
                   progress=""):
        """A 1..n_points rating; returns the number, or None if skipped.

        A number key selects that point (a new key replaces it).
        """
        draw = self._scale_screen(question, low_label, high_label, n_points,
                                  progress)
        numbers = [str(i) for i in range(1, n_points + 1)]
        rating = None
        event.clearEvents()
        while True:
            draw(rating)
            self.flip()
            for key, _ in self._posttask_keys(event.getKeys(modifiers=True)):
                if key in ("return", "num_enter"):
                    return rating
                digit = key.replace("num_", "")
                if digit in numbers:
                    rating = int(digit)

    def _scale_screen(self, question, low_label, high_label, n_points,
                      progress=""):
        """Build the rate_scale screen; returns draw(rating)."""
        labels = [self._label(question, 220, 30, bold=True),
                  self._label(f"Press 1-{n_points} (1 = {low_label}, "
                              f"{n_points} = {high_label})", 170, 20, DIM_TEXT),
                  self._label(self.SKIP_HINT, -290, 18, DIM_TEXT)]
        if progress:
            labels.append(self._label(progress, 300, 18, DIM_TEXT))
        boxes = []
        for i in range(n_points):
            x = (i - (n_points - 1) / 2) * 100
            boxes.append(visual.Rect(self.win, width=80, height=60, pos=(x, 20),
                                     lineWidth=1))
            labels.append(self._label(str(i + 1), 20, 26, bold=True, x=x))
        first_x = boxes[0].pos[0]
        last_x = boxes[-1].pos[0]
        labels.append(self._label(low_label, -40, 20, DIM_TEXT, x=first_x))
        labels.append(self._label(high_label, -40, 20, DIM_TEXT, x=last_x))

        def draw(rating):
            for i, box in enumerate(boxes):
                on = rating == i + 1
                box.fillColor = CHOSEN_FILL if on else OPTION_FILL
                box.lineColor = CHOSEN_LINE if on else "white"
                box.lineWidth = 3 if on else 1
                box.draw()
            for label in labels:
                label.draw()
        return draw

    # --- end of session ---------------------------------------------------
    # The feedback letter is drawn like a printed sheet: a light page on the
    # gray screen, dark text, bold centred title, bold headings, left-aligned
    # body, page number at the bottom.

    LETTER_FONT = "Times New Roman"  # installed on macOS and Windows
    SHEET_SIZE = (800, 720)         # width, height of the page, px
    SHEET_MARGIN = 50               # page edge to text, px
    LETTER_STYLES = {               # kind: (letter height px, bold, alignment)
        "title": (24, True, "center"),
        "heading": (20, True, "left"),
        "body": (16, False, "left"),
    }

    def _letter_paragraphs(self):
        """Read the letter file; returns [(kind, text), ...].

        Paragraphs are separated by an empty line. "# " starts the title,
        "## " a heading; "# " notes before the title are skipped.
        """
        text = PATHS["debriefLetter"].read_text(encoding="utf-8")
        paragraphs = []
        for block in text.strip().split("\n\n"):
            block = block.strip()
            if block.startswith("## "):
                paragraphs.append(("heading", block[3:]))
            elif block.startswith("# "):
                if not paragraphs and all(line.startswith("#") for line in block.splitlines()) \
                        and "\n" in block:
                    continue                     # notes at the top of the file
                paragraphs.append(("title", block[2:]))
            elif block:
                paragraphs.append(("body", block))
        return paragraphs

    def _text_height(self, stim, height):
        """Height of a wrapped TextStim in px.

        Uses PsychoPy's measured size; if this PsychoPy version does not
        provide it, estimates from the number of characters.
        """
        try:
            return stim.boundingBox[1]
        except (AttributeError, TypeError):
            chars_per_line = stim.wrapWidth / (0.5 * height)
            lines = sum(max(1, -(-len(line) // int(chars_per_line)))
                        for line in stim.text.split("\n"))
            return lines * height * 1.25

    def _debrief_pages(self):
        """Lay the letter out on sheet pages; returns a list of pages, each
        a list of positioned TextStims. A paragraph that would run past the
        bottom of the sheet starts the next page."""
        w, h = self.SHEET_SIZE
        text_w = w - 2 * self.SHEET_MARGIN
        top = h / 2 - self.SHEET_MARGIN + 10          # sheet centre is y = 10
        bottom = -h / 2 + self.SHEET_MARGIN + 30      # leaves room for the page number
        pages, y = [[]], top
        for kind, text in self._letter_paragraphs():
            size, bold, align = self.LETTER_STYLES[kind]
            x = 0 if align == "center" else -text_w / 2
            stim = visual.TextStim(self.win, text=text, height=size, bold=bold,
                                   font=self.LETTER_FONT,
                                   color="black", wrapWidth=text_w,
                                   anchorHoriz=align, anchorVert="top",
                                   alignText=align, pos=(x, y))
            needed = self._text_height(stim, size)
            if y - needed < bottom and pages[-1]:
                pages.append([])
                y = top
            stim.pos = (x, y)
            pages[-1].append(stim)
            y -= needed + 0.9 * size                  # space after each paragraph
        return pages

    def _debrief_screen(self):
        """Build the end screens; returns (draw(screen_n), n_screens).

        Screen 0 is the thank-you message; screens 1.. are letter pages.
        """
        pages = self._debrief_pages()
        w, h = self.SHEET_SIZE
        sheet = visual.Rect(self.win, width=w, height=h, pos=(0, 10),
                            fillColor=[0.95, 0.95, 0.95], lineColor=[0.5, 0.5, 0.5],
                            lineWidth=1)
        page_number = visual.TextStim(self.win, text="", pos=(0, 10 - h / 2 + 25),
                                      height=14, color=[-0.4, -0.4, -0.4],
                                      font=self.LETTER_FONT)
        hint = self._label("Press Enter to continue", -372, 14, DIM_TEXT)
        thanks = self._label(SCREEN_TEXT["thankYou"], 0, 28)

        def draw(screen_n):
            if screen_n == 0:
                thanks.draw()
                return
            sheet.draw()
            for stim in pages[screen_n - 1]:
                stim.draw()
            page_number.text = f"Page {screen_n} of {len(pages)}"
            page_number.draw()
            hint.draw()
        return draw, len(pages) + 1

    def show_debrief(self):
        """Thank-you message, then the letter, one page per Enter press.

        Esc leaves the letter early without raising QuitRequested: the
        session's data are already saved, so this is not an abort.
        """
        draw, n_screens = self._debrief_screen()
        for screen_n in range(n_screens):
            draw(screen_n)
            self.flip()
            key = event.waitKeys(keyList=["return", "num_enter", "escape"])[0]
            if key == "escape":
                return

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
