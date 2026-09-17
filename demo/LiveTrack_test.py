import sys
sys.path.insert(0, r"C:\Users\Public\Documents\CRS LiveTrack Python Bindings")
import LiveTrack
import time

LiveTrack.Init()
LiveTrack.SetResultsTypeRaw()
LiveTrack.StartTracking()

try:
    # -----insert test here-----
    for i in range(10):
        d = LiveTrack.GetLastResult()
        print(d.Tracked, d.GazeX, d.GazeY)
        time.sleep(0.5)
    # ---------end--------------
finally:
    LiveTrack.StopTracking()
    LiveTrack.Close()