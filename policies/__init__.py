"""Scheduling policies.

Every policy is one small module with the same "contract":

    NAME, SHORT        names shown in the interface
    PREEMPTIVE         can it take the CPU away from a running process?
    USES_QUANTUM       does it use the time quantum?   (Round Robin)
    USES_PRIORITY      does it use process priority?   (aging only works then)
    DESCRIPTION        one or two sentences for the user

    choose_next(ready, running, sim)
        ready    list of READY processes, in the order they joined the ready queue
        running  the process on the CPU now, or None
        sim      the simulator (read only: sim.time, sim.quantum, sim.slice_used)
        returns  the process that should use the CPU during the next tick:
                 `running` to let it continue, a process from `ready`, or None (idle)

To add a new policy: copy one of these files, change choose_next(),
and add the module to the list below. Nothing else has to change.
"""

from policies import fcfs, sjf, srtf, priority, priority_preemptive, rr

ALL = [fcfs, sjf, srtf, priority, priority_preemptive, rr]
POLICIES = {module.NAME: module for module in ALL}
