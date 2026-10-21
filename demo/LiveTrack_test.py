"""Manual check that the LiveTrack tracker starts and returns a sample."""

import sys
# LiveTrack bindings are installed here, not in site-packages
sys.path.insert(0, r"C:\Users\Public\Documents\CRS LiveTrack Python Bindings")
import LiveTrack
import time

LiveTrack.Init()
LiveTrack.SetResultsTypeRaw()
LiveTrack.StartTracking()

try:
    # -----insert test here-----
    data = LiveTrack.GetLastResult()
    data
    # ---------end--------------
finally:
    LiveTrack.StopTracking()
    LiveTrack.Close()