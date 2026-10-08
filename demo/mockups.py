"""Save an image of every screen participants see, for the ethics application.

Uses the real drawing code in presentation.py, so the images match the
experiment. Does not load the tracker, so it runs on any computer with
PsychoPy:
    python mockups.py
Images are saved to out/mockups/, numbered in the order participants see
them. The feedback letter screens are saved like every other screen,
to show how the letter appears to participants (the letter itself is
submitted separately).
"""

import config

# A normal window on the main screen, whatever the session settings say.
# Changed before Presentation reads config.DISPLAY.
config.DISPLAY["fullscreen"] = False
config.DISPLAY["screen"] = 0

from config import (GENDER_OPTIONS, IMAGE_NAME_ORDER, PATHS, POSTTASK,
                    PROJECT_DIR, SCREEN_TEXT)
import geometry
from presentation import Presentation

OUT_DIR = PROJECT_DIR / "out" / "mockups"

# Example trial: ring not rotated, target g2; the wrong choice is g0.
TARGET, WRONG = "g2", "g0"


def save(pres, name):
    """Save what has been drawn (the back buffer) as out/mockups/<name>.png,
    then flip to clear it for the next screen."""
    pres.win.getMovieFrame(buffer="back")
    pres.win.saveMovieFrames(str(OUT_DIR / f"{name}.png"))
    pres.flip()


def message(pres, text, name):
    """A plain text screen (pres.show_message without waiting for a key)."""
    pres.message.text = text
    pres.message.draw()
    save(pres, name)


def main():
    """One image per screen in the Instructions document.

    File names start with the screen number used there (s01 ... s15);
    "trial_" images show the screens of every trial (between screen 5 and
    the questions).
    """
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    pres = Presentation()
    positions = geometry.ring_positions(0)

    message(pres, SCREEN_TEXT["greeting"], "s01_greeting")

    # --- Screen 2: demographics, as in experiment.ask_demographics ---
    question, hint = SCREEN_TEXT["sonaId"]
    pres._answer_screen(question, hint=hint)("")
    save(pres, "s02a_sona_id")
    question, hint = SCREEN_TEXT["age"]
    pres._answer_screen(question, hint=hint)("")
    save(pres, "s02b_age")
    draw, _ = pres._option_screen(SCREEN_TEXT["gender"], GENDER_OPTIONS)
    draw()
    save(pres, "s02c_gender")
    pres._answer_screen(SCREEN_TEXT["selfDescribe"])("")
    save(pres, "s02d_gender_self_describe")

    message(pres, SCREEN_TEXT["calibration"], "s03_calibration")
    message(pres, SCREEN_TEXT["calibrationDone"], "s04_calibration_complete")
    message(pres, SCREEN_TEXT["calibrationWait"], "s04b_calibration_wait")
    message(pres, SCREEN_TEXT["task"], "s05_task_instruction")

    # --- every trial ---
    pres.draw_fixation()
    save(pres, "trial_1_fixation_dot")
    pres.draw_names(positions)
    pres.draw_fixation()
    save(pres, "trial_2_names_appear")
    pres.draw_names(positions)
    pres.draw_object(TARGET)
    save(pres, "trial_3_object_cue")
    pres.draw_feedback(TARGET, TARGET, positions)
    save(pres, "trial_4_feedback_correct")
    pres.draw_feedback(TARGET, WRONG, positions)
    save(pres, "trial_5_feedback_incorrect")
    pres.draw_feedback(TARGET, None, positions)
    save(pres, "trial_6_feedback_timeout")

    # --- Screens 6-8: phase screens (in the experiment once phases exist) ---
    message(pres, SCREEN_TEXT["learning"], "s06_learning_phase")
    message(pres, SCREEN_TEXT["roundEnd"].format(round=1, percent=75),
            "s07_end_of_round")
    message(pres, SCREEN_TEXT["test"], "s08_test_phase")

    # --- Screens 9-12: post-task questions, as in experiment.posttask_q ---
    pres._long_answer_screen(POSTTASK["q1"], "Question 1 of 4")("")
    save(pres, "s09_question1")
    pres._long_answer_screen(POSTTASK["q2"], "Question 2 of 4")("")
    save(pres, "s10_question2")
    images = []
    for feature in IMAGE_NAME_ORDER:             # each feature alone
        row = "".join("1" if f == feature else "0" for f in IMAGE_NAME_ORDER)
        images.append((PATHS["stimDir"] / f"{row}.png",
                       POSTTASK["q3Labels"][feature]))
    draw = pres._images_screen(POSTTASK["q3"], images, "Question 3 of 4")
    draw(set())
    save(pres, "s11_question3")
    draw({0, 3})                                 # example: two features chosen
    save(pres, "s11_question3_example_answer")
    draw = pres._scale_screen(POSTTASK["q4"], *POSTTASK["q4Ends"], 7,
                              "Question 4 of 4")
    draw(None)
    save(pres, "s12_question4")
    draw(4)                                      # example: 4 chosen
    save(pres, "s12_question4_example_answer")

    # --- Screens 13-14: thank-you and letter, as in show_debrief ---
    draw, n_screens = pres._debrief_screen()
    draw(0)
    save(pres, "s13_thank_you")
    for screen_n in range(1, n_screens):
        draw(screen_n)
        save(pres, f"s14_feedback_letter_page{screen_n}")

    message(pres, SCREEN_TEXT["endOfStudy"], "s15_end_of_study")

    pres.close()
    print(f"Saved screens to {OUT_DIR}")


if __name__ == "__main__":
    main()
