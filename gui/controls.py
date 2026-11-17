"""The control bar: scheduling settings on the left, simulation buttons on the right."""

import tkinter as tk
from tkinter import ttk

from gui import theme


class ControlBar(ttk.Frame):
    def __init__(self, parent, policy_names, on_start_pause, on_step, on_reset, on_settings_changed):
        super().__init__(parent, padding=(12, 10, 12, 6))
        self._on_settings_changed = on_settings_changed

        self.policy = tk.StringVar(value=policy_names[0])
        self.quantum = tk.StringVar(value="2")
        self.cs_cost = tk.StringVar(value="0")
        self.aging = tk.BooleanVar(value=False)
        self.speed = tk.DoubleVar(value=2.0)             # simulated ticks per second
        self._last = None                                # the settings we last reported

        # ---- settings: changing one of them restarts the simulation ----
        self._caption("Scheduling policy", 0)
        box = ttk.Combobox(self, textvariable=self.policy, values=policy_names, state="readonly", width=22)
        box.grid(row=1, column=0, padx=(0, 16), sticky="w")
        box.bind("<<ComboboxSelected>>", self._changed)

        self._caption("Quantum", 1)
        self.quantum_box = ttk.Spinbox(self, from_=1, to=20, textvariable=self.quantum, width=5,
                                       command=self._changed)
        self.quantum_box.grid(row=1, column=1, padx=(0, 16), sticky="w")

        self._caption("Switch cost", 2)
        self.cs_box = ttk.Spinbox(self, from_=0, to=5, textvariable=self.cs_cost, width=5,
                                  command=self._changed)
        self.cs_box.grid(row=1, column=2, padx=(0, 16), sticky="w")

        for spinbox in (self.quantum_box, self.cs_box):
            spinbox.bind("<Return>", self._changed)
            spinbox.bind("<FocusOut>", self._changed)

        self._caption("Starvation fix", 3)
        self.aging_box = ttk.Checkbutton(self, text="Aging", variable=self.aging, command=self._changed)
        self.aging_box.grid(row=1, column=3, padx=(0, 16), sticky="w")

        self.columnconfigure(4, weight=1)                # empty space between the two groups

        # ---- simulation buttons ----
        self.start_button = ttk.Button(self, text="Start", style="Accent.TButton", width=9, command=on_start_pause)
        self.start_button.grid(row=1, column=5, padx=4)
        self.step_button = ttk.Button(self, text="Step", width=7, command=on_step)
        self.step_button.grid(row=1, column=6, padx=4)
        ttk.Button(self, text="Reset", width=7, command=on_reset).grid(row=1, column=7, padx=(4, 18))

        self._caption("Speed", 8)
        ttk.Scale(self, from_=0.5, to=10, variable=self.speed, length=120).grid(row=1, column=8, padx=(0, 18))

        self._caption("Time", 9)
        self.clock = ttk.Label(self, text="0", style="Clock.TLabel", width=4)
        self.clock.grid(row=1, column=9, sticky="w")

        # ---- one line that explains the selected policy ----
        self.description = ttk.Label(self, style="Muted.TLabel", anchor="w", justify="left")
        self.description.grid(row=2, column=0, columnspan=10, sticky="ew", pady=(8, 0))
        self.bind("<Configure>", lambda event: self.description.configure(wraplength=max(200, event.width - 30)))

    def _caption(self, text, column):
        ttk.Label(self, text=text, style="Muted.TLabel").grid(row=0, column=column, sticky="w", pady=(0, 2))

    @staticmethod
    def _number(variable, default, low, high):
        """Read a whole number from an entry, keeping it inside [low, high]."""
        try:
            value = int(variable.get())
        except (ValueError, tk.TclError):
            value = default
        value = max(low, min(high, value))
        variable.set(str(value))
        return value

    def settings(self):
        return {
            "policy": self.policy.get(),
            "quantum": self._number(self.quantum, 2, 1, 20),
            "cs_cost": self._number(self.cs_cost, 0, 0, 5),
            "aging": self.aging.get(),
        }

    def _changed(self, _event=None):
        settings = self.settings()
        if settings != self._last:                       # ignore events that changed nothing
            self._last = settings
            self._on_settings_changed()

    def show_policy(self, policy):
        """Enable only the settings the policy really uses, and describe the policy."""
        self._last = self.settings()
        self.quantum_box.configure(state="normal" if policy.USES_QUANTUM else "disabled")
        self.aging_box.configure(state="normal" if policy.USES_PRIORITY else "disabled")
        kind = "preemptive" if policy.PREEMPTIVE else "non-preemptive"
        self.description.configure(text=f"{policy.DESCRIPTION}  [{kind}]")

    def show_state(self, time, running, finished):
        self.clock.configure(text=str(time))
        self.start_button.configure(text="Pause" if running else ("Restart" if finished else "Start"))
        self.step_button.configure(state="disabled" if finished else "normal")

    def delay_ms(self):
        """Milliseconds between two ticks when the simulation runs by itself."""
        return int(1000 / max(0.5, self.speed.get()))
