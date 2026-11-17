"""The PCB table (one row per process) and the event log."""

import sys
import tkinter as tk
from tkinter import ttk

from core.engine import show_context
from core.pcb import RUNNING, STATES
from gui import theme


class PCBTable(ttk.Frame):
    """Shows the live content of every Process Control Block."""

    COLUMNS = [                      # (key, heading, relative width)
        ("pid", "PID", 38), ("state", "State", 104), ("arrival", "Arrival", 54), ("burst", "Burst", 46),
        ("remaining", "Left", 40), ("context", "Saved context", 112), ("priority", "Priority", 58),
        ("io", "I/O", 80), ("waited", "Waited", 54), ("start", "Start", 44), ("finish", "Finish", 62),
    ]

    def __init__(self, parent, actions=()):
        """`actions` are the task-manager buttons: [(label, function), ...]. They act on the selected row."""
        super().__init__(parent)
        top = ttk.Frame(self)
        top.pack(fill="x", pady=(0, 4))
        ttk.Label(top, text="Process Control Blocks", style="Title.TLabel").pack(side="left")
        self.menu = tk.Menu(self, tearoff=False)         # the same actions, on a right-click
        for label, function in reversed(actions):
            ttk.Button(top, text=label, style="Small.TButton", command=function).pack(side="right", padx=(4, 0))
        for label, function in actions:
            self.menu.add_command(label=label, command=function)
        body = ttk.Frame(self)
        body.pack(fill="both", expand=True)
        self.tree = ttk.Treeview(body, columns=[key for key, _, _ in self.COLUMNS], show="headings", height=5)
        for key, heading, width in self.COLUMNS:
            self.tree.heading(key, text=heading)
            self.tree.column(key, width=width, minwidth=30, anchor="center", stretch=False)
        for state in STATES:                             # row colour = process state
            self.tree.tag_configure(state, background=theme.STATE_TINTS[state])
        scrollbar = ttk.Scrollbar(body, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.tree.pack(side="left", fill="both", expand=True)
        self.tree.bind("<Configure>", self._fit_columns)
        if actions:
            # The right mouse button. On a Mac it is button 2, and Control + click means the same.
            # (On Windows, Control + click must stay free: it selects several rows.)
            clicks = ("<Button-2>", "<Button-3>", "<Control-Button-1>") if sys.platform == "darwin" else ("<Button-3>",)
            for click in clicks:
                self.tree.bind(click, self._show_menu)

    def _show_menu(self, event):
        """Right-click: select the row under the mouse and offer the task-manager actions."""
        row = self.tree.identify_row(event.y)
        if row:
            self.tree.selection_set(row)
            self.menu.tk_popup(event.x_root, event.y_root)

    def _fit_columns(self, event):
        """Share the table's width between the columns, so that no column is cut off."""
        total = sum(width for _key, _heading, width in self.COLUMNS)
        for key, _heading, width in self.COLUMNS:
            self.tree.column(key, width=int((event.width - 4) * width / total))

    @staticmethod
    def _values(p):
        dash = "-"
        priority = str(p.priority) if p.eff_priority == p.priority else f"{p.priority} -> {p.eff_priority}"
        io = f"at {p.io_at} for {p.io_time}" if p.io_at is not None else dash
        # While a process runs, its registers are in the CPU; the copy in the PCB is out of date.
        context = "(on the CPU)" if p.state == RUNNING else show_context(p.context)
        finish = dash if p.finish is None else (f"{p.finish} killed" if p.killed else p.finish)
        return (p.pid, p.state, p.arrival, p.burst, p.remaining, context, priority, io, p.waited,
                dash if p.start is None else p.start, finish)

    def show(self, sim):
        pids = [p.pid for p in sim.processes]
        if list(self.tree.get_children()) != pids:       # the workload changed: build the rows again
            self.tree.delete(*self.tree.get_children())
            for p in sim.processes:
                self.tree.insert("", "end", iid=p.pid, values=self._values(p), tags=(p.state,))
        else:                                            # same processes: only refresh the values
            for p in sim.processes:
                self.tree.item(p.pid, values=self._values(p), tags=(p.state,))

    def selected_pids(self):
        return list(self.tree.selection())


class EventLog(ttk.Frame):
    """A scrolling list of everything the scheduler did, with the time it happened."""

    COLORS = {
        "arrive": theme.STATE_COLORS["READY"], "dispatch": theme.STATE_COLORS["RUNNING"],
        "preempt": "#B4530A", "switch": theme.SWITCH_COLOR, "io": theme.STATE_COLORS["WAITING"],
        "io_done": "#0E7C86", "finish": theme.STATE_COLORS["TERMINATED"], "aging": "#B0277F",
        "manage": theme.MANAGE_COLOR,
    }

    def __init__(self, parent):
        super().__init__(parent)
        ttk.Label(self, text="Event log", style="Title.TLabel").pack(anchor="w", pady=(0, 4))
        body = ttk.Frame(self)
        body.pack(fill="both", expand=True)
        self.text = tk.Text(body, height=8, width=30, wrap="word", state="disabled", relief="flat",
                            background=theme.PANEL, foreground=theme.TEXT, font=theme.FONTS["small"],
                            highlightthickness=1, highlightbackground=theme.LINE, padx=8, pady=6)
        scrollbar = ttk.Scrollbar(body, orient="vertical", command=self.text.yview)
        self.text.configure(yscrollcommand=scrollbar.set)
        self.text.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.text.tag_configure("time", foreground=theme.MUTED, font=theme.FONTS["small_bold"])
        for kind, color in self.COLORS.items():
            self.text.tag_configure(kind, foreground=color)
        for kind in ("switch", "manage"):
            self.text.tag_configure(kind, font=theme.FONTS["small_bold"])

    def add(self, events):
        if not events:
            return
        self.text.configure(state="normal")
        for time, kind, message in events:
            self.text.insert("end", f"t={time:<3} ", "time")
            self.text.insert("end", message + "\n", kind)
        self.text.configure(state="disabled")
        self.text.see("end")                             # scroll to the newest event

    def clear(self):
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self.text.configure(state="disabled")
