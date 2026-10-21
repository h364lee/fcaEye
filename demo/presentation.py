"""The window and everything drawn in it: trial screens, text pages,
question screens, the pause screen and the debrief letter.
"""
import functools
import sys

from psychopy import core, event, visual
from psychopy.visual.textbox2 import textbox2 as _tb2

import design
import eventlog
import geometry
from config import (DISPLAY, GEOMETRY, NAV_TEXT, PAGE_STYLE, PATHS,
                    PAUSE_BUTTONS, PRACTICE_NAMES, PRACTICE_OBJECTS,
                    PRACTICE_SIZES, SCREEN_TEXT)

# Key names that do not equal the character they type.
KEY_CHARS = {"space": " ", "minus": "-", "period": ".", "comma": ",",
             "apostrophe": "'", "slash": "/", "semicolon": ";"}
KEY_CHARS.update({f"num_{d}": str(d) for d in range(10)})

def _rgb(hex_colour):
    """"#RRGGBB" -> PsychoPy rgb, each channel from -1 to 1."""
    h = hex_colour.lstrip("#")
    return [int(h[i:i + 2], 16) / 127.5 - 1 for i in (0, 2, 4)]


# Question screen colours (PsychoPy rgb).
INK = _rgb(PAGE_STYLE["ink"])
DIM_TEXT = _rgb(PAGE_STYLE["muted"])
BOX_FILL = _rgb(PAGE_STYLE["box"])          # typing boxes, options
BOX_LINE = _rgb(PAGE_STYLE["boxLine"])
OPTION_FILL = BOX_FILL
CHOSEN_FILL = _rgb(PAGE_STYLE["chosen"])
CHOSEN_LINE = _rgb(PAGE_STYLE["accent"])

# Pictures a text page can show (third part of a SCREEN_TEXT page).
TRIAL_PICTURES = ("dot", "names", "cue", "correct", "incorrect")

# TextBox2 finds these fonts once they are registered (_build_page).
# TextStim needs them passed as fontFiles every time.
FONT_FILES = [str(f) for f in sorted(PATHS["fontDir"].glob("*.ttf"))]
# TextStim uses the first file of a family it finds, so each weight gets
# only its own file.
FONT_BODY = [str(PATHS["fontDir"] / "SourceSans3-Regular.ttf")]
FONT_BODY_BOLD = [str(PATHS["fontDir"] / "SourceSans3-Semibold.ttf")]


def _on_paper(method):
    """Decorator: show a text screen on white, then restore the old background.

    Nesting is safe: each call restores the colour it found.
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
    """End the session early; saved data are kept and the debrief follows.

    Raised by End on the pause screen, or when the learning criterion is
    not met.
    """


class SkipSection(Exception):
    """"Skip to next section" during trials: end the current phase."""


class RestartBlock(Exception):
    """Continue or Recalibrate during trials: restart the current block.

    recalibrate: True if a calibration should run first.
    """

    def __init__(self, recalibrate):
        super().__init__("block abandoned")
        self.recalibrate = recalibrate


# Draws the pause screen. Module-level because calibrate.py and response.py
# call check_escape() without a Presentation.
_pres = None

# During trials, Continue restarts the block; otherwise it resumes the screen.
_trials_running = False


def set_trials_running(running):
    """Set by experiment.py when trials start and stop."""
    global _trials_running
    _trials_running = running


def check_escape():
    """Open the pause screen if Esc was pressed. Call once per frame.

    May raise the exceptions of pause_menu. core.quit() is not used: pyglet
    swallows its sys.exit(), so the cleanup code would not run.
    """
    if event.getKeys(keyList=['escape']):
        pause_menu()


def pause_menu():
    """Pause screen; the researcher clicks an option.

    Continue: return (outside trials) or raise RestartBlock (in trials).
    Recalibrate (trials only): raise RestartBlock(recalibrate=True).
    Skip to next section (trials only): raise SkipSection.
    End session: confirm, then raise EndSession.
    """
    if _pres is None:                   # no window yet
        raise EndSession("Esc before the window opened")

    # merge.py ends an interrupted trial at pause_on, so pause time is not
    # trial time. No effect before recording starts.
    eventlog.mark("pause_on", duringTrials=_trials_running)
    print("\nPAUSED. Click an option on the stimulus screen.")
    if _trials_running:
        options = ["continue", "recalibrate", "skip", "end"]
    else:
        options = ["continue", "end"]

    while True:
        chosen = options[_pres.choose_button(
            SCREEN_TEXT["pause"][0], [PAUSE_BUTTONS[o] for o in options],
            danger=(options.index("end"),))]
        if chosen != "end":
            break
        # Ending cannot be undone, so ask again.
        confirm = _pres.choose_button(
            SCREEN_TEXT["endConfirm"][0],
            [PAUSE_BUTTONS["back"], PAUSE_BUTTONS["endConfirm"]],
            danger=(1,))
        if confirm == 1:
            eventlog.mark("pause_off", choice="end")
            raise EndSession("researcher chose End on the pause screen")

    print(f"Researcher chose: {chosen}")
    eventlog.mark("pause_off", choice=chosen)
    event.clearEvents()                 # drop keys pressed during the pause
    if not _trials_running:
        return
    if chosen == "skip":
        raise SkipSection("researcher chose Skip to next section")
    raise RestartBlock(recalibrate=(chosen == "recalibrate"))


class Presentation:
    """The window and all stimuli drawn in it."""

    def __init__(self):
        """Open the window and build all stimuli."""
        self.win = visual.Window(
            size=DISPLAY['size'],
            screen=DISPLAY['screen'],
            units=DISPLAY['units'],
            color=DISPLAY['bgColour'],
            fullscr=DISPLAY['fullscreen'],
            allowGUI=True,
        )


        self.fixation = visual.Circle(
            self.win,
            radius=GEOMETRY['centralDotRadius_px'],
            fillColor="white",
            lineColor="white",
        )

        self.message = visual.TextStim(
            self.win, text="", height=24, color="white", wrapWidth=850
        )

        # Feedback: green circle around the correct name and its object.
        self.pair_circle = visual.Circle(
            self.win,
            radius=geometry.pair_circle_radius(),
            fillColor=None,
            lineColor="lime",
            lineWidth=5,
        )

        # Red circle around a wrong name (feedbackWrongMark "o").
        self.wrong_circle = visual.Circle(
            self.win,
            radius=geometry.pair_circle_radius(),
            fillColor=None,
            lineColor="red",
            lineWidth=5,
        )

        # Red X over a wrong name ("x"). Its ends touch a circle the size of
        # the green circle, so the marks match in size.
        arm = geometry.pair_circle_radius() / 2 ** 0.5
        self.wrong_mark = [
            visual.Line(self.win, start=(-arm, -arm), end=(arm, arm),
                        lineColor="red", lineWidth=5),
            visual.Line(self.win, start=(-arm, arm), end=(arm, -arm),
                        lineColor="red", lineWidth=5),
        ]

        if GEOMETRY['feedbackWrongMark'] not in ("x", "o"):
            raise ValueError("GEOMETRY['feedbackWrongMark'] must be \"x\" or "
                             f"\"o\"; it is {GEOMETRY['feedbackWrongMark']!r}")

        # Build every set once so all names can be measured; start on phase1.
        self._built_sets = {}
        sets = design.stimulus_sets()
        for stim_set in sets.values():
            self.use_set(stim_set)
        self.use_set(sets["phase1"])

        # One name selection radius for the whole session, from the largest
        # name of all sets, so the rule is the same in every phase.
        # boundingBox is (width, height) in px, known only once a text exists.
        sizes = [text.boundingBox
                 for _, name_texts in self._built_sets.values()
                 for text in name_texts.values()]
        self.name_radius_px = geometry.name_select_radius_px(sizes)
        print(f"Name selection radius: {self.name_radius_px:.0f} px "
              f"({self.name_radius_px / geometry.px_per_deg():.2f} deg)")
        try:
            geometry.check_tolerance(self.name_radius_px)
        except ValueError:
            self.win.close()
            raise

        self._build_page()
        self._mouse_parked = False      # set by park_mouse

        global _pres
        _pres = self


    def use_set(self, stim_set):
        """Use this design.StimulusSet from now on (each set is built once)."""
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
        """Return {object: drawable}: images, or shapes for the practice set."""
        if stim_set.images is None:
            return {obj: self._practice_shape(PRACTICE_OBJECTS[obj])
                    for obj in stim_set.names}
        return {obj: visual.ImageStim(self.win,
                                      image=str(stim_set.stim_dir / file_name),
                                      size=GEOMETRY['objSize_px'])
                for obj, file_name in stim_set.images.items()}

    def _practice_shape(self, features, scale=1.0):
        """Return one practice object, (colour, shape, size), as a shape.

        A triangle fills the same box as a square of its size, so it fits
        where real objects go. scale: smaller copies for the trial pictures.
        """
        colour, shape, size = features
        width = PRACTICE_SIZES["bigWidth_px"] * scale
        if size == "small":
            width *= PRACTICE_SIZES["smallScale"]
        if shape == "square":
            return visual.Rect(self.win, width=width, height=width,
                               fillColor=colour, lineColor=None)
        half = width / 2
        return visual.ShapeStim(self.win,
                                vertices=[(-half, -half), (half, -half),
                                          (0, half)],
                                fillColor=colour, lineColor=None)

    def draw_fixation(self):
        """Draw the central dot."""
        self.fixation.draw()

    def draw_names(self, positions):
        """Draw each name centred on its ring position."""
        for obj, pos in zip(self.ring_order, positions):
            text = self.name_texts[obj]
            text.pos = pos
            text.draw()

    def draw_object(self, target):
        """Draw the target object in the centre (the go signal)."""
        image = self.obj_images[target]
        image.pos = (0, 0)
        image.draw()

    def draw_feedback(self, target, selection, positions):
        """Draw the correct name and its object; hide the other names.

        Correct: green circle around the pair. Wrong: also the chosen name
        with a red mark. Timeout (selection None): no circle, no mark.
        """
        name_pos = positions[self.ring_order.index(target)]
        obj_pos = geometry.feedback_obj_pos(name_pos)

        self.name_texts[target].pos = name_pos
        self.name_texts[target].draw()
        image = self.obj_images[target]
        image.pos = obj_pos
        image.draw()

        if selection is None:
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
        """Change the window background to a "#RRGGBB" colour."""
        self.win.color = _rgb(hex_colour)
        self.win.clearBuffer()

    def flip(self):
        """Show what was drawn; returns the flip time."""
        return self.win.flip()

    # --- text pages ---

    def _build_page(self):
        """Build the page stimuli once; draw_page only changes their text.

        Layout, top to bottom, left-aligned: title, body, footer (Back, Next).
        """
        st = PAGE_STYLE
        # Register the bundled fonts so TextBox2 finds them by family name.
        _tb2.allFonts.addFontFiles(FONT_FILES)

        w, h = st["sheetSize"]
        top, bottom = h / 2, -h / 2
        left, right = -st["columnWidth"] / 2, st["columnWidth"] / 2
        self._col = (left, right, top, bottom)

        self._page_title = self._text(st["titleFont"], st["titleHeight"],
                                      st["ink"], (left, top - 84),
                                      (right - left, 60), bold=True)
        self._page_body = self._text(st["bodyFont"], st["bodyHeight"],
                                     st["body"], (left, top - 150),
                                     (right - left, 330),
                                     lineSpacing=st["lineSpacing"])
        # Page without a title: body centred between the top and the footer.
        self._page_body_mid = self._text(st["bodyFont"], st["bodyHeight"],
                                         st["body"],
                                         (left, (top + bottom + 74) / 2),
                                         (right - left, 400),
                                         anchor="center-left",
                                         lineSpacing=st["lineSpacing"])
        footer_y = bottom + 44
        self._footer_y = footer_y
        # Top of the footer area (nothing is drawn here). Notes and pictures
        # go above it.
        self._hairline_y = bottom + 74
        self._page_back = self._text(st["bodyFont"], 18, st["muted"],
                                     (left, footer_y), (200, 30),
                                     anchor="left", text=NAV_TEXT["back"])
        self._page_next = self._text(st["bodyFont"], 18, st["ink"],
                                     (right, footer_y), (200, 30),
                                     anchor="right", bold=True)
        # Small grey note just above the footer.
        self._page_note = self._text(st["bodyFont"], 18, st["muted"],
                                     (left, self._hairline_y + 18),
                                     (right - left, 60), anchor="bottom-left",
                                     lineSpacing=st["lineSpacing"])
        self._pictures = {}             # scale -> picture stimuli
        self._pic_caption = visual.TextStim(
            self.win, text="", height=17, color=_rgb(st["muted"]),
            font=st["bodyFont"], fontFiles=FONT_BODY)

    # --- trial pictures on instruction pages ---
    # Small copies of a practice trial: target g2, wrong choice g0, ring not
    # rotated.

    def _build_pictures(self, s):
        """Build the stimuli for pictures at scale s."""
        st = PAGE_STYLE
        w, h = DISPLAY["size"]
        pic = {"size": (w * s, h * s)}
        pic["bg"] = visual.Rect(self.win, width=w * s, height=h * s,
                                fillColor=DISPLAY["bgColour"], lineColor=None)
        pic["dot"] = visual.Circle(
            self.win, radius=max(2.5, GEOMETRY['centralDotRadius_px'] * s),
            fillColor="white", lineColor=None)
        pic["names"] = {
            obj: visual.TextStim(self.win, text=name,
                                 height=st["pictureNameHeight"],
                                 color="white")
            for obj, name in PRACTICE_NAMES.items()}
        pic["objects"] = {obj: self._practice_shape(f, scale=s)
                          for obj, f in PRACTICE_OBJECTS.items()}
        r = geometry.pair_circle_radius() * s
        pic["pair"] = visual.Circle(self.win, radius=r, fillColor=None,
                                    lineColor="lime", lineWidth=2)
        pic["wrong_o"] = [visual.Circle(self.win, radius=r, fillColor=None,
                                        lineColor="red", lineWidth=2)]
        arm = r / 2 ** 0.5
        pic["wrong_x"] = [
            visual.Line(self.win, start=(-arm, -arm), end=(arm, arm),
                        lineColor="red", lineWidth=2),
            visual.Line(self.win, start=(-arm, arm), end=(arm, -arm),
                        lineColor="red", lineWidth=2)]
        return pic

    def _draw_picture(self, kind, centre, s):
        """Draw one picture of kind TRIAL_PICTURES at scale s; no flip."""
        if kind not in TRIAL_PICTURES:
            raise ValueError(f"unknown picture {kind!r}; use one of "
                             f"{TRIAL_PICTURES}")
        if s not in self._pictures:
            self._pictures[s] = self._build_pictures(s)
        pic = self._pictures[s]
        cx, cy = centre

        def at(point):                  # full-screen position -> picture
            return (cx + point[0] * s, cy + point[1] * s)

        order = list(PRACTICE_NAMES)
        full = geometry.ring_positions(0)
        target, wrong = "g2", "g0"

        pic["bg"].pos = centre
        pic["bg"].draw()
        if kind in ("dot", "names"):
            pic["dot"].pos = centre
            pic["dot"].draw()
        if kind in ("names", "cue"):
            for obj, pos in zip(order, full):
                pic["names"][obj].pos = at(pos)
                pic["names"][obj].draw()
        if kind == "cue":
            pic["objects"][target].pos = centre
            pic["objects"][target].draw()
        if kind in ("correct", "incorrect"):
            name_full = full[order.index(target)]
            obj_full = geometry.feedback_obj_pos(name_full)
            pic["names"][target].pos = at(name_full)
            pic["names"][target].draw()
            pic["objects"][target].pos = at(obj_full)
            pic["objects"][target].draw()
            pic["pair"].pos = at(((name_full[0] + obj_full[0]) / 2,
                                     (name_full[1] + obj_full[1]) / 2))
            pic["pair"].draw()
        if kind == "incorrect":
            wrong_pos = at(full[order.index(wrong)])
            pic["names"][wrong].pos = wrong_pos
            pic["names"][wrong].draw()
            marks = (pic["wrong_x"] if GEOMETRY['feedbackWrongMark'] == "x"
                     else pic["wrong_o"])
            for mark in marks:
                mark.pos = wrong_pos
                mark.draw()

    def _draw_pictures(self, pictures):
        """Draw pictures in a row above the footer, captions below them.

        Several pictures shrink if needed to fit the text column.
        """
        left, right, _, _ = self._col
        gap = 24
        n = len(pictures)
        screen_w, screen_h = DISPLAY["size"]
        fit = ((right - left) - gap * (n - 1)) / n / screen_w
        s = min(PAGE_STYLE["pictureScale"], fit)
        w, h = screen_w * s, screen_h * s
        captions = any(caption for _, caption in pictures)
        base = self._hairline_y + 24 + (28 if captions else 0)
        y = base + h / 2
        for i, (kind, caption) in enumerate(pictures):
            x = (i - (n - 1) / 2) * (w + gap)
            self._draw_picture(kind, (x, y), s)
            if caption:
                self._pic_caption.text = caption
                self._pic_caption.pos = (x, base - 14)
                self._pic_caption.draw()

    def _text(self, font, height, colour, pos, size, anchor="top-left",
              text="", **kwargs):
        """A TextBox2 whose text starts exactly at pos (no padding)."""
        return visual.TextBox2(
            self.win, text=text, font=font, letterHeight=height,
            color=_rgb(colour), units="pix", pos=pos, size=size,
            anchor=anchor, alignment=anchor, padding=0, **kwargs)

    def draw_page(self, pages, index, nav=True, fill=None):
        """Draw pages[index], a (title, body[, extra]) tuple; no flip.

        nav=False: no footer. fill: values for {} fields, e.g. {"round": 2}.
        """
        title, body = pages[index][:2]
        # extra: [(picture, caption), ...] or a note text
        extra = pages[index][2] if len(pages[index]) > 2 else None
        pictures = extra if isinstance(extra, list) else []
        note = extra if isinstance(extra, str) else ""
        if fill:
            title, body = title.format(**fill), body.format(**fill)
        if title:
            self._page_title.text = title
            self._page_title.draw()
            self._page_body.text = body
            self._page_body.draw()
        else:
            self._page_body_mid.text = body
            self._page_body_mid.draw()
        if pictures:
            self._draw_pictures(pictures)
        if note:
            self._page_note.text = note
            self._page_note.draw()
        if not nav:
            return

        if index > 0:
            self._page_back.draw()
        last = index == len(pages) - 1
        self._page_next.text = NAV_TEXT["last"] if last else NAV_TEXT["next"]
        self._page_next.draw()

    @_on_paper
    def show_pages(self, pages, fill=None, escape_exits=False):
        """Show text pages; right arrow = next, left arrow = back.

        Returns after the right arrow on the last page. Esc opens the pause
        screen, or returns if escape_exits is True.
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
    def show_choice(self, pages, keys):
        """Show one page without footer until one of keys is pressed; return it."""
        event.clearEvents()
        while True:
            self.draw_page(pages, 0, nav=False)
            self.flip()
            key = event.waitKeys(keyList=list(keys) + ["escape"])[0]
            if key in keys:
                return key
            pause_menu()

    @_on_paper
    def choose_button(self, page, labels, danger=()):
        """Show one page with clickable buttons; return the clicked index.

        danger: indexes of buttons drawn in the warning colour. A parked
        cursor is parked again afterwards.
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
        # A button still held from before must not count as a click.
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
        while any(mouse.getPressed()):
            self.flip()

        self.win.mouseVisible = was_visible
        if self._mouse_parked:
            self.park_mouse()
        return chosen

    def _label(self, text, y, height, color=INK, bold=False, x=0,
               align="center"):
        """Return a text line for the question screens."""
        return visual.TextStim(self.win, text=text, pos=(x, y), height=height,
                               color=color, bold=bold, wrapWidth=900,
                               font=PAGE_STYLE["bodyFont"],
                               fontFiles=FONT_BODY_BOLD if bold else FONT_BODY,
                               anchorHoriz=align, alignText=align)

    def _title(self, text, y):
        """Return the question line, in semibold like page titles."""
        return visual.TextStim(self.win, text=text, pos=(0, y), height=32,
                               color=INK, bold=True, wrapWidth=900,
                               font=PAGE_STYLE["titleFont"],
                               fontFiles=FONT_BODY_BOLD)

    @_on_paper
    def type_answer(self, question, allowed, progress="", hint="", max_len=20,
                    is_valid=None, optional=False):
        """Ask one question with a typing box; return the typed text.

        Only characters in allowed are accepted. Enter is ignored until
        is_valid(answer) is True. optional=True: Enter on an empty box
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
                    break                    # typed text is kept
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
                # Upper case if Shift or Caps Lock is on, but not both.
                if char.isalpha() and mods.get("shift") != mods.get("capslock"):
                    char = char.upper()
                if char in allowed and len(answer) < max_len:
                    answer += char

    def _answer_screen(self, question, progress="", hint=""):
        """Build the type_answer screen; return draw(answer)."""
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
        """Show options in boxes; return the one chosen by number key or click.

        The chosen box stays marked for 0.3 s so the participant sees it.
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
        """Build the choose_option screen; return (draw(chosen=None), boxes)."""
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

    # --- post-task questions ---
    # Keyboard only. Enter confirms; Enter with no answer skips (None).

    SKIP_HINT = ("Press Enter to continue. "
                 "You can press Enter without answering to skip")

    def _posttask_keys(self, keys):
        """Return keys; on Esc, open the pause screen and return []."""
        if any(key == "escape" for key, _ in keys):
            pause_menu()
            return []
        return keys

    @_on_paper
    def type_long_answer(self, question, progress="", max_len=300):
        """Ask an open question in a large box; return the text, or None."""
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
                    continue
                if char.isalpha() and shift != mods.get("capslock"):
                    char = char.upper()
                if len(answer) < max_len:
                    answer += char

    def _long_answer_screen(self, question, progress=""):
        """Build the type_long_answer screen; return draw(answer)."""
        labels = [self._title(question, 220),
                  self._label(self.SKIP_HINT, -290, 18, DIM_TEXT)]
        if progress:
            labels.append(self._label(progress, 300, 18, DIM_TEXT))
        box = visual.Rect(self.win, width=800, height=300, pos=(0, -20),
                          fillColor=BOX_FILL, lineColor=BOX_LINE, lineWidth=1.5)
        # Anchored at the box's top-left, so long answers wrap downward.
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
        """Show images in a row; return the chosen labels, or None if skipped.

        images: list of (image_path, label). Number keys toggle choices.
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
                    chosen ^= {int(digit) - 1}   # toggle

    def _images_screen(self, question, images, progress=""):
        """Build the choose_images screen; return draw(chosen)."""
        n = len(images)
        labels = [self._title(question, 220),
                  self._label(f"Press 1-{n} to choose or unchoose. "
                              "You can choose more than one.", 170, 20, DIM_TEXT),
                  self._label(self.SKIP_HINT, -290, 18, DIM_TEXT)]
        if progress:
            labels.append(self._label(progress, 300, 18, DIM_TEXT))
        stims, frames = [], []
        for i, (path, label) in enumerate(images):
            x = (i - (n - 1) / 2) * 150      # px
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
        """Ask for a 1..n_points rating; return it, or None if skipped."""
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
        """Build the rate_scale screen; return draw(rating)."""
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

    # --- end of session ---
    # The debrief letter is drawn as a light grey sheet on the white screen.

    LETTER_FONT = "Times New Roman"  # installed on macOS and Windows
    SHEET_SIZE = (800, 720)         # width, height, px
    SHEET_MARGIN = 50               # sheet edge to text, px
    LETTER_STYLES = {               # kind: (letter height px, bold, alignment)
        "title": (24, True, "center"),
        "heading": (20, True, "left"),
        "body": (16, False, "left"),
    }

    def _letter_paragraphs(self):
        """Read the letter file; return [(kind, text), ...].

        Paragraphs are split by empty lines. "# " marks the title, "## " a
        heading. A block of "#" note lines before the title is skipped.
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
                    continue
                paragraphs.append(("title", block[2:]))
            elif block:
                paragraphs.append(("body", block))
        return paragraphs

    def _text_height(self, stim, height):
        """Return a wrapped TextStim's height in px.

        Estimated from the character count if this PsychoPy version has no
        boundingBox.
        """
        try:
            return stim.boundingBox[1]
        except (AttributeError, TypeError):
            chars_per_line = stim.wrapWidth / (0.5 * height)
            lines = sum(max(1, -(-len(line) // int(chars_per_line)))
                        for line in stim.text.split("\n"))
            return lines * height * 1.25

    def _debrief_pages(self):
        """Lay the letter out on sheets; return a list of TextStim lists.

        A paragraph that does not fit starts a new sheet.
        """
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
            y -= needed + 0.9 * size                  # gap after a paragraph
        return pages

    def _debrief_screen(self):
        """Build the end screens; return (draw(screen_n), n_screens).

        Screen 0 is the thank-you page; screens 1.. are letter sheets.
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
        """Show the thank-you page, then the letter; arrows move between them.

        Esc leaves at once, without the pause screen: the data are already
        saved.
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
        """Hide the cursor and move it to the centre of screen 0 (Windows only).

        Off the stimulus screen, it cannot cover stimuli even if shown again.
        Screen 0 starts at (0, 0) in Windows desktop coordinates.
        """
        self._mouse_parked = True
        self.win.mouseVisible = False
        if sys.platform == "win32":
            import ctypes
            user32 = ctypes.windll.user32
            user32.SetCursorPos(user32.GetSystemMetrics(0) // 2,
                                user32.GetSystemMetrics(1) // 2)

    def close(self):
        """Close the window."""
        self.win.close()
