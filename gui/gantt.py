"""The live Gantt chart: who used the CPU during every tick."""

import tkinter as tk
from tkinter import ttk

from core.engine import IDLE, SWITCH
from gui import theme


class GanttChart(ttk.Frame):
    CELL = 30            # width of one tick, in pixels
    LEFT = 16            # empty space before time 0
    TOP = 10
    BAR = 36             # height of the bar

    def __init__(self, parent):
        super().__init__(parent)
        self.canvas = tk.Canvas(self, height=self.TOP + self.BAR + 30, background=theme.PANEL,
                                highlightthickness=1, highlightbackground=theme.LINE)
        scrollbar = ttk.Scrollbar(self, orient="horizontal", command=self.canvas.xview)
        self.canvas.configure(xscrollcommand=scrollbar.set)
        self.canvas.pack(fill="x")
        scrollbar.pack(fill="x")

    def show(self, sim, colors):
        canvas = self.canvas
        canvas.delete("all")
        top, bottom = self.TOP, self.TOP + self.BAR

        if not sim.gantt:
            canvas.create_text(self.LEFT, (top + bottom) / 2, anchor="w", fill=theme.MUTED,
                               text="Gantt chart: it grows here, one block per tick, when the simulation runs.")
            canvas.configure(scrollregion=(0, 0, 10, bottom + 30))
            return

        for label, start, end in sim.gantt_blocks():
            x1 = self.LEFT + start * self.CELL
            x2 = self.LEFT + end * self.CELL
            if label == IDLE:
                fill = theme.IDLE_COLOR
            elif label == SWITCH:
                fill = theme.SWITCH_COLOR
            else:
                fill = colors.get(label, theme.ACCENT)
            canvas.create_rectangle(x1, top, x2, bottom, fill=fill, outline=theme.PANEL, width=2)
            canvas.create_text((x1 + x2) / 2, (top + bottom) / 2, text=label, fill=theme.text_on(fill),
                               font=theme.FONTS["small_bold"] if label in (IDLE, SWITCH) else theme.FONTS["bold"])
            canvas.create_text(x1, bottom + 12, text=str(start), fill=theme.MUTED, font=theme.FONTS["small"])

        end_x = self.LEFT + len(sim.gantt) * self.CELL
        canvas.create_text(end_x, bottom + 12, text=str(len(sim.gantt)), fill=theme.TEXT, font=theme.FONTS["small_bold"])
        canvas.configure(scrollregion=(0, 0, end_x + 40, bottom + 30))
        canvas.xview_moveto(1.0)                         # keep the newest tick visible
