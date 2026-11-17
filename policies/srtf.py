"""Shortest Remaining Time First (SRTF) = preemptive SJF."""

NAME = "SRTF"
SHORT = "SRTF"
PREEMPTIVE = True
USES_QUANTUM = False
USES_PRIORITY = False
DESCRIPTION = ("Shortest Remaining Time First (preemptive SJF): if the next CPU burst of a ready process is "
               "shorter than what the running one has left of its burst, it takes the CPU immediately.")


def choose_next(ready, running, sim):
    if not ready:
        return running          # nobody else: continue (or stay idle if running is None)
    shortest = min(ready, key=lambda p: (p.next_burst, p.arrival))
    if running is not None and running.next_burst <= shortest.next_burst:
        return running          # the running process is still the shortest (a tie does not preempt)
    return shortest             # preempt: a shorter job is waiting
