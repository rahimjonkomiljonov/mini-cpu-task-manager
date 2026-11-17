"""Round Robin (RR): every process gets the CPU for one time quantum, in turn."""

NAME = "Round Robin"
SHORT = "RR"
PREEMPTIVE = True
USES_QUANTUM = True
USES_PRIORITY = False
DESCRIPTION = ("Round Robin: each process runs for at most one time quantum, then goes to the back of the "
               "ready queue. Fair and responsive; a small quantum causes many context switches.")


def choose_next(ready, running, sim):
    if running is not None and sim.slice_used < sim.quantum:
        return running          # its time slice is not over yet
    if ready:
        return ready[0]         # next in line (the engine moves the old process to the tail)
    return running              # nobody else is ready: keep running (or stay idle)
