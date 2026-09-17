"""Five-trial demo with gaze calibration.

Same trials as demo.py, preceded by a LiveTrack calibration pass. This
script owns LiveTrack's lifecycle -- Init, result type, StartTracking,
StopTracking, Close. calibrate.py only runs the routine in the middle.

    cd demo
    python demo_calibrated.py
"""

import sys
sys.path.insert(0, r"C:\Users\Public\Documents\CRS LiveTrack Python Bindings")
import LiveTrack

import calibrate
import geometry
import response
from config import CALIBRATION, PHASES
from demo import run_trial
from presentation import Presentation, QuitRequested


def report_calibration(pres, result):
    """Show the accuracy on screen and in the terminal.

    Returns:
        True if every calibrated eye met the criterion, else False.
    """
    threshold = CALIBRATION["accuracy_threshold_deg"]

    if not result:
        pres.show_message("No eye was calibrated.\n\nPress space to continue.")
        print("No eye was calibrated.")
        return False

    lines = []
    passed = True
    for eye, entry in result.items():
        ok = entry["accuracy_deg"] < threshold
        passed = passed and ok
        line = (f"{eye}: {entry['accuracy_deg']:.2f} deg "
                f"from {entry['n_points']} targets  "
                f"[{'PASS' if ok else 'FAIL'}]")
        lines.append(line)
        print(line)

    lines.append(f"\nCriterion: under {threshold} deg")
    lines.append("\nPress space to continue.")
    pres.show_message("\n".join(lines))
    return passed


def main():
    geometry.check_tolerance()        # fail before anything opens
    pres = Presentation()

    LiveTrack.Init()
    LiveTrack.SetResultsTypeRaw()     # calibration reads pupil/glint vectors
    LiveTrack.StartTracking()

    results = []
    try:
        pres.show_message("Calibration.\n\nLook at each dot until it "
                          "disappears.\n\nPress space to begin.")

        accuracy = calibrate.gaze_calibration(pres.win)
        if not report_calibration(pres, accuracy):
            # In the real experiment this is where you would recalibrate,
            # and the numbers would go to the experimenter only.
            print("Calibration did not meet criterion -- continuing anyway.")

        # From here gaze comes back as GazeX/GazeY in screen pixels centred
        # at 0,0 -- the same frame the responders use -- because the
        # calibration targets were given in those units.
        #
        # The results type is set while buffering is stopped, the order
        # CRS's own demos use.
        LiveTrack.StopTracking()
        LiveTrack.SetResultsTypeCalibrated()
        LiveTrack.ClearDataBuffer()
        LiveTrack.StartTracking()

        pres.show_message("Look at the central dot until a name appears.\n\n"
                          "Then look at the object that name belongs to, and "
                          "keep looking at it until the screen changes.\n\n"
                          "Press space to start. Escape stops the session.")
        for target in pres.ring_order:
            results.append(run_trial(pres, target, PHASES["demo"]))
    except response.FixationTimeout as e:
        print(f"\nABORTED: {e}")
        print("Check that the eye is in view and that gaze reads near the "
              "dot when the participant looks at it; recalibrate if not.")
    except QuitRequested:
        print("\nStopped by the experimenter.")
    finally:
        LiveTrack.StopTracking()
        LiveTrack.ClearDataBuffer()
        LiveTrack.Close()
        pres.close()

    for r in results:
        print(r)


if __name__ == "__main__":
    main()