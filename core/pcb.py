"""Process Control Block (PCB).

The PCB is the record an operating system keeps for every process.
Our simulated PCB holds the same kinds of information as a real one:
identity, state, a "program counter", scheduling information and accounting.
"""

# The five classic process states (the process state diagram), plus SUSPENDED.
NEW = "NEW"                # created, but not yet admitted to the ready queue
READY = "READY"            # in the ready queue, waiting for the CPU
RUNNING = "RUNNING"        # using the CPU right now
WAITING = "WAITING"        # blocked until its I/O operation finishes
SUSPENDED = "SUSPENDED"    # paused by the user (the task manager) until it is resumed
TERMINATED = "TERMINATED"  # finished, or killed by the user

STATES = (NEW, READY, RUNNING, WAITING, SUSPENDED, TERMINATED)


class PCB:
    """Everything the simulated OS knows about one process."""

    def __init__(self, pid, arrival, burst, priority=1, io_at=None, io_time=0):
        # ---- the workload: given by the user, never changes ----
        self.pid = str(pid).strip()      # process name, for example "P1"
        self.arrival = int(arrival)      # time the process enters the system
        self.burst = int(burst)          # total CPU time the process needs
        self.priority = int(priority)    # base priority: a LOWER number is MORE important
        # Optional I/O: after `io_at` units of CPU time the process blocks for `io_time` units.
        # "No I/O" is written as None (or an empty field), never as 0: a 0 is a mistake and is refused.
        self.io_at = None if io_at in (None, "") else int(io_at)
        self.io_time = int(io_time or 0)
        self._check()
        self.reset()

    def _check(self):
        """Refuse a workload that makes no sense (raises ValueError)."""
        if not self.pid:
            raise ValueError("The process needs a name (PID).")
        if self.arrival < 0:
            raise ValueError("Arrival time cannot be negative.")
        if self.burst < 1:
            raise ValueError("Burst time must be at least 1.")
        if self.priority < 0:
            raise ValueError("Priority cannot be negative.")
        if self.io_at is not None:
            if not 1 <= self.io_at < self.burst:
                raise ValueError("I/O must start after at least 1 CPU unit and before the burst ends.")
            if self.io_time < 1:
                raise ValueError("I/O time must be at least 1.")
        elif self.io_time:
            raise ValueError("An I/O duration was given, but not when the I/O starts.")

    def reset(self):
        """Put the process back to the moment before the simulation starts."""
        # ---- the changing part of the PCB: managed by the simulator ----
        self.state = NEW
        self.remaining = self.burst          # CPU time still needed
        self.eff_priority = self.priority    # effective priority (aging can improve it)
        self.io_left = 0                     # I/O time still needed while WAITING
        self.io_done = False                 # has the I/O operation already happened?
        # The saved CPU context: the register values this process had when it last left the CPU.
        # A context switch copies the CPU registers here (save) and later back to the CPU (restore).
        self.context = {"PC": 0, "ACC": 0}
        self.killed = False                  # terminated by the user before it finished?
        # ---- accounting: used for the scheduling metrics ----
        self.start = None                    # first time the process got the CPU
        self.finish = None                   # time the process terminated
        self.waited = 0                      # ticks spent in the READY queue
        self.dispatches = 0                  # how many times it was given the CPU
        self.aged = 0                        # ticks waited since the last priority boost
        self.io_waited = 0                   # ticks spent in the WAITING state
        self.suspended_time = 0              # ticks spent in the SUSPENDED state

    def clone(self):
        """A fresh copy with the same workload (state and accounting start again)."""
        return PCB(self.pid, self.arrival, self.burst, self.priority, self.io_at, self.io_time)

    # ---- values calculated from the PCB ----

    @property
    def pc(self):
        """'Program counter': how many CPU units the process has executed so far."""
        return self.burst - self.remaining

    @property
    def next_burst(self):
        """Length of the next CPU burst: CPU time until the process asks for I/O, or until it ends.

        A process with I/O has two CPU bursts (before and after the I/O). SJF and SRTF compare this value.
        """
        if self.io_at is not None and not self.io_done:
            return self.io_at - self.pc
        return self.remaining

    @property
    def turnaround(self):
        """Turnaround time = finish - arrival (None until the process terminates)."""
        return None if self.finish is None else self.finish - self.arrival

    @property
    def response(self):
        """Response time = first time on the CPU - arrival (None until it first runs)."""
        return None if self.start is None else self.start - self.arrival

    def __repr__(self):
        return f"PCB({self.pid}, {self.state}, arrival={self.arrival}, remaining={self.remaining}/{self.burst})"
