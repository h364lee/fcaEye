# AI usage: code co-written with Claude Opus 5.5.
# Research questions, experimental design and program requirements came from Caleb and Britt.

"""
Genereates 
    random participant IDs for a given SONA ID
    a key file that links PID to SONA ID
"""

import csv
import secrets
from datetime import datetime

from config import PATHS

COLUMNS = ["sonaID", "participantID", "session"]

def assign_pid(sona_id):
    pid = "P" + secrets.token_hex(4)

    path = PATHS["keyFile"]
    path.parent.mkdir(parents=True, exist_ok=True)
    is_new = not path.exists()
    with open(path, "a", newline="", encoding="utf-8") as f:
        writier = csv.writer(f)
        if is_new:
            writier.writerow(["sonaID", "participantID", "session"])
        writier.writerow([sona_id, pid, datetime.now().strftime("%Y-%m-%d %H:%M")])

    return pid
