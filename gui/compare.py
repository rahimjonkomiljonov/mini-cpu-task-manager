"""The Compare tab: run every policy on the same workload and compare the metrics."""

import tkinter as tk
from tkinter import ttk

from core import metrics
from core.engine import Simulator
from gui import theme
from policies import ALL


class CompareTab(ttk.Frame):
    CHARTS = [                       # (metric key, chart title) - for all four, lower is better
        ("avg_waiting", "Average waiting time"),
        ("avg_turnaround", "Average turnaround time"),
        ("avg_response", "Average response time"),
        ("context_switches", "Context switches"),
    ]
    COLUMNS = [                      # (key, heading, width)
        ("policy", "Policy", 190), ("kind", "Type", 130), ("turnaround", "Avg turnaround", 120),
        ("waiting", "Avg waiting", 110), ("response", "Avg response", 110),
        ("switches", "Context switches", 130), ("util", "CPU utilisation", 120), ("time", "Total time", 90),
    ]

    def __init__(self, parent, get_workload, get_settings):
        super().__init__(parent, padding=14)
        self._get_workload = get_workload
        self._get_settings = get_settings
        self._rows = []              # [(policy module, summary dictionary), ...]

        top = ttk.Frame(self)
        top.pack(fill="x")
        ttk.Button(top, text="Run comparison", style="Accent.TButton", command=self.run).pack(side="left")
        self.info = ttk.Label(top, style="Muted.TLabel", justify="left",
                              text="Runs all policies on the current workload, with the current quantum, "
                                   "switch cost and aging settings.")
        self.info.pack(side="left", padx=12)

        self.tree = ttk.Treeview(self, columns=[key for key, _, _ in self.COLUMNS], show="headings",
                                 height=len(ALL))
        for key, heading, width in self.COLUMNS:
            self.tree.heading(key, text=heading)
            self.tree.column(key, width=width, anchor="w" if key in ("policy", "kind") else "center")
        self.tree.pack(fill="x", pady=(12, 10))

        self.canvas = tk.Canvas(self, height=250, background=theme.PANEL,
                                highlightthickness=1, highlightbackground=theme.LINE)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", lambda event: self._draw_charts())

        self.notes = ttk.Label(self, justify="left")
        self.notes.pack(anchor="w", pady=(10, 0))

    # ------------------------------------------------------------------ running

    def run(self):
        workload = self._get_workload()
        settings = self._get_settings()
        if not workload:
            self.info.configure(text="Add some processes first.")
            return
        self._rows = []
        for policy in ALL:
            sim = Simulator(workload, policy, settings["quantum"], settings["cs_cost"], settings["aging"])
            self._rows.append((policy, metrics.summary(sim.run_all())))

        self.info.configure(text=f"{len(workload)} processes, quantum {settings['quantum']}, "
                                 f"switch cost {settings['cs_cost']}, aging {'on' if settings['aging'] else 'off'}.")
        self.tree.delete(*self.tree.get_children())
        for policy, m in self._rows:
            self.tree.insert("", "end", values=(
                policy.NAME, "preemptive" if policy.PREEMPTIVE else "non-preemptive",
                f"{m['avg_turnaround']:.2f}", f"{m['avg_waiting']:.2f}", f"{m['avg_response']:.2f}",
                m["context_switches"], f"{m['cpu_utilisation']:.0f}%", m["total_time"]))
        self._draw_charts()
        self.notes.configure(text="\n".join(self._observations()))

    def clear(self):
        """Forget old results (called when the workload changes)."""
        self._rows = []
        self.tree.delete(*self.tree.get_children())
        self.notes.configure(text="")
        self._draw_charts()

    def _observations(self):
        """One sentence per metric: which policy (or policies) did best."""
        lines = []
        for key, title in self.CHARTS:
            best = min(m[key] for _policy, m in self._rows)
            winners = ", ".join(policy.NAME for policy, m in self._rows if m[key] == best)
            value = f"{best:.2f}" if isinstance(best, float) else str(best)
            lines.append(f"Lowest {title.lower()}:  {winners}  ({value})")
        return lines

    # ------------------------------------------------------------------ drawing

    def _draw_charts(self):
        canvas = self.canvas
        canvas.delete("all")
        width, height = canvas.winfo_width(), canvas.winfo_height()
        if not self._rows:
            canvas.create_text(width / 2, height / 2, fill=theme.MUTED,
                               text="Press \"Run comparison\" to see one bar chart per metric.")
            return
        gap = 14
        chart_width = (width - gap * (len(self.CHARTS) + 1)) / len(self.CHARTS)
        for i, (key, title) in enumerate(self.CHARTS):
            self._draw_chart(gap + i * (chart_width + gap), chart_width, height, key, title)

    def _draw_chart(self, x, width, height, key, title):
        canvas = self.canvas
        values = [m[key] for _policy, m in self._rows]
        highest = max(values) or 1
        best = min(values)
        base = height - 30                               # y of the bottom of the bars
        room = base - 58                                 # height of the tallest bar
        bar = (width - 16) / len(values)                 # space for one bar

        canvas.create_text(x + width / 2, 18, text=title, font=theme.FONTS["bold"], fill=theme.TEXT)
        canvas.create_line(x + 6, base, x + width - 6, base, fill=theme.LINE)
        for j, ((policy, _m), value) in enumerate(zip(self._rows, values)):
            left = x + 8 + j * bar
            top = base - room * value / highest
            canvas.create_rectangle(left + 4, top, left + bar - 4, base,
                                    fill=theme.PROCESS_COLORS[j], outline="")
            is_best = value == best
            canvas.create_text(left + bar / 2, top - 9,
                               text=f"{value:.2f}" if isinstance(value, float) else str(value),
                               font=theme.FONTS["small_bold"] if is_best else theme.FONTS["small"],
                               fill=theme.STATE_COLORS["RUNNING"] if is_best else theme.MUTED)
            canvas.create_text(left + bar / 2, base + 12, text=policy.SHORT,
                               font=theme.FONTS["small"], fill=theme.TEXT)
