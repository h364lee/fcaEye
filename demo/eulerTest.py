import sys
from config import PROJECT_DIR

sys.path.insert(0, str(PROJECT_DIR))

from eulerTours import euler

exp = euler.Euler(stimuli=8, 
                  catch_frequency=0, 
                  catch_to_all=False, 
                  stim_repeat=False, 
                  pair_repeats=1, 
                  seq_repeats=1, 
                  triplets=False)

print(exp.get_sequence(0))