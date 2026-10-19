"""
All parameters are stored here.
Outline:
     1. SESSION
     2. COUNTERBALANCING    
     3. SESSION STRUCTURE    
     4. TRIAL TIMING         
     5. GAZE                 
     6. SCREEN AND LAYOUT    
     7. FILES               
     8. STIMULI              
     9. TEXT                 
    10. LOOK OF TEXT SCREENS fonts and colours

Names: g0-g7 are objects, m0-m5 attributes
"""

from pathlib import Path

# ==========================================================================
# 1. SESSION
# ==========================================================================

SESSION = {
    "yesDemographics": True,     
    "yesCalibration": True,     
}

# trial numbers for demo
DEMO_TRIALS = {
    "practice": 3,       # e.g. 3
    "learning": 4,       # per learning block, e.g. 4
    "test": 5,           # per test block, e.g. 5
}

# ==========================================================================
# 2. COUNTERBALANCING
# ==========================================================================

COUNTERBALANCE = {
    "groupCell": 1,                 # a row of GROUP_CELLS
}

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
# 3. SESSION STRUCTURE
#    practice -> learning 1 -> test 1 -> learning 2 -> test 2
# ==========================================================================

PHASES = {
    "practiceTrials": 1,           # trials per practice round (a random
                                   # practice shape); after each round the
                                   # participant chooses: again, or move on
    "learnBlockTrials": 32,        # each object equally often, random order;
                                   # must be a multiple of the object count
    "learnCriterion": 0.25,         # proportion correct in one block; a timeout
                                   # counts as not correct. 29/32 passes, 28/32 not
    "learnCriterionBlocks": 1,     # consecutive blocks at or above the criterion
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
#    in seconds (unless the name says different)
# ==========================================================================

TIMING = {
    "previewDurRange": (0.6, 1.0),    
    "feedbackDur": 2.0,
    "iti": 1.0,
    "responseTimeout_s": 5.0,         
}


# ==========================================================================
# 5. GAZE
#    Fixation check, gaze selection, calibration.
# ==========================================================================

# Central fixation before each cue
CENTRAL_FIXATION = {
    "centralHold_ms": 2000,      # how long gaze must stay inside the radius
    "centralRadius_deg": 2,   # distance from screen centre that counts as on the dot
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
    "ringRadius": 310,              
    "objCount": 8,  
    "objSize_px": 120,               # object image, in the centre and in feedback
    "height_name_px": 24,            # letter height of the names on the ring
    "centralDotRadius_px": 5,        # center fixation dot radius
    "nameSelectMargin_deg": 1.0,     # selection circle around each name:
                                     # radius = centre-to-corner distance of the
                                     # widest name + this value.
    "feedbackWrongMark": "x",        # mark on a wrong choice: "x" or "o";
                                     # same size as the green circle
    "feedbackNameOffset_px": 70,     # name centre to object centre in feedback;
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

# SCAFFOLD for the second context (C2 below). Copied from CONTEXT;
# replace with the second context.
CONTEXT_2 = {obj: list(row) for obj, row in CONTEXT.items()}

# By label, as GROUP_CELLS (section 2) names them. The labels follow the
# design table; the contents are placeholders until the final contexts exist.
CONTEXTS = {"C1": CONTEXT, "C2": CONTEXT_2}

# Which visual feature stands for each attribute, and what 0 and 1 mean.
# stimuli.py refers to this.

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

# Practice objects: 2 x 2 x 2 = 8, one per name, drawn as plain shapes.
# PLACEHOLDER pairing of names and objects.
#   (colour: "white"/"black", shape: "square"/"triangle", size: "big"/"small")
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
    "bigWidth_px": 90,      # big square's side = the real objects' square
                            # (75% of GEOMETRY["objSize_px"]); a triangle
                            # fills the same box (base and height)
    "smallScale": 0.6,      # small = 60% of big, in width
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

# Revised after the ethics submission (Oct 2026): check whether the ethics
# documents need the same changes.
# Screens that only show text are lists of pages: (title, body). Text starts
# at the left; a page with no title ("") shows its text in the vertical
# middle of the screen. The participant moves with the arrow keys: right = next,
# left = back; the page footer shows the keys (NAV_TEXT).
SCREEN_TEXT = {
    # Screen 1
    "greeting": [
        ("Welcome",
         "Welcome and thank you for taking part in this study.\n\n"
         "In this experiment, you will learn made-up names for visual "
         "shapes. You will choose names by looking at them, and an eye "
         "tracker will record where you look.",
         # third part as text: a small grey note above the footer line
         "Use the arrow keys to move through the instructions: "
         "\u2192 for next, \u2190 for back."),
        ("Welcome",
         "If you want to stop at any time, press Esc or let the "
         "researcher know.\n\n"
         "We will ask you a few demographic questions first."),
    ],
    # Screen 2: (question, hint under the box)
    "sonaId": ("What is your SONA ID?", "6 digits"),
    "age": ("What is your age?",
            "You may skip this question: press Enter without typing"),
    "gender": "What is your gender?",
    "selfDescribe": "Please describe your gender",
    # Screen 5 (before calibration). A page may have a third part: pictures
    # of the trial screen, drawn small under the text, each as
    # (picture, caption). Pictures: "dot", "names", "cue", "correct",
    # "incorrect" (presentation.TRIAL_PICTURES). They use the practice
    # objects and names, so they show nothing that is learned later.
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
    # Screen 3
    "calibration": [
        ("Calibration",
         "You will go through the calibration process to adjust the "
         "eye tracker to your eyes.\n\n"
         "Small dots will appear on the screen, one at a time. Look "
         "directly at each dot until it disappears.\n\n"
         "Please keep your head still on the chin rest."),
    ],
    # Screen 4: both eyes passed. A page with no title ("") shows its text
    # in the middle of the screen.
    "calibrationDone": [("", "Calibration was successful.")],
    # After an attempt that failed; the calibration then runs again
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
    # After each practice trial. Keys: Space = again, right arrow = move on
    "practiceChoice": [
        ("", "Press Space to practise again.\n\n"
             "Press \u2192 to move on to the task."),
    ],
    # Screens 6-8: before learning 1, after the practice
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
    # After each learning round. {round}, {percent} and {next} are filled
    # in by experiment.run_learning; {next} is one of "roundEndNext".
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
    # Before learning 2
    "learning2": [
        ("Learning",
         "You will now learn another new set of shapes with new names."),
    ],
    # After test 2, before the post-task questions
    "taskEnd": [
        ("", "You have finished the task.\n\n"
             "We will ask a few optional questions about your experience."),
    ],
    # Screen 13 (screens 9-12 are POSTTASK below; screen 14 is the letter,
    # and the session ends when the participant leaves it)
    "thankYou": [
        ("Thank you for your participation!",
         "Please read the debrief form on the next pages.\n\n"
         "When you have finished, please let the researcher know."),
    ],
    # Shown before an abandoned round starts again
    "blockRestart": [
        ("", "The round will start again from the beginning."),
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
    "skip": "Skip to next section",
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
    "q2": "Did you use any particular way of remembering the shape-name pairs?",
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
    "pictureScale": 0.28,           # trial pictures: size of the real screen
                                    # (two side by side shrink to fit)
    "pictureNameHeight": 13,        # names in pictures, px (larger than to
                                    # scale, so they stay readable)
}
