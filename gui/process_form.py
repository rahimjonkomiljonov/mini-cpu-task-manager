"""The workload panel: create processes by hand, or load a ready-made workload."""

import tkinter as tk
from tkinter import messagebox, ttk

from core.pcb import PCB


class ProcessForm(ttk.LabelFrame):
    FIELDS = [                       # (key, label, default value)
        ("pid", "PID", "P1"),
        ("arrival", "Arrival time", "0"),
        ("burst", "Burst time", "5"),
        ("priority", "Priority", "1"),
        ("io_at", "I/O after (CPU units)", ""),
        ("io_time", "I/O duration", ""),
    ]

    def __init__(self, parent, sample_names, on_add, on_remove, on_clear, on_load_sample, on_random):
        super().__init__(parent, text="Workload", padding=10)
        self._on_add = on_add
        self.vars = {}

        for row, (key, label, default) in enumerate(self.FIELDS):
            ttk.Label(self, text=label).grid(row=row, column=0, sticky="w", pady=3)
            self.vars[key] = tk.StringVar(value=default)
            entry = ttk.Entry(self, textvariable=self.vars[key], width=9)
            entry.grid(row=row, column=1, sticky="e", pady=3, padx=(8, 0))
            entry.bind("<Return>", lambda event: self._add())

        row = len(self.FIELDS)
        ttk.Label(self, style="Muted.TLabel", justify="left", wraplength=235,
                  text="Priority: a lower number is more important. "
                       "Leave the two I/O fields empty for a process that only uses the CPU. "
                       "While the simulation runs, Add process creates the process live."
                  ).grid(row=row, column=0, columnspan=2, sticky="w", pady=(6, 8))

        ttk.Button(self, text="Add process", style="Accent.TButton", command=self._add
                   ).grid(row=row + 1, column=0, columnspan=2, sticky="ew", pady=2)
        pair = ttk.Frame(self)                                   # two buttons side by side
        pair.grid(row=row + 2, column=0, columnspan=2, sticky="ew", pady=2)
        ttk.Button(pair, text="Remove selected", command=on_remove).pack(side="left", fill="x", expand=True)
        ttk.Button(pair, text="Clear all", command=on_clear).pack(side="left", fill="x", expand=True, padx=(4, 0))

        ttk.Separator(self).grid(row=row + 3, column=0, columnspan=2, sticky="ew", pady=10)

        ttk.Label(self, text="Sample workloads").grid(row=row + 4, column=0, columnspan=2, sticky="w")
        self.sample = tk.StringVar(value=sample_names[0])
        ttk.Combobox(self, textvariable=self.sample, values=sample_names, state="readonly", width=24
                     ).grid(row=row + 5, column=0, columnspan=2, sticky="ew", pady=(3, 4))
        pair = ttk.Frame(self)
        pair.grid(row=row + 6, column=0, columnspan=2, sticky="ew", pady=2)
        ttk.Button(pair, text="Load sample", command=lambda: on_load_sample(self.sample.get())
                   ).pack(side="left", fill="x", expand=True)
        ttk.Button(pair, text="Random", command=on_random).pack(side="left", fill="x", expand=True, padx=(4, 0))

        self.columnconfigure(0, weight=1)

    def _add(self):
        """Read the fields, build a PCB and hand it to the application."""
        values = {key: variable.get().strip() for key, variable in self.vars.items()}
        try:
            process = PCB(values["pid"], int(values["arrival"]), int(values["burst"]), int(values["priority"]),
                          int(values["io_at"]) if values["io_at"] else None,     # empty = no I/O; "0" is refused
                          int(values["io_time"]) if values["io_time"] else 0)
        except ValueError as error:
            message = str(error)
            if "invalid literal" in message:
                message = "Arrival, burst, priority and the I/O fields must be whole numbers."
            messagebox.showerror("Cannot add the process", message, parent=self)
            return
        self._on_add(process)

    def suggest_pid(self, pid):
        """Prepare the form for the next process."""
        self.vars["pid"].set(pid)
