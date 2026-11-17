"""First-Come, First-Served (FCFS)."""

NAME = "FCFS"
SHORT = "FCFS"
PREEMPTIVE = False
USES_QUANTUM = False
USES_PRIORITY = False
DESCRIPTION = ("First-Come, First-Served: processes run in the order they entered the ready queue. "
               "Simple and fair in order, but short jobs can get stuck behind a long one (convoy effect).")


def choose_next(ready, running, sim):
    if running is not None:
        return running          # non-preemptive: a running process is never interrupted
    if ready:
        return ready[0]         # the head of the queue has waited the longest
    return None                 # nobody is ready: the CPU stays idle
