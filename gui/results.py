"""The Results tab: scheduling metrics for every process and for the whole run."""

from tkinter import ttk

from core import metrics
from gui import theme


class ResultsTab(ttk.Frame):
    COLUMNS = [                      # (key, heading)
        ("pid", "PID"), ("arrival", "Arrival"), ("burst", "Burst"), ("io_time", "I/O time"),
        ("start", "Start"), ("finish", "Finish"), ("turnaround", "Turnaround"),
        ("waiting", "Waiting"), ("response", "Response"),
    ]
    TILES = [                        # (key, caption)
        ("avg_turnaround", "Average turnaround"), ("avg_waiting", "Average waiting"),
        ("avg_response", "Average response"), ("cpu_utilisation", "CPU utilisation"),
        ("throughput", "Throughput (per tick)"), ("context_switches", "Context switches"),
        ("switch_time", "Ticks lost to switching"), ("idle_time", "Idle ticks"),
    ]

    def __init__(self, parent):
        super().__init__(parent, padding=14)

        # ---- summary tiles ----
        tiles = ttk.Frame(self)
        tiles.pack(fill="x")
        self.values = {}
        for i, (key, caption) in enumerate(self.TILES):
            tile = ttk.Frame(tiles, style="Panel.TFrame", padding=(14, 10))
            tile.grid(row=i // 4, column=i % 4, sticky="nsew", padx=5, pady=5)
            tiles.columnconfigure(i % 4, weight=1, uniform="tile")
            self.values[key] = ttk.Label(tile, text="-", style="Panel.TLabel", font=theme.FONTS["big"])
            self.values[key].pack(anchor="w")
            ttk.Label(tile, text=caption, style="PanelMuted.TLabel").pack(anchor="w")

        # ---- one row per process ----
        self.progress = ttk.Label(self, style="Title.TLabel")
        self.progress.pack(anchor="w", pady=(14, 4))
        self.tree = ttk.Treeview(self, columns=[key for key, _ in self.COLUMNS], show="headings", height=12)
        for key, heading in self.COLUMNS:
            self.tree.heading(key, text=heading)
            self.tree.column(key, width=90, anchor="center")
        self.tree.tag_configure("average", background="#E6EEFC", font=theme.FONTS["bold"])
        self.tree.pack(fill="both", expand=True)

        ttk.Label(self, style="Muted.TLabel", justify="left",
                  text="Turnaround = Finish - Arrival        Waiting = time spent in the READY queue        "
                       "Response = first time on the CPU - Arrival\n"
                       "For a process without I/O:  Waiting = Turnaround - Burst.   "
                       "Averages use the processes that have finished so far; killed processes are left out."
                  ).pack(anchor="w", pady=(8, 0))

    @staticmethod
    def _text(value, decimals=2, suffix=""):
        if value is None:
            return "-"
        return (f"{value:.{decimals}f}" if isinstance(value, float) else str(value)) + suffix

    def show(self, sim):
        m = metrics.summary(sim)
        for key, _caption in self.TILES:
            if key == "cpu_utilisation":
                text = self._text(m[key], 0, "%")
            elif key == "throughput":
                text = self._text(m[key], 3)
            else:
                text = self._text(m[key])
            self.values[key].configure(text=text)

        killed = f"{m['killed']} killed, " if m["killed"] else ""
        self.progress.configure(text=f"Per-process results  ({m['finished']} of {m['processes']} finished, "
                                     f"{killed}time {m['total_time']})")
        self.tree.delete(*self.tree.get_children())
        for row in metrics.process_rows(sim):
            values = [self._text(row[key]) for key, _ in self.COLUMNS]
            if row["killed"]:
                values[0] += " (killed)"
            self.tree.insert("", "end", values=values)
        if m["finished"]:
            self.tree.insert("", "end", tags=("average",), values=(
                "Average", "", "", "", "", "", self._text(m["avg_turnaround"]),
                self._text(m["avg_waiting"]), self._text(m["avg_response"])))
