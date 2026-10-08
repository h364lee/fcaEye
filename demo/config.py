"""
Keep all variables here - 2026-09-12
"""
SESSION = {
    "yesDemographics": False,     # False: skip the questions, ID becomes "debug"
    "yesCalibration": False,      # False: use the calibration stored in the tracker
}

GENDER_OPTIONS = [
    "Woman",
    "Man",
    "Non-binary",
    "Prefer to self-describe",
    "Prefer not to answer",
]

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

TIMING = {
    "previewDurRange": (0.6, 1.0),    # random from this range to prevent anticipation
    "feedbackDur": 2.0,
    "iti": 1.0,
    "responseTimeout_s": 5.0,         # no selection by then -> trial ends as a timeout
}

# COUNTERBALANCING

# The context (objects x attributes) is in context.py, not here.

# Which visual feature stands for each attribute, and what 0 and 1 mean.
# Keys must be m0, m1, ... in column order of CONTEXT. Counterbalance by
# changing which feature each attribute gets. 1 always = feature present.
# Features are described in stimuli.py.
ATTRIBUTES = {
    "m0": {"feature": "colour", 1: "orange", 0: "gray"},
    "m1": {"feature": "stripes", 1: "stripes", 0: "none"},
    "m2": {"feature": "outline", 1: "thick", 0: "none"},
    "m3": {"feature": "hole", 1: "hole", 0: "none"},
    "m4": {"feature": "slot", 1: "slot", 0: "none"},
    "m5": {"feature": "circle", 1: "circle", 0: "square"},
}

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

# Where each object sits on the ring. Edit before each session.
ORDER = {
    # Slot 1 is at 3 o'clock (before ringRotation); later slots go
    # counter-clockwise. Each object exactly once.
    "ringOrder": ["g0", "g1", "g2", "g3", "g4", "g5", "g6", "g7"],
}

# Trial order: an Euler tour over the objects (design.trial_sequence), so
# every transition i -> j between consecutive trials appears equally often.
# A new random seed (1-9999) each session; it is saved in the data file.
EULER_TOUR = {
    "stay_trial": False,    # allow i -> i (same object twice in a row)
    "tour_repeats": 1,      # full tours joined end to end; each i -> j
                            # appears this many times. 8 objects, no stay:
                            # 56 transitions per tour, so 56 * repeats + 1 trials
}



from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent

PATHS = {
    "stimDir": PROJECT_DIR / "stimObj",
    "dataDir": PROJECT_DIR / "data",
    "debriefLetter": PROJECT_DIR / "demo" / "debrief_letter.txt",   # shown at the end
}

# Fixed feature order of the digits in the image file names, as
# stimuli.py writes them. 1 = present. E.g. 100001.png = orange circle.
# Does not change with counterbalancing.
IMAGE_NAME_ORDER = ["colour", "stripes", "outline", "hole", "slot", "circle"]

CALIBRATION = {
# matched CRS LiveTrack calibrate.py 2026-09-14
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

# Gaze dwell selection
DWELL_SELECTION = {
    "dwell_ms": 1000,           # how long gaze must hold to select
    "dwellRadius_deg": 1.5,     # remain within 1.5 deg radius from that fixation
    "blinkTimeout_ms": 300,   # if blinks > 300 ms, then restart.
}

# Central fixation criterion for cue presentation.
CENTRAL_FIXATION = {
    "centralHold_ms": 2000,      # how long gaze must stay inside the radius
    "centralRadius_deg": 1.25,   # distance from screen centre that counts as on the dot
    "centralTimeout_s": 20,      # give up and abort the session
}


# TEXT SHOWN TO PARTICIPANTS
# Kept here, not in experiment.py, so mockups.py can show the same text
# without loading the tracker.

# Same wording as the Instructions document submitted for ethics review
# (ethicsApp/fcaEyeInstructions); change both together.
SCREEN_TEXT = {
    # Screen 1
    "greeting": ("Welcome and thank you for taking part in this study.\n\n"
                 "In this experiment, you will learn made-up names for visual "
                 "objects. You will choose names by looking at them, and an eye "
                 "tracker will record where you look.\n\n"
                 "If you want to stop at any time, press Esc or let the "
                 "researcher know.\n\n"
                 "Press Enter to continue"),
    # Screen 2: (question, hint under the box)
    "sonaId": ("What is your SONA ID?", "6 digits"),
    "age": ("What is your age?",
            "You may skip this question: press Enter without typing"),
    "gender": "What is your gender?",
    "selfDescribe": "Please describe your gender",
    # Screen 3
    "calibration": ("You will go through the calibration process to adjust the "
                    "eye tracker to your eyes.\n\n"
                    "Small dots will appear on the screen, one at a time. Look "
                    "directly at each dot until it disappears.\n\n"
                    "Please keep your head still on the chin rest.\n\n"
                    "Press Enter to continue"),
    # Screen 4: both eyes passed
    "calibrationDone": "Calibration is complete.\n\nPress Enter to continue",
    # Screen 4b: a calibration failed; the researcher recalibrates (R) or ends (Esc)
    "calibrationWait": "Please wait while the researcher adjusts the eye tracker.",
    # Screen 5
    "task": ("Welcome to the task!\n\n"
             "On each trial, a dot appears at the centre of the screen. Look at "
             "the dot and hold.\n"
             "After a moment, several names will appear in a ring around it. "
             "Keep holding your gaze on the central dot until it changes into a "
             "shape.\n\n"
             "Once a shape replaces the dot, look at the name that belongs to "
             "the shape and keep looking at it to make your choice. Once you "
             "hold your gaze at your chosen name long enough, your selection "
             "will be confirmed.\n\n"
             "After each choice, the shape appears next to its CORRECT name, "
             "with a green circle around them. If your choice was INCORRECT, a "
             "red circle marks the name you chose.\n\n"
             "Please choose as quickly and accurately as you can.\n\n"
             "Press Enter to continue"),
    # Screens 6-8: used once the learning and test phases are built
    "learning": ("You will learn the names of a new set of shapes.\n\n"
                 "At first, you will need to guess. After each choice, you will "
                 "see whether you were correct. Use the feedback to learn which "
                 "name belongs to each shape.\n\n"
                 "Training continues in rounds until you choose correctly most "
                 "of the time.\n\n"
                 "Press Enter to continue"),
    "roundEnd": ("End of round {round}. You chose the correct name on "
                 "{percent}% of trials.\n\nPress Enter to continue"),
    "test": ("Now you will be tested on the names you learned.\n\n"
             "The task is the same as before, but you will not be given "
             "feedback whether your choices are correct.\n\n"
             "Press Enter to continue"),
    # Screen 13 (screens 9-12 are POSTTASK below; screen 14 is the letter)
    "thankYou": ("Thank you for your participation!\n\n"
                 "Please press Enter to continue to the debrief form.\n\n"
                 "Press Enter to continue"),
    # Screen 15
    "endOfStudy": ("The study is complete. Thank you again for taking part.\n\n"
                   "Please let the researcher know that you have finished."),
}

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
