import functools
import sys

from psychopy import core, event, visual
from psychopy.visual.textbox2 import textbox2 as _tb2

import design
import geometry
from config import (DISPLAY, GEOMETRY, NAV_TEXT, PAGE_STYLE, PATHS,
                    PAUSE_BUTTONS, SCREEN_TEXT)

# Key names that do not equal the character they type.
KEY_CHARS = {"space": " ", "minus": "-", "period": ".", "comma": ",",
             "apostrophe": "'", "slash": "/", "semicolon": ";"}
KEY_CHARS.update({f"num_{d}": str(d) for d in range(10)})

def _rgb(hex_colour):
    """"#RRGGBB" -> PsychoPy rgb, each channel from -1 to 1."""
    h = hex_colour.lstrip("#")
    return [int(h[i:i + 2], 16) / 127.5 - 1 for i in (0, 2, 4)]


# Question screens: dark text and light boxes on the off-white background,
# in the colours of PAGE_STYLE.
INK = _rgb(PAGE_STYLE["ink"])
DIM_TEXT = _rgb(PAGE_STYLE["muted"])
BOX_FILL = _rgb(PAGE_STYLE["box"])          # typing boxes, options
BOX_LINE = _rgb(PAGE_STYLE["boxLine"])
OPTION_FILL = BOX_FILL
CHOSEN_FILL = _rgb(PAGE_STYLE["chosen"])
CHOSEN_LINE = _rgb(PAGE_STYLE["accent"])

# The bundled page fonts. TextBox2 finds them once registered (_build_page);
# TextStim needs them passed as fontFiles each time.
FONT_FILES = [str(f) for f in sorted(PATHS["fontDir"].glob("*.ttf"))]
# TextStim takes the first matching file of a family, so each weight gets
# only its own file.
FONT_BODY = [str(PATHS["fontDir"] / "SourceSans3-Regular.ttf")]
FONT_BODY_BOLD = [str(PATHS["fontDir"] / "SourceSans3-Semibold.ttf")]
FONT_TITLE = [str(PATHS["fontDir"] / "SourceSerif4Display-Regular.ttf")]


def _on_paper(method):
    """Run a text screen on the off-white background, then restore the
    background it had before (grey during calibration and trials).

    Used as a decorator on every Presentation method that shows a text
    screen. Nesting is safe: the pause screen inside an instruction page
    restores off-white, and the page restores grey when it closes.
    """
    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        previous = list(self.win.color)
        self.set_background(PAGE_STYLE["paper"])
        try:
            return method(self, *args, **kwargs)
        finally:
            self.win.color = previous
            self.win.clearBuffer()
    return wrapper


class EndSession(Exception):
    """The researcher chose End on the pause screen, or Esc after a failed
    calibration. The data written so far stay saved and the session goes
    to the debrief letter."""


class RestartBlock(Exception):
    """The researcher chose Continue on the pause screen during the trials.

    The current trial and block are abandoned and the block starts again.
    recalibrate: True if the researcher asked for a calibration first.
    """

    def __init__(self, recalibrate):
        super().__init__("block abandoned")
        self.recalibrate = recalibrate


# The Presentation that draws the pause screen. Set in Presentation.__init__,
# because check_escape() is also called from calibrate.py and response.py,
# which have no Presentation of their own.
_pres = None

# True only while trials run. It decides what Continue does: during trials
# it abandons the block; at any other time the same screen carries on.
_trials_running = False


def set_trials_running(running):
    """experiment.py calls this when trials start and stop."""
    global _trials_running
    _trials_running = running


def check_escape():
    """Open the pause screen if Esc has been pressed since the last check.

    Called once per frame from every loop that can run for a while.
    Returns normally if the participant carries on where they were;
    otherwise raises EndSession or RestartBlock (see pause_menu).

    Raising rather than calling core.quit() is deliberate: core.quit() calls
    sys.exit() from inside pyglet's key handler, and pyglet swallows the
    exception, so the script carries on and the caller's cleanup never runs.
    An exception raised here travels up normally, so the finally blocks that
    close LiveTrack and the window still execute.
    """
    if event.getKeys(keyList=['escape']):
        pause_menu()


def pause_menu():
    """Pause screen: the participant is asked to call the researcher.

    The researcher clicks an option with the mouse:
        Continue                    -> outside a block: return, the same
                                       screen goes on; inside a block:
                                       raise RestartBlock
        Recalibrate, then continue  -> (inside a block only)
                                       raise RestartBlock(recalibrate=True)
        End session                 -> confirm, then raise EndSession
    """
    if _pres is None:                   # no window yet: nothing to show
        raise EndSession("Esc before the window opened")

    print("\nPAUSED. Click an option on the stimulus screen.")
    if _trials_running:
        options = ["continue", "recalibrate", "end"]
    else:
        options = ["continue", "end"]

    while True:
        chosen = options[_pres.choose_button(
            SCREEN_TEXT["pause"][0], [PAUSE_BUTTONS[o] for o in options],
            danger=(options.index("end"),))]
        if chosen != "end":
            break
        # Ending cannot be undone, so it is confirmed once
        confirm = _pres.choose_button(
            SCREEN_TEXT["endConfirm"][0],
            [PAUSE_BUTTONS["back"], PAUSE_BUTTONS["endConfirm"]],
            danger=(1,))
        if confirm == 1:
            raise EndSession("researcher chose End on the pause screen")

    print(f"Researcher chose: {chosen}")
    event.clearEvents()                 # drop keys pressed during the pause
    if not _trials_running:
        return
    raise RestartBlock(recalibrate=(chosen == "recalibrate"))


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

        # Object images (centre cue, feedback), name texts (ring) and ring
        # order come from the stimulus set in use. phase1 until use_set() is
        # called.
        self._built_sets = {}
        self.use_set(design.stimulus_sets()["phase1"])

        self._build_page()
        self._mouse_parked = False      # set by park_mouse

        # the pause screen is drawn in this window
        global _pres
        _pres = self


    def use_set(self, stim_set):
        """Show this stimulus set (a design.StimulusSet) from now on.

        Each set's images and names are built once and kept, so switching
        back to a set does not load its images again.
        """
        if stim_set.label not in self._built_sets:
            names = {obj: visual.TextStim(self.win, text=name,
                                          height=GEOMETRY['height_name_px'],
                                          color="white")
                     for obj, name in stim_set.names.items()}
            self._built_sets[stim_set.label] = (self._load_objects(stim_set),
                                                names)
        self.obj_images, self.name_texts = self._built_sets[stim_set.label]
        self.ring_order = list(stim_set.ring_order)
        self.stim_set = stim_set

    def _load_objects(self, stim_set):
        """{object: drawable}: the image files, or white circles when the
        set has no images (practice). Both have .pos and .draw(), so the
        drawing code treats them the same."""
        if stim_set.images is None:
            return {obj: visual.Circle(self.win,
                                       radius=GEOMETRY['objSize_px'] / 2,
                                       fillColor="white", lineColor="white")
                    for obj in stim_set.names}
        return {obj: visual.ImageStim(self.win,
                                      image=str(stim_set.stim_dir / file_name),
                                      size=GEOMETRY['objSize_px'])
                for obj, file_name in stim_set.images.items()}

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

    def set_background(self, hex_colour):
        """Change the window background now (the next drawing uses it)."""
        self.win.color = _rgb(hex_colour)
        self.win.clearBuffer()

    def flip(self):
        """ just flip() - update the screen
        """
        return self.win.flip()

    # --- text pages ------------------------------------------------------
    # One look for every text screen: a dark card with a title, a line, the
    # body, and a footer with the keys and page dots.

    def _build_page(self):
        """Create the page stimuli once; draw_page only changes their text.

        Layout, top to bottom, all left edges on one column:
            page count ("2 OF 4", several pages only)
            title (serif), short accent line
            body (sans)
            hairline; footer: Back, page marks, Next
        """
        st = PAGE_STYLE
        # The bundled fonts, so TextBox2 finds them by family name
        _tb2.allFonts.addFontFiles(FONT_FILES)

        w, h = st["sheetSize"]
        top, bottom = h / 2, -h / 2
        left, right = -st["columnWidth"] / 2, st["columnWidth"] / 2
        self._col = (left, right, top, bottom)

        self._page_count = self._text(st["bodyFont"], 14, st["accent"],
                                      (left, top - 56), (right - left, 22),
                                      bold=True)
        self._page_title = self._text(st["titleFont"], st["titleHeight"],
                                      st["ink"], (left, top - 84),
                                      (right - left, 60))
        self._page_rule = visual.Rect(self.win, width=44, height=3,
                                      pos=(left + 22, top - 158),
                                      fillColor=_rgb(st["accent"]),
                                      lineColor=None)
        self._page_body = self._text(st["bodyFont"], st["bodyHeight"],
                                     st["body"], (left, top - 196),
                                     (right - left, 330),
                                     lineSpacing=st["lineSpacing"])
        footer_y = bottom + 44
        self._footer_y = footer_y
        self._hairline = visual.Line(self.win, start=(left, bottom + 74),
                                     end=(right, bottom + 74),
                                     lineColor=_rgb(st["hairline"]),
                                     lineWidth=1)
        self._page_back = self._text(st["bodyFont"], 18, st["muted"],
                                     (left, footer_y), (200, 30),
                                     anchor="left", text=NAV_TEXT["back"])
        self._page_next = self._text(st["bodyFont"], 18, st["ink"],
                                     (right, footer_y), (200, 30),
                                     anchor="right", bold=True)
        self._page_mark = visual.Rect(self.win, width=26, height=3,
                                      lineColor=None)

    def _text(self, font, height, colour, pos, size, anchor="top-left",
              text="", **kwargs):
        """A TextBox2 whose text starts exactly at pos (no padding)."""
        return visual.TextBox2(
            self.win, text=text, font=font, letterHeight=height,
            color=_rgb(colour), units="pix", pos=pos, size=size,
            anchor=anchor, alignment=anchor, padding=0, **kwargs)

    def draw_page(self, pages, index, nav=True, fill=None):
        """Draw page 'index' of 'pages' (a list of (title, body)); no flip.

        nav=False leaves out the footer (screens where the participant
        presses nothing). fill: values for {} fields, e.g. {"round": 2}.
        """
        st = PAGE_STYLE
        title, body = pages[index]
        if fill:
            title, body = title.format(**fill), body.format(**fill)
        if len(pages) > 1:
            self._page_count.text = f"{index + 1} OF {len(pages)}"
            self._page_count.draw()
        self._page_title.text = title
        self._page_title.draw()
        self._page_rule.draw()
        self._page_body.text = body
        self._page_body.draw()
        if not nav:
            return

        self._hairline.draw()
        if index > 0:
            self._page_back.draw()
        last = index == len(pages) - 1
        self._page_next.text = NAV_TEXT["last"] if last else NAV_TEXT["next"]
        self._page_next.draw()
        if len(pages) > 1:              # one mark per page, current in accent
            for i in range(len(pages)):
                self._page_mark.pos = ((i - (len(pages) - 1) / 2) * 34,
                                       self._footer_y)
                self._page_mark.fillColor = _rgb(
                    st["accent"] if i == index else st["hairline"])
                self._page_mark.draw()

    @_on_paper
    def show_pages(self, pages, fill=None, escape_exits=False):
        """Show text pages; right arrow = next, left arrow = back.

        Returns after the right arrow on the last page.
        Esc opens the pause screen; after Continue the same page is shown
        again. escape_exits=True: Esc just returns instead (last screen).
        """
        index = 0
        event.clearEvents()
        while True:
            self.draw_page(pages, index, fill=fill)
            self.flip()
            key = event.waitKeys(keyList=["right", "left", "escape"])[0]
            if key == "right":
                if index == len(pages) - 1:
                    return
                index += 1
            elif key == "left":
                index = max(0, index - 1)
            elif escape_exits:
                return
            else:
                pause_menu()

    @_on_paper
    def show_waiting(self, pages, keys):
        """One page without a footer, until one of 'keys' is pressed (by the
        researcher); returns that key. The participant presses nothing."""
        self.draw_page(pages, 0, nav=False)
        self.flip()
        event.clearEvents()
        return event.waitKeys(keyList=list(keys))[0]

    @_on_paper
    def choose_button(self, page, labels, danger=()):
        """Show one page with clickable buttons; return the clicked index.

        For the researcher (pause screen). danger: indexes of buttons drawn
        in the warning colour. The cursor is shown and moved onto the
        stimulus screen, then hidden again afterwards if it was parked.
        """
        st = PAGE_STYLE
        left, right, top, _ = self._col
        width = right - left
        buttons = []
        for i, label in enumerate(labels):
            y = top - 350 - 70 * i
            box = visual.Rect(self.win, width=width, height=54, pos=(0, y),
                              lineWidth=1.5)
            text = self._text(st["bodyFont"], 20,
                              st["danger"] if i in danger else st["ink"],
                              (left + 24, y), (width - 48, 30), anchor="left",
                              text=label, bold=i not in danger)
            buttons.append((box, text))

        was_visible = self.win.mouseVisible
        mouse = event.Mouse(win=self.win, visible=True)
        self.win.mouseVisible = True
        mouse.setPos((0, top - 350))
        # A button still held from before must not count as a click
        while any(mouse.getPressed()):
            self.flip()
        mouse.clickReset()

        chosen = None
        while chosen is None:
            self.draw_page([page], 0, nav=False)
            for i, (box, text) in enumerate(buttons):
                hover = box.contains(mouse)
                box.fillColor = _rgb(st["hover"] if hover else st["paper"])
                box.lineColor = _rgb(st["accent"] if hover else st["hairline"])
                box.draw()
                text.draw()
                if hover and mouse.getPressed()[0]:
                    chosen = i
            self.flip()
        while any(mouse.getPressed()):  # wait for release
            self.flip()

        self.win.mouseVisible = was_visible
        if self._mouse_parked:
            self.park_mouse()
        return chosen

    def _label(self, text, y, height, color=INK, bold=False, x=0,
               align="center"):
        """A text line for the question screens."""
        return visual.TextStim(self.win, text=text, pos=(x, y), height=height,
                               color=color, bold=bold, wrapWidth=900,
                               font=PAGE_STYLE["bodyFont"],
                               fontFiles=FONT_BODY_BOLD if bold else FONT_BODY,
                               anchorHoriz=align, alignText=align)

    def _title(self, text, y):
        """The question line of a question screen: the page title font."""
        return visual.TextStim(self.win, text=text, pos=(0, y), height=32,
                               color=INK, wrapWidth=900,
                               font=PAGE_STYLE["titleFont"],
                               fontFiles=FONT_TITLE)

    @_on_paper
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
                    pause_menu()
                    break                    # redraw; typed text is kept
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

        Separate from the key loop, so the screen can be drawn
        without waiting for keys.
        """
        labels = [self._title(question, 124),
                  self._label("Press Enter to continue", -256, 20, DIM_TEXT)]
        if progress:
            labels.append(self._label(progress, 234, 18, DIM_TEXT))
        if hint:
            labels.append(self._label(hint, -86, 18, DIM_TEXT))
        box = visual.Rect(self.win, width=400, height=70, pos=(0, 19),
                          fillColor=BOX_FILL, lineColor=BOX_LINE, lineWidth=1.5)
        typed = self._label("", 19, 30, x=-180, align="left")

        def draw(answer):
            box.draw()
            typed.text = answer + "|"        # "|" marks where typing goes
            typed.draw()
            for label in labels:
                label.draw()
        return draw

    @_on_paper
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
                    pause_menu()
                    break
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
        labels = [self._title(question, 184),
                  self._label("Press a number", -296, 20, DIM_TEXT)]
        if progress:
            labels.append(self._label(progress, 264, 18, DIM_TEXT))
        boxes = []
        for i, option in enumerate(options):
            y = 87 - 70 * i
            boxes.append(visual.Rect(self.win, width=460, height=55, pos=(0, y),
                                     fillColor=OPTION_FILL, lineColor=BOX_LINE,
                                     lineWidth=1))
            labels.append(self._label(str(i + 1), y, 22, DIM_TEXT, bold=True,
                                      x=-205, align="left"))
            labels.append(self._label(option, y, 24, x=-165, align="left"))

        def draw(chosen=None):
            for i, box in enumerate(boxes):
                box.fillColor = CHOSEN_FILL if i == chosen else OPTION_FILL
                box.lineColor = CHOSEN_LINE if i == chosen else BOX_LINE
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
        """Open the pause screen on Esc; otherwise return the keys pressed.

        After Continue, keys pressed before the pause are dropped.
        """
        if any(key == "escape" for key, _ in keys):
            pause_menu()
            return []
        return keys

    @_on_paper
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
        labels = [self._title(question, 220),
                  self._label(self.SKIP_HINT, -290, 18, DIM_TEXT)]
        if progress:
            labels.append(self._label(progress, 300, 18, DIM_TEXT))
        box = visual.Rect(self.win, width=800, height=300, pos=(0, -20),
                          fillColor=BOX_FILL, lineColor=BOX_LINE, lineWidth=1.5)
        # top-left of the box; long answers wrap onto new lines
        typed = visual.TextStim(self.win, text="", pos=(-385, 120), height=24,
                                color=INK, wrapWidth=770,
                                font=PAGE_STYLE["bodyFont"],
                                fontFiles=FONT_BODY,
                                anchorHoriz="left", anchorVert="top",
                                alignText="left")

        def draw(answer):
            box.draw()
            typed.text = answer + "|"
            typed.draw()
            for label in labels:
                label.draw()
        return draw

    @_on_paper
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
        labels = [self._title(question, 220),
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

    @_on_paper
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
        labels = [self._title(question, 220),
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
                box.lineColor = CHOSEN_LINE if on else BOX_LINE
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
        hint = self._label(f"{NAV_TEXT['back']}        {NAV_TEXT['next']}",
                           -372, 16, DIM_TEXT)

        def draw(screen_n):
            if screen_n == 0:
                self.draw_page(SCREEN_TEXT["thankYou"], 0)
                return
            sheet.draw()
            for stim in pages[screen_n - 1]:
                stim.draw()
            page_number.text = f"Page {screen_n} of {len(pages)}"
            page_number.draw()
            hint.draw()
        return draw, len(pages) + 1

    @_on_paper
    def show_debrief(self):
        """Thank-you message, then the letter; arrows move back and forth.

        Right arrow on the last page ends the letter. Esc leaves the letter
        early without opening the pause screen: the session's data are
        already saved, so this is not an abort.
        """
        draw, n_screens = self._debrief_screen()
        screen_n = 0
        event.clearEvents()
        while True:
            draw(screen_n)
            self.flip()
            key = event.waitKeys(keyList=["right", "left", "escape"])[0]
            if key == "escape":
                return
            if key == "left":
                screen_n = max(0, screen_n - 1)
            elif screen_n == n_screens - 1:
                return
            else:
                screen_n += 1

    def park_mouse(self):
        """Hide the cursor and move it to the experimenter's screen.

        Moving it off the stimulus screen keeps it from sitting on the
        stimuli, even if the window shows it again. Screen 0 (the primary
        monitor) starts at (0, 0) in Windows' desktop coordinates, so its
        centre is half its width and half its height.
        """
        self._mouse_parked = True
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
