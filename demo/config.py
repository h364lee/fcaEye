"""Experiment settings.

Sections: 1 session, 2 counterbalancing, 3 session structure, 4 timing,
5 gaze, 6 screen, 7 files, 8 stimuli, 9 text, 10 text screen style.
Objects are g0-g7; attributes are m0-m5.
"""

from pathlib import Path

# ==========================================================================
# 1. SESSION
# ==========================================================================

SESSION = {
    "yesDemographics": True,     # False: skip the demographic questions
    "yesCalibration": True,      # False: skip calibration
}

# TEST: cuts each block to this many trials (None = full block).
# Set all to None before real data.
DEMO_TRIALS = {
    "practice": 2,       # per practice round
    "learning": 4,       # per learning block
    "test": 5,           # per test block
}

# ==========================================================================
# 2. COUNTERBALANCING
# ==========================================================================

COUNTERBALANCE = {
    "groupCell": 1,                 # row of GROUP_CELLS (1-8)
}

# Each row: (context label, object set) for phase 1 and phase 2.
# isom = same context in both phases; shift = different context.
# Phase 2 is not run for now; its settings are kept for later.
GROUP_CELLS = {
    #    phase 1     phase 2
    1: [("C1", 1), ("C1", 2)],     # isom
    2: [("C1", 1), ("C2", 2)],     # shift
    3: [("C2", 1), ("C2", 2)],     # isom
    4: [("C2", 1), ("C1", 2)],     # shift
    5: [("C1", 2), ("C1", 1)],     # isom
    6: [("C1", 2), ("C2", 1)],     # shift
    7: [("C2", 2), ("C2", 1)],     # isom
    8: [("C2", 2), ("C1", 1)],     # shift
}


# ==========================================================================
# 3. SESSION STRUCTURE: practice -> learning 1 -> test 1
#    (learning 2 and test 2 are off for now; see experiment.main)
# ==========================================================================

PHASES = {
    "practiceTrials": 1,           # trials per practice round
    "learnBlockTrials": 32,        # trials per learning block; must be a
                                   # multiple of the object count
    "learnCriterion": 0.25,        # TEST value. Proportion correct needed in
                                   # a block; a timeout counts as wrong
    "learnCriterionBlocks": 1,     # TEST value. Consecutive blocks needed at
                                   # or above learnCriterion
    "learnMaxBlocks": 10,          # if criterion not met by then, the session
                                   # ends (abandoned blocks do not count)
}

# A test block is one Euler tour (design.trial_sequence): each transition
# i -> j between consecutive trials appears equally often.
EULER_TOUR = {
    "stay_trial": True,     # allow i -> i (same object twice in a row)
    "tour_repeats": 1,      # times each i -> j appears. 8 objects with stay:
                            # 64 * repeats + 1 trials; without stay: 56.
}


# ==========================================================================
# 4. TRIAL TIMING (seconds)
# ==========================================================================

TIMING = {
    "previewDurRange": (0.6, 1.0),    # names shown before the object; random
                                      # in this range
    "feedbackDur": 2.0,               # feedback screen
    "iti": 1.0,                       # blank screen between trials
    "responseTimeout_s": 5.0,         # time allowed to select a name
}


# ==========================================================================
# 5. GAZE
# ==========================================================================

# Central fixation before each cue
CENTRAL_FIXATION = {
    "centralHold_ms": 2000,      # gaze must stay on the dot this long
    "centralRadius_deg": 2,      # distance from centre that counts as on the dot
    "centralTimeout_s": 20,      # not held by then: the session is aborted
}

# Selecting a name by looking at it
DWELL_SELECTION = {
    "dwell_ms": 1000,           # gaze hold needed to select
    "dwellRadius_deg": 1.5,     # gaze must stay within this distance of where
                                # the hold began
    "blinkTimeout_ms": 300,     # gaze loss up to this long pauses the count;
                                # longer resets it
}

# Live gaze state (whereGaze column of <stem>_gaze.csv): g0-g7, centre, other
# or lost, recorded during trials from dot_on to feedback (or blank).
GAZE_STATE = {
    "interval_ms": 10,          # one state per interval of tracker time
}

# Calibration (values match CRS LiveTrack calibrate.py)
CALIBRATION = {
    "viewDist_mm": 850,             # eye to screen
    "screenSize_mm": [400, 300],    # width, height of the visible screen
    "targets_deg": [                # target positions (x, y) from centre
        [-9.5,-9.5],[0,-9.5],[9.5,-9.5],
        [-9.5,0],[0,0],[9.5,0],
        [-9.5,9.5],[0,9.5],[9.5,9.5]
        ],
    "setupDelay_ms": 1200.0,        # wait after a target appears before
                                    # accepting a fixation
    "minFixDur_ms": 1200,           # length of a stable fixation
    "fixTimeout_s": 5,              # give up on a target after this
    "fixThreshold_px": 3.1,         # max spread of the pupil-glint vector
                                    # (camera px) for a stable fixation
    "fixInDot_deg": 0.3,            # target inner dot diameter
    "fixOutDot_deg": 0.6,           # target outer dot diameter
    "calibrationCriterion_deg": 0.5,  # pass: error below this for both eyes
}


# ==========================================================================
# 6. SCREEN AND LAYOUT (pixels unless the name says otherwise)
# ==========================================================================

DISPLAY = {
    "size": [1024, 768],
    "fullscreen": True,
    "bgColour": [0, 0, 0],     # PsychoPy rgb (-1 to 1); 0,0,0 = grey
    "units": "pix",
    "screen" : 1,   # monitor index (0 = first)
}

GEOMETRY = {
    "ringRadius": 310,               # screen centre to each name
    "objCount": 8,                   # objects (and names) on the ring
    "objSize_px": 120,               # object image size
    "height_name_px": 24,            # letter height of the names
    "centralDotRadius_px": 5,        # fixation dot radius
    "nameSelectMargin_deg": 1.0,     # selection circle radius = widest name's
                                     # centre-to-corner distance + this
    "feedbackNameOffset_px": 70,     # name centre to object centre in feedback
                                     # (object below the name, or above where
                                     # it would not fit)
    "ringRotation": 0,               # degrees, or "random" (new each trial)
}


# ==========================================================================
# 7. FILES
# ==========================================================================

PROJECT_DIR = Path(__file__).resolve().parent.parent

PATHS = {
    "stimDir": PROJECT_DIR / "stimObj",                 # object images
    "dataDir": PROJECT_DIR / "data",                    # output files
    "debriefLetter": PROJECT_DIR / "demo" / "debrief_letter.txt",   # shown at the end
    "fontDir": PROJECT_DIR / "demo" / "fonts",          # page fonts (PAGE_STYLE)
}


# ==========================================================================
# 8. STIMULI
# ==========================================================================

# Formal contexts: rows are objects, columns attributes; 1 = the object
# has the attribute. All contexts use the same object labels.
CONTEXT = {
    #     m0 m1 m2 m3 m4 m5
    "g0": [1, 1, 1, 0, 0, 0],
    "g1": [1, 0, 1, 0, 1, 0],
    "g2": [1, 1, 0, 1, 0, 0],
    "g3": [1, 0, 0, 1, 0, 1],
    "g4": [0, 0, 0, 1, 1, 1],
    "g5": [0, 1, 0, 1, 0, 1],
    "g6": [0, 0, 1, 0, 1, 1],
    "g7": [0, 1, 1, 0, 1, 0],
}

# SCAFFOLD: copy of CONTEXT; replace with the second context.
CONTEXT_2 = {obj: list(row) for obj, row in CONTEXT.items()}

# Labels used in GROUP_CELLS. PLACEHOLDER contents until the final
# contexts exist.
CONTEXTS = {"C1": CONTEXT, "C2": CONTEXT_2}

# Visual feature for each attribute, and what 1 and 0 mean (stimuli.py).
ATTRIBUTES = {
    "m0": {"feature": "colour", 1: "orange", 0: "gray"},
    "m1": {"feature": "stripes", 1: "stripes", 0: "none"},
    "m2": {"feature": "outline", 1: "thick", 0: "none"},
    "m3": {"feature": "hole", 1: "hole", 0: "none"},
    "m4": {"feature": "slot", 1: "slot", 0: "none"},
    "m5": {"feature": "circle", 1: "circle", 0: "square"},
}

# Feature order of the digits in image file names; 1 = present.
# E.g. 100001.png = orange circle.
IMAGE_NAME_ORDER = ["colour", "stripes", "outline", "hole", "slot", "circle"]

# Name set A, used with object set 1.
NAMES = {
    "g0": "Guli",
    "g1": "Domu",
    "g2": "Vemi",
    "g3": "Zudo",
    "g4": "Tora",
    "g5": "Kesa",
    "g6": "Pino",
    "g7": "Ruba",
}

# Name set B, used with object set 2. PLACEHOLDER: not yet matched to set A.
NAMES_B = {
    "g0": "Lobe",
    "g1": "Mafu",
    "g2": "Nesi",
    "g3": "Ropa",
    "g4": "Sife",
    "g5": "Tuni",
    "g6": "Wako",
    "g7": "Zeli",
}

# PLACEHOLDER practice names, one per practice object below.
PRACTICE_NAMES = {
    "g0": "Dada",
    "g1": "Fifi",
    "g2": "Lolo",
    "g3": "Mimi",
    "g4": "Nunu",
    "g5": "Sasa",
    "g6": "Tete",
    "g7": "Vava",
}

# Practice objects, drawn as plain shapes. PLACEHOLDER pairing with names.
# (colour: "white"/"black", shape: "square"/"triangle", size: "big"/"small")
PRACTICE_OBJECTS = {
    "g0": ("white", "square", "big"),
    "g1": ("white", "square", "small"),
    "g2": ("white", "triangle", "big"),
    "g3": ("white", "triangle", "small"),
    "g4": ("black", "square", "big"),
    "g5": ("black", "square", "small"),
    "g6": ("black", "triangle", "big"),
    "g7": ("black", "triangle", "small"),
}
PRACTICE_SIZES = {
    "bigWidth_px": 90,      # big shape width and height (= real objects'
                            # square, 75% of objSize_px)
    "smallScale": 0.6,      # small size as a fraction of big
}

# Object sets: images, features and names. Set 1 uses name set A,
# set 2 name set B.
# SCAFFOLD: set 2 uses set 1's features and images until its own exist.
OBJECT_SETS = {
    1: {"names": NAMES, "stimDir": PATHS["stimDir"],
        "attributes": ATTRIBUTES, "imageNameOrder": IMAGE_NAME_ORDER},
    2: {"names": NAMES_B, "stimDir": PATHS["stimDir"],
        "attributes": ATTRIBUTES, "imageNameOrder": IMAGE_NAME_ORDER},
}

# Name positions on the ring, each object once. Slot 1 is at 3 o'clock
# (before ringRotation); later slots go counter-clockwise.
ORDER = {
    "ringOrder": ["g0", "g1", "g2", "g3", "g4", "g5", "g6", "g7"],
}


# ==========================================================================
# 9. TEXT (everything participants read)
# ==========================================================================

SCREEN_TEXT = {
    # Order below follows the session.
    "greeting": [
        ("Welcome",
         "Welcome and thank you for taking part in this study.\n\n"
         "In this experiment, you will learn made-up names for visual "
         "shapes. You will choose names by looking at them, and an eye "
         "tracker will record where you look.",
         # third part: small grey note above the footer
         "Use the arrow keys to move through the instructions: "
         "\u2192 for next, \u2190 for back."),
        ("Welcome",
         "If you want to stop at any time, press Esc or let the "
         "researcher know.\n\n"
         "We will ask you a few demographic questions first."),
    ],
    # Demographic questions: (question, hint under the box)
    "sonaId": ("What is your SONA ID?", "6 digits"),
    "age": ("What is your age?",
            "You may skip this question: press Enter without typing"),
    "gender": "What is your gender?",
    "selfDescribe": "Please describe your gender",
    # Instructions. Optional third part: small trial
    # pictures as (picture, caption). Pictures: "dot", "names", "cue",
    # "correct", "incorrect". They use practice objects and names.
    "task": [
        ("Instruction",
         "On each trial, a dot appears at the centre of the screen. Look at "
         "the dot and hold your gaze on it.",
         [("dot", "")]),
        ("Instruction",
         "After a moment, several names will appear in a ring around the dot. "
         "Keep holding your gaze on the central dot until it changes into "
         "a shape.",
         [("names", "")]),
        ("Instruction",
         "One of the names belongs to the shape. "
         "Once a shape replaces the dot, look at the name that belongs to "
         "the shape and keep looking at it to make your choice. "
         "Once you hold your gaze at your chosen name long enough, your "
         "selection will be confirmed.",
         [("cue", "")]),
        ("Instruction",
         "After each choice, the shape appears next to its CORRECT name, "
         "with a green circle around them. "
         "If your choice was INCORRECT, a red X marks the name you chose.",
         [("correct", "Correct"), ("incorrect", "Incorrect")]),
        ("Instruction",
         "Before the task starts, you will go through calibration of the "
         "eye tracker."),
    ],
    "calibration": [
        ("Calibration",
         "You will go through the calibration process to adjust the "
         "eye tracker to your eyes.\n\n"
         "Small dots will appear on the screen, one at a time. Look "
         "directly at each dot until it disappears.\n\n"
         "Please keep your head still on the chin rest."),
    ],
    # Both eyes passed. A page with title "" shows its text
    # in the middle of the screen.
    "calibrationDone": [("", "Calibration was successful.")],
    # After a failed attempt; calibration then runs again
    "calibrationFailed": [
        ("", "Calibration was not successful. We will do it again."),
    ],
    # PLACEHOLDER: before the practice trials
    "practice": [
        ("Practice",
         "You will first practise choosing names with your eyes, with a "
         "small set of simple shapes.\n\n"
         "After each practice trial, you can choose to practise again or "
         "move on to the task."),
    ],
    # After each practice round
    "practiceChoice": [
        ("", "Press Space to practise again.\n\n"
             "Press \u2192 to move on to the task."),
    ],
    # Before learning 1, after the practice
    "learning": [
        ("Learning",
         "Now you are moving on to the real task.\n\n"
         "You will learn the names of a new set of shapes. At first, you'll "
         "need to guess. After each choice, you will see whether you "
         "were correct. Use the feedback to learn which name belongs to "
         "each shape.\n\n"
         "Learning continues in rounds until you choose correctly most of "
         "the time. Please choose as quickly and accurately as you can."),
    ],
    # After each learning round. Fields are filled in by
    # experiment.run_learning; {next} is one of "roundEndNext".
    "roundEnd": [
        ("", "You chose the correct name on {percent}% of trials in round "
             "{round}.\n\n"
             "Press \u2192 to move on to {next}."),
    ],
    "roundEndNext": {
        "round": "the next round",      # criterion not met yet
        "test": "the test",             # criterion met
        "end": "the end of this part",  # last round, criterion not met
    },
    "test": [
        ("Test",
         "Now you will be tested on the names you learned.\n\n"
         "The task is the same as before, but you will not be given "
         "feedback whether your choices are correct."),
    ],
    # Before learning 2 (not used now; kept for later)
    "learning2": [
        ("Learning",
         "You will now learn another new set of shapes with new names."),
    ],
    # After the last test, before the post-task questions
    "taskEnd": [
        ("", "You have finished the task.\n\n"
             "We will ask a few optional questions about your experience."),
    ],
    # After the post-task questions (POSTTASK); the debrief letter follows.
    "thankYou": [
        ("Thank you for your participation!",
         "Please let the researcher know that you have finished.\n\n"
         "Continue to read the debrief form on the next pages."),
    ],
    # Shown before an abandoned round starts again
    "blockRestart": [
        ("", "The round will start again from the beginning."),
    ],
    # Pause screen (Esc); the researcher clicks one of PAUSE_BUTTONS
    "pause": [("Paused", "Please call the researcher.")],
    # After "End session", to confirm
    "endConfirm": [
        ("End the session?",
         "The data recorded so far stay saved, and the participant goes "
         "to the debrief letter."),
    ],
}

# Page footer. "last" replaces "next" on a screen's last page.
NAV_TEXT = {"back": "\u2190  Back", "next": "Next  \u2192",
            "last": "Continue  \u2192"}

# Pause screen buttons (for the researcher)
PAUSE_BUTTONS = {
    "continue": "Continue",
    "recalibrate": "Recalibrate",
    "skip": "Skip to next section",
    "end": "End session",
    "back": "Go back",
    "endConfirm": "Yes, end the session",
}

# Gender options, in display order
GENDER_OPTIONS = [
    "Woman",
    "Man",
    "Non-binary",
    "Prefer to self-describe",
    "Prefer not to answer",
]

# Post-task questions, all optional. Asked from most open to most
# specific, so earlier questions do not cue later ones.
POSTTASK = {
    "q1": "Did you notice any pattern? If yes, please describe it.",
    "q2": "Did you use any particular way of remembering the shape-name pairs?",
    "q3": "Which visual feature(s) stood out the most?",
    # label under each feature image
    "q3Labels": {"colour": "Colour", "stripes": "Stripes", "outline": "Outline",
                 "hole": "Hole", "slot": "Notch", "circle": "Round shape"},
    "q4": "How easy or difficult was the task?",
    "q4Ends": ("Very easy", "Very difficult"),     # labels under 1 and 7
}


# ==========================================================================
# 10. LOOK OF TEXT SCREENS (instructions, questions, pause, debrief)
# ==========================================================================

# Text screens are white with black text; calibration and trials use
# DISPLAY["bgColour"]. Colours are hex codes. Sizes in px.
# Font bundled in demo/fonts (Source Sans 3, SIL Open Font Licence).
PAGE_STYLE = {
    "titleFont": "Source Sans 3",   # titles in semibold
    "bodyFont": "Source Sans 3",
    "sheetHeight": 660,             # text area height
    "columnWidth": 640,             # text width; about 60 characters a line
    "titleHeight": 34,              # title letter height
    "bodyHeight": 23,               # body letter height
    "letterHeadingHeight": 23,      # debrief letter: heading letter height
    "letterBodyHeight": 19,         # debrief letter: body letter height
                                    # (smaller, so the long letter needs
                                    # fewer pages)
    "lineSpacing": 1.12,            # TextBox2 units: 1 = the font's own spacing
    "paper": "#FFFFFF",             # background of text screens
    "ink": "#000000",               # titles, "Next"
    "body": "#000000",              # body text
    "muted": "#6E6E6E",             # "Back", notes, picture captions
    "hairline": "#BDBDBD",          # button edges (pause screen)
    "accent": "#000000",            # button edge under the mouse, chosen option
    "hover": "#EEEEEE",             # button under the mouse
    "danger": "#9E3B33",            # "End session"
    "box": "#FFFFFF",               # typing boxes and answer options
    "boxLine": "#BDBDBD",           # their edges
    "chosen": "#E6E6E6",            # a chosen option
    "pictureScale": 0.28,           # trial picture size / real screen size
    "pictureNameHeight": 13,        # name height in pictures (above scale,
                                    # so it stays readable)
}
