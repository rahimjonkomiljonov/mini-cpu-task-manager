"""The simulator: a small CPU scheduler driven by a clock.

One call of step() simulates one time unit ("tick"), the interval [time, time + 1):

    1. processes that arrive now are admitted:        NEW     -> READY
    2. processes whose I/O is complete come back:     WAITING -> READY
    3. the scheduling policy decides who gets the CPU (a context switch may happen)
    4. the CPU executes one unit; READY processes wait; I/O makes progress
    5. at the end of the tick the running process leaves the CPU
       if it has finished (-> TERMINATED) or needs I/O (-> WAITING)

The simulator never decides WHO runs next. It always asks the policy
(see the `policies` package), so every policy plugs into the same engine.

Between two ticks the user can also manage a live process, like in a real task manager:
create(), kill(), suspend(), resume() and set_priority().
"""

from core.pcb import NEW, READY, RUNNING, WAITING, SUSPENDED, TERMINATED

IDLE = "idle"        # Gantt label: nobody is using the CPU
SWITCH = "CS"        # Gantt label: the CPU is busy doing a context switch
AGING_INTERVAL = 3   # with aging on, a READY process gains one priority level every 3 ticks it waits


def show_context(context):
    """The register values as text, for the event log and the window."""
    return f"PC={context['PC']}, ACC={context['ACC']}"


class Simulator:
    def __init__(self, workload, policy, quantum=2, cs_cost=0, aging=False):
        # Fresh copies of the PCBs, so the same workload can be simulated again and again.
        self.processes = [p.clone() for p in workload]
        self.policy = policy                  # a module from the `policies` package
        self.quantum = max(1, int(quantum))   # time slice (used by Round Robin)
        self.cs_cost = max(0, int(cs_cost))   # ticks one context switch costs (0 = free)
        self.aging = bool(aging) and getattr(policy, "USES_PRIORITY", False)

        self.time = 0                # the clock
        self.ready = []              # the ready queue: PCBs in the order they became ready
        self.running = None          # the PCB on the CPU (None = no process)
        self.slice_used = 0          # ticks the running process has used in its current turn
        self.gantt = []              # one label per tick: a PID, IDLE or SWITCH
        self.events = []             # the event log: (time, kind, text)
        self.context_switches = 0
        self.finished = not self.processes

        # The simulated CPU has two registers. Only ONE process can use them at a time, so a
        # context switch must save them in the PCB of the old process and load the values of the new one.
        #   PC   program counter: the number of CPU units the running process has executed
        #   ACC  accumulator: every unit adds the new PC to it (a stand-in for "the data of the program")
        self.cpu = {"PC": 0, "ACC": 0}
        self.last_saved = None       # (pid, context) of the latest save, shown during a context switch

        self._last_on_cpu = None     # the process that used the CPU during the previous tick
        self._switch_left = 0        # ticks still needed to complete a context switch
        self._switch_target = None   # the process that gets the CPU when the switch is over

    # ------------------------------------------------------------------ one tick

    def step(self):
        """Simulate one tick. Returns the events that happened during this call."""
        first_new_event = len(self.events)
        if not self.finished:
            t = self.time
            self._admit_arrivals(t)
            self._finish_io(t)
            self._schedule(t)
            self._run_one_tick(t)
            self.time = t + 1
            self._leave_cpu(t + 1)
            self._check_finished()
        return self.events[first_new_event:]

    def run_all(self, max_ticks=100000):
        """Run until every process has terminated."""
        while not self.finished:
            if self.time > max_ticks or self.stalled:
                raise RuntimeError("The simulation does not end (check the policy, or resume the "
                                   "suspended processes).")
            self.step()
        return self

    @property
    def stalled(self):
        """True when only SUSPENDED processes are left: nothing can happen until the user acts."""
        alive = [p for p in self.processes if p.state != TERMINATED]
        return bool(alive) and all(p.state == SUSPENDED for p in alive)

    def _check_finished(self):
        self.finished = all(p.state == TERMINATED for p in self.processes)

    # ------------------------------------------------------------------ the five phases

    def _admit_arrivals(self, t):
        """Phase 1: NEW -> READY for every process whose arrival time has come."""
        for p in self.processes:
            if p.state == NEW and p.arrival <= t:
                p.state = READY
                self.ready.append(p)
                self._log(t, "arrive", f"{p.pid} arrived: NEW -> READY "
                                       f"(burst {p.burst}, priority {p.priority})")

    def _finish_io(self, t):
        """Phase 2: WAITING -> READY for every process whose I/O is complete."""
        for p in self.processes:
            if p.state == WAITING and p.io_left <= 0:
                p.state = READY
                self.ready.append(p)
                self._log(t, "io_done", f"{p.pid} completed I/O: WAITING -> READY")

    def _schedule(self, t):
        """Phase 3: ask the policy who should use the CPU during this tick."""
        if self._switch_left > 0:
            return                              # a context switch is still in progress
        if self._switch_target is not None:     # the switch is over: the CPU is free now
            # Ask the policy again. While the switch was in progress a better process may have
            # arrived, or the user may have killed / suspended the process we were switching to.
            planned, self._switch_target = self._switch_target, None
            chosen = self.policy.choose_next(self.ready, None, self)
            if chosen is not None:
                if chosen is not planned:
                    self._log(t, "switch", f"The ready queue changed during the switch: "
                                           f"{chosen.pid} gets the CPU instead of {planned.pid}")
                self._dispatch(chosen, t)
            return

        chosen = self.policy.choose_next(self.ready, self.running, self)

        if chosen is None or chosen is self.running:
            # Nothing changes. In Round Robin, a process whose quantum has expired
            # while nobody else is ready simply receives a fresh time slice.
            if (self.running is not None and getattr(self.policy, "USES_QUANTUM", False)
                    and self.slice_used >= self.quantum):
                self.slice_used = 0
            return

        # The CPU changes hands.
        previous = self.running if self.running is not None else self._last_on_cpu
        if self.running is not None:            # the running process is preempted
            old = self.running
            self._save_context(old)
            old.state = READY
            self.ready.append(old)              # it goes to the tail of the ready queue
            self.running = None
            self._log(t, "preempt", f"{old.pid} preempted: RUNNING -> READY "
                                    f"(context saved in its PCB: {show_context(old.context)})")

        if previous is not None and previous is not chosen:
            self.context_switches += 1
            cost = f", costs {self.cs_cost} tick(s)" if self.cs_cost else ""
            self._log(t, "switch", f"Context switch #{self.context_switches}: "
                                   f"{previous.pid} -> {chosen.pid}{cost}")
            if self.cs_cost > 0:                # the switch itself takes CPU time
                self._switch_left = self.cs_cost
                self._switch_target = chosen
                return

        self._dispatch(chosen, t)

    def _dispatch(self, p, t):
        """Give the CPU to process p: READY -> RUNNING."""
        self.ready.remove(p)
        p.state = RUNNING
        p.dispatches += 1
        if p.start is None:
            p.start = t                          # first time on the CPU (for response time)
        self.running = p
        self.slice_used = 0
        self.cpu = dict(p.context)               # restore: PCB -> CPU registers
        self._log(t, "dispatch", f"{p.pid} dispatched: READY -> RUNNING "
                                 f"(context loaded from its PCB: {show_context(p.context)})")

    def _save_context(self, p):
        """Save: CPU registers -> PCB. Called every time a process leaves the CPU."""
        p.context = dict(self.cpu)
        self.last_saved = (p.pid, dict(self.cpu))

    def _run_one_tick(self, t):
        """Phase 4: time passes for everybody."""
        if self._switch_left > 0:                # the CPU is saving / loading PCBs
            self.gantt.append(SWITCH)
            self._switch_left -= 1
            self._last_on_cpu = None
        elif self.running is None:               # nobody to run
            self.gantt.append(IDLE)
            self._last_on_cpu = None
        else:                                    # the running process executes one unit
            self.running.remaining -= 1
            self.cpu["PC"] += 1                  # the work happens in the CPU registers,
            self.cpu["ACC"] += self.cpu["PC"]    # not in the PCB
            self.slice_used += 1
            self.gantt.append(self.running.pid)
            self._last_on_cpu = self.running

        for p in self.ready:                     # everybody in the ready queue waits
            p.waited += 1
            if self.aging:
                self._age(p, t + 1)

        for p in self.processes:
            if p.state == WAITING:               # I/O devices work in parallel with the CPU
                p.io_left -= 1
                p.io_waited += 1
            elif p.state == SUSPENDED:           # a suspended process does nothing at all
                p.suspended_time += 1

    def _leave_cpu(self, t):
        """Phase 5: at the end of the tick, the running process terminates or blocks for I/O."""
        p = self.running
        if p is None:
            return
        if p.remaining == 0:
            self._save_context(p)
            p.state = TERMINATED
            p.finish = t
            self.running = None
            self._log(t, "finish", f"{p.pid} finished: RUNNING -> TERMINATED "
                                   f"(turnaround {p.turnaround}, waited {p.waited})")
        elif p.io_at is not None and not p.io_done and p.pc >= p.io_at:
            self._save_context(p)
            p.state = WAITING
            p.io_left = p.io_time
            p.io_done = True
            self.running = None
            self._log(t, "io", f"{p.pid} requests I/O: RUNNING -> WAITING for {p.io_time} ticks "
                               f"(context saved in its PCB: {show_context(p.context)})")

    def _age(self, p, t):
        """Aging: the longer a process waits, the more important it becomes."""
        p.aged += 1
        if p.aged >= AGING_INTERVAL and p.eff_priority > 0:
            p.aged = 0
            p.eff_priority -= 1
            self._log(t, "aging", f"Aging: {p.pid} has waited long, "
                                  f"priority {p.eff_priority + 1} -> {p.eff_priority}")

    # ------------------------------------------------------------------ managing a live process
    #
    # These are the "task manager" operations. The user calls them between two ticks.
    # Each one returns the events it logged. A request that makes no sense raises ValueError.

    def create(self, process):
        """Create a process while the simulation runs. It cannot arrive in the past."""
        if self.find(process.pid) is not None:
            raise ValueError(f"A process named {process.pid} already exists.")
        first_new_event = len(self.events)
        p = process.clone()
        p.arrival = max(p.arrival, self.time)
        self.processes.append(p)
        self.finished = False
        self._log(self.time, "manage", f"{p.pid} created by the user: NEW (arrives at {p.arrival}, "
                                       f"burst {p.burst}, priority {p.priority})")
        return self.events[first_new_event:]

    def kill(self, pid):
        """Terminate a process immediately, whatever it is doing."""
        p = self._alive(pid)
        first_new_event = len(self.events)
        old_state = p.state
        self._take_away(p)
        p.state = TERMINATED
        p.killed = True
        p.finish = self.time
        self._log(self.time, "manage", f"{p.pid} killed by the user: {old_state} -> TERMINATED "
                                       f"({p.remaining} of {p.burst} CPU units were never executed)")
        self._check_finished()
        return self.events[first_new_event:]

    def suspend(self, pid):
        """Pause a process: it keeps its PCB, but it cannot get the CPU until it is resumed.

        If it was doing I/O, the I/O is paused too and continues after resume().
        """
        p = self._alive(pid)
        if p.state == NEW:
            raise ValueError(f"{p.pid} has not arrived yet, so it cannot be suspended.")
        if p.state == SUSPENDED:
            raise ValueError(f"{p.pid} is already suspended.")
        first_new_event = len(self.events)
        old_state = p.state
        self._take_away(p)
        p.state = SUSPENDED
        saved = f" (context saved in its PCB: {show_context(p.context)})" if old_state == RUNNING else ""
        self._log(self.time, "manage", f"{p.pid} suspended by the user: {old_state} -> SUSPENDED{saved}")
        return self.events[first_new_event:]

    def resume(self, pid):
        """Continue a suspended process: back to the ready queue (or back to its unfinished I/O)."""
        p = self._alive(pid)
        if p.state != SUSPENDED:
            raise ValueError(f"{p.pid} is not suspended.")
        first_new_event = len(self.events)
        if p.io_left > 0:
            p.state = WAITING
        else:
            p.state = READY
            self.ready.append(p)                 # like everybody else: at the tail of the ready queue
        self._log(self.time, "manage", f"{p.pid} resumed by the user: SUSPENDED -> {p.state}")
        return self.events[first_new_event:]

    def set_priority(self, pid, priority):
        """Change the priority of a live process (a lower number is more important)."""
        p = self._alive(pid)
        priority = int(priority)
        if priority < 0:
            raise ValueError("Priority cannot be negative.")
        first_new_event = len(self.events)
        old = p.eff_priority
        p.priority = p.eff_priority = priority
        p.aged = 0
        used = "" if getattr(self.policy, "USES_PRIORITY", False) else " (this policy ignores priority)"
        self._log(self.time, "manage", f"{p.pid} priority changed by the user: {old} -> {priority}{used}")
        return self.events[first_new_event:]

    def find(self, pid):
        """The PCB with this PID, or None."""
        for p in self.processes:
            if p.pid == pid:
                return p
        return None

    def _alive(self, pid):
        p = self.find(pid)
        if p is None:
            raise ValueError(f"There is no process named {pid}.")
        if p.state == TERMINATED:
            raise ValueError(f"{p.pid} has already terminated.")
        return p

    def _take_away(self, p):
        """Remove a process from the CPU or from the ready queue (before a kill or a suspend)."""
        if p is self.running:
            self._save_context(p)
            self.running = None                  # _last_on_cpu stays: the next dispatch is a context switch
        elif p in self.ready:
            self.ready.remove(p)
        # If p was the target of a context switch in progress, _schedule() asks the policy again
        # when the switch is over, and p is no longer in the ready queue.

    # ------------------------------------------------------------------ helpers

    def _log(self, t, kind, text):
        self.events.append((t, kind, text))

    @property
    def switch_target(self):
        """During a context switch: the process that is being loaded (else None)."""
        return self._switch_target if self._switch_target in self.ready else None

    def gantt_blocks(self):
        """The Gantt chart as merged blocks: [(label, start, end), ...]."""
        blocks = []
        for t, label in enumerate(self.gantt):
            if blocks and blocks[-1][0] == label:
                blocks[-1][2] = t + 1            # the same label continues: make the block longer
            else:
                blocks.append([label, t, t + 1])
        return [tuple(b) for b in blocks]
