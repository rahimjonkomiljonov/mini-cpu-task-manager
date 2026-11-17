"""Priority scheduling, preemptive. A LOWER number means a HIGHER priority."""

NAME = "Priority (preemptive)"
SHORT = "PRIO-P"
PREEMPTIVE = True
USES_QUANTUM = False
USES_PRIORITY = True
DESCRIPTION = ("Priority (preemptive): a ready process with a better priority (lower number) than the "
               "running one takes the CPU immediately.")


def choose_next(ready, running, sim):
    if not ready:
        return running
    best = min(ready, key=lambda p: (p.eff_priority, p.arrival))
    if running is not None and running.eff_priority <= best.eff_priority:
        return running          # the running process is at least as important (a tie does not preempt)
    return best                 # preempt: a more important process is waiting
