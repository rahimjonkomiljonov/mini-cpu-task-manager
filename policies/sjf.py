"""Shortest Job First (SJF), non-preemptive."""

NAME = "SJF"
SHORT = "SJF"
PREEMPTIVE = False
USES_QUANTUM = False
USES_PRIORITY = False
DESCRIPTION = ("Shortest Job First: when the CPU becomes free, the ready process with the shortest next CPU "
               "burst goes next. Gives a low average waiting time, but long jobs may starve.")


def choose_next(ready, running, sim):
    if running is not None:
        return running          # non-preemptive: let the running process finish
    if ready:
        # Shortest next CPU burst first (see PCB.next_burst); a tie goes to the earlier arrival.
        return min(ready, key=lambda p: (p.next_burst, p.arrival))
    return None
