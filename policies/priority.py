"""Priority scheduling, non-preemptive. A LOWER number means a HIGHER priority."""

NAME = "Priority"
SHORT = "PRIO"
PREEMPTIVE = False
USES_QUANTUM = False
USES_PRIORITY = True
DESCRIPTION = ("Priority (non-preemptive): when the CPU becomes free, the ready process with the best "
               "priority (lowest number) goes next. Low-priority processes can starve; aging fixes that.")


def choose_next(ready, running, sim):
    if running is not None:
        return running          # non-preemptive
    if ready:
        # eff_priority is the base priority improved by aging (when aging is on).
        return min(ready, key=lambda p: (p.eff_priority, p.arrival))
    return None
