"""The main window: builds every panel and connects the panels to the simulator."""

import random
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

from core import metrics, samples
from core.engine import Simulator
from core.pcb import PCB
from gui import theme
from gui.compare import CompareTab
from gui.controls import ControlBar
from gui.gantt import GanttChart
from gui.pcb_table import EventLog, PCBTable
from gui.process_form import ProcessForm
from gui.results import ResultsTab
from gui.state_board import StateBoard
from policies import POLICIES

MAX_PROCESSES = 12


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Mini CPU Task Manager")
        width = min(1280, self.winfo_screenwidth() - 40)      # fit on small screens too
        height = min(820, self.winfo_screenheight() - 90)
        self.geometry(f"{width}x{height}")
        self.minsize(min(1100, width), min(680, height))
        theme.setup(self)

        self.workload = []           # the processes the user defined (a list of PCBs)
        self.sim = None              # the current simulation
        self.colors = {}             # pid -> colour
        self.hint = ""               # what to try with the loaded sample (shown in the status bar)
        self.running = False         # is the clock running by itself?
        self._timer = None           # the scheduled next tick, if any

        self._build()
        self.bind("<F5>", lambda event: self.start_pause())
        self.bind("<F6>", lambda event: self.step())
        self.bind("<F7>", lambda event: self.reset())
        self.load_sample(samples.DEFAULT_SAMPLE)

    # ------------------------------------------------------------------ layout

    def _build(self):
        self.controls = ControlBar(self, list(POLICIES), self.start_pause, self.step, self.reset, self.reset)
        self.controls.pack(fill="x")
        # The status bar is packed before the tabs, so it stays visible when the window is small.
        self.status = ttk.Label(self, style="Muted.TLabel", anchor="w", padding=(12, 6))
        self.status.pack(side="bottom", fill="x")

        tabs = ttk.Notebook(self)
        tabs.pack(fill="both", expand=True, padx=10, pady=(4, 0))
        simulation = ttk.Frame(tabs, padding=10)
        self.results = ResultsTab(tabs)
        self.compare = CompareTab(tabs, lambda: self.workload, self.controls.settings)
        tabs.add(simulation, text="Simulation")
        tabs.add(self.results, text="Results")
        tabs.add(self.compare, text="Compare policies")

        # Simulation tab, left side: the workload form.
        self.form = ProcessForm(simulation, list(samples.SAMPLES), self.add_process, self.remove_selected,
                                self.clear_all, self.load_sample, self.random_workload)
        self.form.pack(side="left", fill="y", padx=(0, 10))

        # Simulation tab, right side: state board, Gantt chart, PCB table and event log.
        right = ttk.Frame(simulation)
        right.pack(side="left", fill="both", expand=True)
        self.board = StateBoard(right)
        self.board.pack(fill="both", expand=True)
        self.gantt = GanttChart(right)
        self.gantt.pack(fill="x", pady=8)
        bottom = ttk.PanedWindow(right, orient="horizontal")
        bottom.pack(fill="both", expand=True)
        self.table = PCBTable(bottom, actions=[("Kill", self.kill_selected), ("Suspend", self.suspend_selected),
                                               ("Resume", self.resume_selected),
                                               ("Priority...", self.change_priority)])
        self.log = EventLog(bottom)
        bottom.add(self.table, weight=3)
        bottom.add(self.log, weight=1)


    # ------------------------------------------------------------------ simulation control

    def reset(self):
        """Start again from time 0 with the current workload and settings."""
        self._stop_clock()
        settings = self.controls.settings()
        policy = POLICIES[settings["policy"]]
        self.sim = Simulator(self.workload, policy, settings["quantum"], settings["cs_cost"], settings["aging"])
        self.colors = theme.process_colors([p.pid for p in self.workload])
        self.controls.show_policy(policy)
        self.log.clear()
        self.refresh(animate=False)

    def step(self):
        """The Step button: advance exactly one tick."""
        self._stop_clock()
        self._advance()

    def start_pause(self):
        """The Start / Pause / Restart button."""
        if self.running:
            self._stop_clock()
        elif self.workload:
            if self.sim.finished:
                self.reset()                             # "Restart"
            self.running = True
            self._tick()
        self._show_status()

    def _tick(self):
        """One automatic tick; then schedule the next one."""
        self._advance()
        if self.sim.finished or self.sim.stalled:        # stalled: only suspended processes are left
            self.running = False
            self._show_status()
        elif self.running:
            self._timer = self.after(self.controls.delay_ms(), self._tick)

    def _advance(self):
        if self.sim.finished:
            return
        events = self.sim.step()                         # <- the simulator does the real work
        self.log.add(events)
        slow_enough = not self.running or self.controls.delay_ms() >= 200
        self.refresh(animate=slow_enough)

    def _stop_clock(self):
        self.running = False
        if self._timer is not None:
            self.after_cancel(self._timer)
            self._timer = None

    def destroy(self):
        self._stop_clock()                               # no tick may fire after the window has closed
        super().destroy()

    # ------------------------------------------------------------------ display

    def refresh(self, animate=True):
        """Show the simulator's current state in every panel."""
        self.board.show(self.sim, self.colors, animate)
        self.gantt.show(self.sim, self.colors)
        self.table.show(self.sim)
        self.results.show(self.sim)
        self._show_status()

    def _show_status(self):
        sim = self.sim
        m = metrics.summary(sim)
        self.controls.show_state(sim.time, self.running, sim.finished and bool(sim.processes))
        if not sim.processes:
            text = "Add a process or load a sample workload to begin."
        elif sim.stalled:
            text = (f"Time {sim.time}:  only suspended processes are left, so nothing can run.  "
                    f"Select one in the PCB table and press Resume (or Kill).")
        elif sim.finished:
            text = (f"Finished at time {sim.time}:  {m['context_switches']} context switches,  "
                    f"CPU utilisation {m['cpu_utilisation']:.0f}%.  Open the Results tab, or compare the policies.")
        elif sim.time == 0:
            text = (self.hint or "Ready.") + "   Start = F5,  Step = F6,  Reset = F7."
        else:
            text = (f"Time {sim.time}:  {m['finished']} of {m['processes']} processes finished   |   "
                    f"{m['context_switches']} context switches   |   CPU utilisation {m['cpu_utilisation']:.0f}%")
        self.status.configure(text=text)

    # ------------------------------------------------------------------ editing the workload

    def add_process(self, process):
        if any(p.pid == process.pid for p in self.workload):
            messagebox.showerror("Cannot add the process", f"A process named {process.pid} already exists.",
                                 parent=self)
        elif len(self.workload) >= MAX_PROCESSES:
            messagebox.showerror("Cannot add the process", f"The limit is {MAX_PROCESSES} processes.", parent=self)
        elif self.sim.time > 0 and not self.sim.finished:
            # The simulation is under way: create the process live, without starting again.
            process.arrival = max(process.arrival, self.sim.time)        # it cannot arrive in the past
            self.workload.append(process)                                # so that Reset replays it too
            self.log.add(self.sim.create(process))
            self.colors = theme.process_colors([p.pid for p in self.sim.processes])
            self._suggest_next_pid()
            self.compare.clear()
            self.refresh(animate=False)
        else:
            self.workload.append(process)
            self._workload_changed()

    # ------------------------------------------------------------------ managing a live process

    def kill_selected(self):
        self._manage(self.sim.kill)

    def suspend_selected(self):
        self._manage(self.sim.suspend)

    def resume_selected(self):
        self._manage(self.sim.resume)

    def change_priority(self, priority=None):
        """Ask for a new priority (unless one is given) and set it for the selected process."""
        if not self._selected_live():
            return
        if priority is None:
            priority = simpledialog.askinteger("Change priority", "New priority (a lower number is more important):",
                                               minvalue=0, maxvalue=99, parent=self)
        if priority is not None:
            self._manage(lambda pid: self.sim.set_priority(pid, priority))

    def _selected_live(self):
        selected = self.table.selected_pids()
        if not selected:
            messagebox.showinfo("Manage a process", "First click a row in the PCB table.", parent=self)
        return selected

    def _manage(self, operation):
        """Apply one task-manager operation of the simulator to the selected processes."""
        for pid in self._selected_live():
            try:
                self.log.add(operation(pid))
            except ValueError as error:                  # for example: resume a process that is not suspended
                messagebox.showerror("Not possible", str(error), parent=self)
        self.refresh()

    def remove_selected(self):
        selected = self.table.selected_pids()
        if not selected:
            messagebox.showinfo("Remove a process", "First click a row in the PCB table.", parent=self)
            return
        self.workload = [p for p in self.workload if p.pid not in selected]
        self._workload_changed()

    def clear_all(self):
        self.workload = []
        self._workload_changed()

    def load_sample(self, name):
        self.workload = samples.load(name)
        self._workload_changed(hint=samples.HINTS.get(name, ""))

    def random_workload(self):
        arrivals = sorted(random.randint(0, 8) for _ in range(random.randint(4, 6)))
        self.workload = []
        for i, arrival in enumerate(arrivals):
            burst = random.randint(2, 9)
            io_at = random.randint(1, burst - 1) if random.random() < 0.3 else None
            self.workload.append(PCB(f"P{i + 1}", arrival, burst, random.randint(1, 5),
                                     io_at, random.randint(2, 4) if io_at else 0))
        self._workload_changed()

    def _workload_changed(self, hint=""):
        self.hint = hint
        self._suggest_next_pid()
        self.compare.clear()
        self.reset()

    def _suggest_next_pid(self):
        used = {p.pid for p in self.workload}
        number = 1
        while f"P{number}" in used:
            number += 1
        self.form.suggest_pid(f"P{number}")              # the name for the next new process
