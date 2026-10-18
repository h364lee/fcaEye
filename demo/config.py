"""config.py: every setting of the experiment, in one place.

No other file holds a number or a text that you may want to change.
Sections, from the most often changed to the least (search "# 3." etc.):

     1. SESSION SWITCHES     parts on or off for testing; demo trial counts
     2. COUNTERBALANCING     group cell for this session; the design table
     3. SESSION STRUCTURE    practice length, learning criterion, test length
     4. TRIAL TIMING         preview, feedback, blank interval, timeout
     5. GAZE                 central fixation, dwell selection, calibration
     6. SCREEN AND LAYOUT    display, ring and feedback geometry
     7. FILES                folders and files the experiment reads
     8. STIMULI              formal contexts, names, visual features, ring order
     9. TEXT                 everything participants read
    10. LOOK OF TEXT SCREENS fonts and colours

Names: g0-g7 are objects, m0-m5 attributes (0-based, as in FCA).
"""

from pathlib import Path



# ==========================================================================
# 1. SESSION SWITCHES
#    Turn parts of the session on or off while testing.
# ==========================================================================

SESSION = {
    "yesDemographics": True,     # False: skip the questions, ID becomes "debug"
    "yesCalibration": False,      # False: use the calibration stored in the tracker
}

# TEMPORARY, for demos: cut every block of a stage to this many trials.
# None = full length. The criterion still needs learnCriterionBlocks
# blocks (section 3), so lower that too for a short demo. Saved in the
# trial file.
DEMO_TRIALS = {
    "practice": 3,       # e.g. 3
    "learning": 3,       # per learning block, e.g. 4
    "test": 3,           # per test block, e.g. 5
}


# ==========================================================================
# 2. COUNTERBALANCING
#    Which group cell this session runs.
# ==========================================================================

# Set by hand for now; later from the participant number.
COUNTERBALANCE = {
    "groupCell": 1,                 # a row of GROUP_CELLS
}

# The design table, one row per group cell.
# Each phase: (context in CONTEXTS, object set in OBJECT_SETS; section 8).
# Same context in both phases = "isom"; different = "shift".
# 2 x 2 x 2: phase-1 context x isom/shift x which set comes first.
GROUP_CELLS = {
    #    phase 1      phase 2
    1: [("M3", 1), ("M3", 2)],     # isom
    2: [("M3", 1), ("N5", 2)],     # shift
    3: [("N5", 1), ("N5", 2)],     # isom
    4: [("N5", 1), ("M3", 2)],     # shift
    5: [("M3", 2), ("M3", 1)],     # isom
    6: [("M3", 2), ("N5", 1)],     # shift
    7: [("N5", 2), ("N5", 1)],     # isom
    8: [("N5", 2), ("M3", 1)],     # shift
}


# ==========================================================================
# 3. SESSION STRUCTURE
#    practice -> learning 1 -> test 1 -> learning 2 -> test 2
# ==========================================================================

PHASES = {
    "practiceTrials": 8,           # placeholder objects, with feedback
    "learnBlockTrials": 32,        # each object equally often, random order;
                                   # must be a multiple of the object count
    "learnCriterion": 0.9,         # proportion correct in one block; a timeout
                                   # counts as not correct. 29/32 passes, 28/32 not
    "learnCriterionBlocks": 3,     # consecutive blocks at or above the criterion
    "learnMaxBlocks": 10,          # criterion not met by then -> session ends
                                   # (abandoned blocks do not count)
}

# A test block is one Euler tour over the objects (design.trial_sequence),
# so every transition i -> j between consecutive trials appears equally
# often. Each block gets a new random seed, saved in the trial file.
EULER_TOUR = {
    "stay_trial": True,     # allow i -> i (same object twice in a row)
    "tour_repeats": 1,      # full tours joined end to end; each i -> j
                            # appears this many times. 8 objects with stay:
                            # 64 transitions per tour, so 64 * repeats + 1 trials
                            # (the first trial has no prime). Without stay: 56.
}


# ==========================================================================
# 4. TRIAL TIMING
#    Seconds, unless the name says otherwise.
# ==========================================================================

TIMING = {
    "previewDurRange": (0.6, 1.0),    # random from this range to prevent anticipation
    "feedbackDur": 2.0,
    "iti": 1.0,
    "responseTimeout_s": 5.0,         # no selection by then -> trial ends as a timeout
}


# ==========================================================================
# 5. GAZE
#    Fixation check, gaze selection, calibration.
# ==========================================================================

# Central fixation before each cue
CENTRAL_FIXATION = {
    "centralHold_ms": 2000,      # how long gaze must stay inside the radius
    "centralRadius_deg": 1.25,   # distance from screen centre that counts as on the dot
    "centralTimeout_s": 20,      # give up and abort the session
}

# Gaze dwell selection of a name
DWELL_SELECTION = {
    "dwell_ms": 1000,           # how long gaze must hold to select
    "dwellRadius_deg": 1.5,     # remain within 1.5 deg radius from that fixation
    "blinkTimeout_ms": 300,   # if blinks > 300 ms, then restart.
}

# Calibration (matched CRS LiveTrack calibrate.py, 2026-09-14)
CALIBRATION = {
    "viewDist_mm": 850, 
    "screenSize_mm": [400, 300],
    "targets_deg": [
        [-9.5,-9.5],[0,-9.5],[9.5,-9.5],
        [-9.5,0],[0,0],[9.5,0],
        [-9.5,9.5],[0,9.5],[9.5,9.5]
        ],
    "setupDelay_ms": 1200.0,
    "minFixDur_ms": 1200,
    "fixTimeout_s": 5,
    "fixThreshold_px": 3.1,
    "fixInDot_deg": 0.3,
    "fixOutDot_deg": 0.6,
    "calibrationCriterion_deg": 0.5, # < 0.5 degree error
}


# ==========================================================================
# 6. SCREEN AND LAYOUT
#    Pixels, unless the name says otherwise.
# ==========================================================================

DISPLAY = {
    "size": [1024, 768],
    "fullscreen": True,
    "bgColour": [0, 0, 0],     
    "units": "pix",
    "screen" : 1,   # display monitor
}

GEOMETRY = {
    "ringRadius": 310,               # screen centre to each name centre. As large
                                     # as fits: check_feedback_fit() stops if the
                                     # feedback circle would leave the screen
    "objCount": 8,  
    "objSize_px": 120,               # object image, in the centre and in feedback
    "height_name_px": 36,            # letter height of the names on the ring
    "centralDotRadius_px": 5,        # center fixation dot radius
    "objSelectRadius_px": 100,       # gaze within this of a name centre selects it
    "feedbackCircleRadius_px": 68,   # size of the mark on a wrong name ("x" or "o")
    "feedbackWrongMark": "o",        # mark on a wrong choice: "x" or "o"
    "feedbackNameOffset_px": 80,     # name centre to object centre in feedback;
                                     # the object goes below the name (above it
                                     # where the circle would not fit, e.g. the
                                     # bottom slot).
                                     # The green circle around the pair is computed
                                     # from this and objSize_px
    "ringRotation": 0,               # degrees, or "random" for a new rotation each trial
}


# ==========================================================================
# 7. FILES
#    Folders and files the experiment reads and writes.
# ==========================================================================

PROJECT_DIR = Path(__file__).resolve().parent.parent

PATHS = {
    "stimDir": PROJECT_DIR / "stimObj",
    "dataDir": PROJECT_DIR / "data",
    "debriefLetter": PROJECT_DIR / "demo" / "debrief_letter.txt",   # shown at the end
    "fontDir": PROJECT_DIR / "demo" / "fonts",          # page fonts (PAGE_STYLE)
}


# ==========================================================================
# 8. STIMULI
#    Contexts, names, visual features, ring order.
# ==========================================================================

# Formal contexts: rows are objects g0-g7, columns attributes m0-m5,
# 1 = the object has the attribute. Every context uses the same object
# labels, so the trial file keeps the same columns.
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

# SCAFFOLD for the second context (N5 below). Copied from CONTEXT;
# replace with the second context.
CONTEXT_2 = {obj: list(row) for obj, row in CONTEXT.items()}

# By label, as GROUP_CELLS (section 2) names them. The labels follow the
# design table; the contents are placeholders until the final contexts exist.
CONTEXTS = {"M3": CONTEXT, "N5": CONTEXT_2}

# Which visual feature stands for each attribute, and what 0 and 1 mean.
# Keys must be m0, m1, ... in column order of the contexts. 1 always =
# feature present. Features are described in stimuli.py.
ATTRIBUTES = {
    "m0": {"feature": "colour", 1: "orange", 0: "gray"},
    "m1": {"feature": "stripes", 1: "stripes", 0: "none"},
    "m2": {"feature": "outline", 1: "thick", 0: "none"},
    "m3": {"feature": "hole", 1: "hole", 0: "none"},
    "m4": {"feature": "slot", 1: "slot", 0: "none"},
    "m5": {"feature": "circle", 1: "circle", 0: "square"},
}

# Fixed feature order of the digits in the image file names, as
# stimuli.py writes them. 1 = present. E.g. 100001.png = orange circle.
IMAGE_NAME_ORDER = ["colour", "stripes", "outline", "hole", "slot", "circle"]

# Name set A, used with object set 1.
# PLACEHOLDER: g5-g7 names are temporary, not yet matched to the others.
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

# Name set B, used with object set 2. PLACEHOLDER names, not yet matched
# to set A.
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

# PLACEHOLDER practice names. The practice objects are plain white circles,
# so there is nothing to learn: the practice only teaches gaze selection.
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

# Object sets: how a context's objects look and what they are called.
# An object set and its name set always go together (Set 1 / Name A,
# Set 2 / Name B).
#   names:          {object: name}
#   stimDir:        folder of the images (stimuli.py)
#   attributes:     which feature stands for each attribute (like ATTRIBUTES)
#   imageNameOrder: feature order of the digits in the image file names
# SCAFFOLD: set 2 uses set 1's features and images until its own exist.
OBJECT_SETS = {
    1: {"names": NAMES, "stimDir": PATHS["stimDir"],
        "attributes": ATTRIBUTES, "imageNameOrder": IMAGE_NAME_ORDER},
    2: {"names": NAMES_B, "stimDir": PATHS["stimDir"],
        "attributes": ATTRIBUTES, "imageNameOrder": IMAGE_NAME_ORDER},
}

# Where each object's name sits on the ring. Slot 1 is at 3 o'clock
# (before GEOMETRY["ringRotation"]); later slots go counter-clockwise.
ORDER = {
    # each object exactly once
    "ringOrder": ["g0", "g1", "g2", "g3", "g4", "g5", "g6", "g7"],
}


# ==========================================================================
# 9. TEXT
#    Everything participants read.
# ==========================================================================

# Same wording as the Instructions document submitted for ethics review
# (ethicsApp/fcaEyeInstructions); change both together.
# Screens that only show text are lists of pages: (title, body). The
# participant moves with the arrow keys: right = next, left = back; the
# page footer shows the keys (NAV_TEXT).
SCREEN_TEXT = {
    # Screen 1
    "greeting": [
        ("Welcome",
         "Welcome and thank you for taking part in this study.\n\n"
         "In this experiment, you will learn made-up names for visual "
         "objects. You will choose names by looking at them, and an eye "
         "tracker will record where you look.\n\n"
         "If you want to stop at any time, press Esc or let the "
         "researcher know."),
    ],
    # Screen 2: (question, hint under the box)
    "sonaId": ("What is your SONA ID?", "6 digits"),
    "age": ("What is your age?",
            "You may skip this question: press Enter without typing"),
    "gender": "What is your gender?",
    "selfDescribe": "Please describe your gender",
    # Screen 3
    "calibration": [
        ("Calibration",
         "You will go through the calibration process to adjust the "
         "eye tracker to your eyes.\n\n"
         "Small dots will appear on the screen, one at a time. Look "
         "directly at each dot until it disappears.\n\n"
         "Please keep your head still on the chin rest."),
    ],
    # Screen 4: both eyes passed
    "calibrationDone": [("Calibration complete", "Calibration is complete.")],
    # Screen 4b: a calibration failed; the researcher recalibrates (R) or
    # ends (Esc). Shown without the footer: the participant does nothing.
    "calibrationWait": [
        ("Please wait",
         "Please wait while the researcher adjusts the eye tracker."),
    ],
    # Screen 5
    "task": [
        ("Welcome to the task!",
         "On each trial, a dot appears at the centre of the screen. Look at "
         "the dot and hold.\n\n"
         "After a moment, several names will appear in a ring around it. "
         "Keep holding your gaze on the central dot until it changes into a "
         "shape."),
        ("Choosing a name",
         "Once a shape replaces the dot, look at the name that belongs to "
         "the shape and keep looking at it to make your choice.\n\n"
         "Once you hold your gaze at your chosen name long enough, your "
         "selection will be confirmed."),
        ("Feedback",
         "After each choice, the shape appears next to its CORRECT name, "
         "with a green circle around them.\n\n"
         "If your choice was INCORRECT, a red circle marks the name you "
         "chose."),
        ("Ready?",
         "Please choose as quickly and accurately as you can."),
    ],
    # PLACEHOLDER: before the practice trials
    "practice": [
        ("Practice (placeholder text)",
         "You will first practise choosing names with your eyes. The shapes "
         "in this practice are all the same, so any name can be chosen."),
    ],
    # PLACEHOLDER: before learning 2
    "learning2": [
        ("Second half (placeholder text)",
         "You will now learn names again."),
    ],
    # Screens 6-8
    "learning": [
        ("Learning",
         "You will learn the names of a new set of shapes.\n\n"
         "At first, you will need to guess. After each choice, you will "
         "see whether you were correct. Use the feedback to learn which "
         "name belongs to each shape.\n\n"
         "Training continues in rounds until you choose correctly most "
         "of the time."),
    ],
    # {round} and {percent} are filled in by experiment.run_learning
    "roundEnd": [
        ("End of round {round}",
         "You chose the correct name on {percent}% of trials."),
    ],
    "test": [
        ("Test",
         "Now you will be tested on the names you learned.\n\n"
         "The task is the same as before, but you will not be given "
         "feedback whether your choices are correct."),
    ],
    # Screen 13 (screens 9-12 are POSTTASK below; screen 14 is the letter)
    "thankYou": [
        ("Thank you for your participation!",
         "Please continue to the debrief form."),
    ],
    # Shown before an abandoned block starts again
    "blockRestart": [
        ("Starting again",
         "The block will start again from the beginning."),
    ],
    # Screen 15
    "endOfStudy": [
        ("The study is complete",
         "Thank you again for taking part.\n\n"
         "Please let the researcher know that you have finished."),
    ],
    # Pause screen (Esc). The researcher clicks one of PAUSE_BUTTONS.
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

# Clickable options on the pause screen (for the researcher)
PAUSE_BUTTONS = {
    "continue": "Continue",
    "recalibrate": "Recalibrate",
    "end": "End session",
    "back": "Go back",
    "endConfirm": "Yes, end the session",
}

# Demographics: gender options, in this order
GENDER_OPTIONS = [
    "Woman",
    "Man",
    "Non-binary",
    "Prefer to self-describe",
    "Prefer not to answer",
]

# Questions after the last trial, all optional (Enter with no answer skips).
# Secondary measures: context for the eye-tracking results, not a test of
# the main hypothesis. Asked from most open to most specific, so earlier
# questions do not cue later ones.
POSTTASK = {
    "q1": "Did you notice any pattern? If yes, please describe it.",
    "q2": "Did you use any particular way of remembering the object-name pairs?",
    "q3": "Which visual feature(s) stood out the most?",
    # label under each feature image, in IMAGE_NAME_ORDER's feature names
    "q3Labels": {"colour": "Colour", "stripes": "Stripes", "outline": "Outline",
                 "hole": "Hole", "slot": "Notch", "circle": "Round shape"},
    "q4": "How easy or difficult was the task?",
    "q4Ends": ("Very easy", "Very difficult"),     # labels under 1 and 7
}


# ==========================================================================
# 10. LOOK OF TEXT SCREENS
#    Instructions, questions, pause, debrief.
# ==========================================================================

# Text screens use the off-white "paper" background; calibration and trials
# keep DISPLAY["bgColour"] (grey). Colours are hex codes.
# Fonts are bundled in demo/fonts (Adobe Source Serif and Source Sans, SIL
# Open Font Licence), so the pages look the same on every computer.
PAGE_STYLE = {
    "titleFont": "Source Serif 4 Display",
    "bodyFont": "Source Sans 3",
    "sheetSize": (780, 660),        # text area, px
    "columnWidth": 640,             # text width; about 60 characters a line
    "titleHeight": 40,              # letter height, px
    "bodyHeight": 23,
    "lineSpacing": 1.12,            # TextBox2 units: 1 = the font's own spacing
    "paper": "#F4F2ED",             # background of text screens
    "ink": "#1F2328",               # titles, "Next"
    "body": "#3B3F45",              # body text
    "muted": "#8A867E",             # "Back"
    "hairline": "#D9D5CC",          # footer line, inactive page marks
    "accent": "#2F6B8A",            # line under the title, current page mark
    "hover": "#E8E4DB",             # button under the mouse
    "danger": "#9E3B33",            # "End session"
    "box": "#FFFFFF",               # typing boxes and answer options
    "boxLine": "#BDB8AE",           # their edges
    "chosen": "#DCE7EE",            # a chosen option
}
