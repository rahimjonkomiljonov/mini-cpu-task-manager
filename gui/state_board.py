"""The state board: one column per process state.

Every process is a coloured card. When its state changes, the card moves to
another column, so the life of a process (NEW -> READY -> RUNNING -> ...) is visible.
"""

import tkinter as tk

from core.engine import IDLE, SWITCH, show_context
from core.pcb import NEW, READY, RUNNING, WAITING, SUSPENDED, TERMINATED, STATES
from gui import theme


class StateBoard(tk.Canvas):
    HEADER = 54          # height of a column header
    GAP = 10             # space between columns
    FRAMES = 8           # animation frames for one move
    FRAME_MS = 18        # milliseconds between two frames

    def __init__(self, parent):
        super().__init__(parent, height=220, background=theme.PANEL,
                         highlightthickness=1, highlightbackground=theme.LINE)
        self._sim = None
        self._colors = {}
        self._cards = {}         # pid -> {"now": box, "from": box, "to": box}; a box is [x, y, width, height]
        self._frame = 0
        self._job = None         # the scheduled animation call, if any
        self.bind("<Configure>", lambda event: self.show(self._sim, self._colors, animate=False))
        self.bind("<Destroy>", lambda event: self._cancel())

    def _cancel(self):
        """Stop the animation that is running, if any."""
        if self._job is not None:
            self.after_cancel(self._job)
            self._job = None

    # ------------------------------------------------------------------ public

    def show(self, sim, colors, animate=True):
        """Display the simulator's current situation (cards glide to their new places)."""
        self._sim, self._colors = sim, colors
        self._cancel()
        if sim is None or self.winfo_width() < 50:
            return

        targets = self._layout(sim)
        for pid in list(self._cards):
            if pid not in targets:
                del self._cards[pid]
        moving = False
        for pid, box in targets.items():
            card = self._cards.get(pid)
            if card is None or not animate:
                self._cards[pid] = {"now": list(box), "from": list(box), "to": list(box)}
            else:
                card["from"] = list(card["now"])
                card["to"] = list(box)
                moving = moving or card["from"] != card["to"]

        if moving:
            self._frame = 0
            self._animate()
        else:
            self._draw()

    # ------------------------------------------------------------------ layout

    def _group(self, sim, state):
        """The processes shown in one column, in display order."""
        if state == READY:
            return list(sim.ready)                              # the real order of the ready queue
        group = [p for p in sim.processes if p.state == state]
        if state == NEW:
            group.sort(key=lambda p: p.arrival)
        elif state == WAITING:
            group.sort(key=lambda p: p.io_left)
        elif state == TERMINATED:
            group.sort(key=lambda p: p.finish)
        return group

    def _columns(self):
        """(x, width) of every column."""
        width = (self.winfo_width() - self.GAP * (len(STATES) + 1)) / len(STATES)
        return [(self.GAP + i * (width + self.GAP), width) for i in range(len(STATES))]

    def _layout(self, sim):
        """Where should every card be? Returns pid -> (x, y, width, height)."""
        boxes = {}
        room = self.winfo_height() - self.HEADER - self.GAP
        for (x, width), state in zip(self._columns(), STATES):
            group = self._group(sim, state)
            row = max(18, min(42, room / max(len(group), 1)))    # cards shrink when a column is crowded
            for i, p in enumerate(group):
                boxes[p.pid] = (x + 8, self.HEADER + i * row, width - 16, row - 6)
        return boxes

    # ------------------------------------------------------------------ drawing

    def _animate(self):
        self._frame += 1
        k = self._frame / self.FRAMES
        k = 1 - (1 - k) ** 2                                     # ease out: quick start, soft landing
        for card in self._cards.values():
            card["now"] = [a + (b - a) * k for a, b in zip(card["from"], card["to"])]
        self._draw()
        self._job = self.after(self.FRAME_MS, self._animate) if self._frame < self.FRAMES else None

    def _draw(self):
        self.delete("all")
        sim = self._sim
        bottom = self.winfo_height() - 6
        for (x, width), state in zip(self._columns(), STATES):
            count = len(self._group(sim, state))
            color = theme.STATE_COLORS[state]
            theme.round_rect(self, x, 6, x + width, bottom, radius=10, fill="#F5F7FA", outline=theme.LINE)
            self.create_text(x + 12, 22, anchor="w", text=state, fill=color, font=theme.FONTS["bold"])
            self.create_text(x + width - 12, 22, anchor="e", text=str(count), fill=color, font=theme.FONTS["bold"])
            self.create_text(x + 12, 39, anchor="w", text=theme.STATE_HINTS[state],
                             fill=theme.MUTED, font=theme.FONTS["small"])
            if state == RUNNING and count == 0:
                self._draw_cpu_note(x, width)
            elif state == RUNNING:                               # the registers of the simulated CPU
                self._draw_note(x, width, self.HEADER + 46, "CPU registers", [show_context(sim.cpu)],
                                theme.STATE_COLORS[RUNNING])

        # Draw the cards that are moving last, so they pass over the others.
        still = [p for p in sim.processes if self._cards[p.pid]["from"] == self._cards[p.pid]["to"]]
        moving = [p for p in sim.processes if p not in still]
        for p in still + moving:
            self._draw_card(p)

    def _draw_card(self, p):
        x, y, w, h = self._cards[p.pid]["now"]
        color = self._colors.get(p.pid, theme.ACCENT)
        ink = theme.text_on(color)
        theme.round_rect(self, x, y, x + w, y + h, radius=7, fill=color, outline="")
        middle = y + h / 2 - (3 if h >= 30 else 0)
        self.create_text(x + 10, middle, anchor="w", text=p.pid, fill=ink, font=theme.FONTS["bold"])
        self.create_text(x + w - 10, middle, anchor="e", text=self._detail(p), fill=ink, font=theme.FONTS["small"])
        if h >= 30:                                              # progress bar: how much of the burst is done
            y_bar = y + h - 6
            self.create_line(x + 9, y_bar, x + w - 9, y_bar, fill=theme.shade(color), width=3)
            if p.pc:
                self.create_line(x + 9, y_bar, x + 9 + (w - 18) * p.pc / p.burst, y_bar, fill=ink, width=3)

    def _detail(self, p):
        """The small text on the right side of a card."""
        if p.state == NEW:
            return f"arrives at {p.arrival}"
        if p.state == READY:
            if getattr(self._sim.policy, "USES_PRIORITY", False):
                return f"prio {p.eff_priority}, left {p.remaining}"
            return f"left {p.remaining}"
        if p.state == RUNNING:
            return f"{p.pc}/{p.burst} done"
        if p.state == WAITING:
            return f"I/O: {p.io_left} left"
        if p.state == SUSPENDED:
            return f"left {p.remaining}"
        return f"killed at {p.finish}" if p.killed else f"done at {p.finish}"

    def _draw_cpu_note(self, x, width):
        """What the CPU is doing when no process is RUNNING."""
        sim = self._sim
        if sim.finished:
            title, lines, color = "all done", ["every process terminated"], theme.MUTED
        elif sim.time == 0:
            title, lines, color = "not started", ["press Start or Step"], theme.MUTED
        elif sim.gantt[-1] == SWITCH:
            # The two halves of a context switch: the old registers go into a PCB, the new ones come out of one.
            title, lines, color = "context switch", [], theme.SWITCH_COLOR
            if sim.last_saved:
                pid, context = sim.last_saved
                lines += [f"saved from {pid}:", show_context(context)]
            if sim.switch_target:
                lines += [f"loading for {sim.switch_target.pid}:", show_context(sim.switch_target.context)]
        elif sim.stalled:
            title, lines, color = "CPU idle", ["everybody is suspended"], theme.MUTED
        elif sim.gantt[-1] == IDLE:
            title, lines, color = "CPU idle", ["nobody was ready"], theme.MUTED
        else:                                                    # the last process has just left the CPU
            title, lines, color = "CPU is free", ["the scheduler picks next"], theme.STATE_COLORS[RUNNING]
        self._draw_note(x, width, self.HEADER, title, lines, color)

    def _draw_note(self, x, width, y, title, lines, color):
        """A dashed box with a title and some small lines of text."""
        height = 27 + 15 * len(lines)
        theme.round_rect(self, x + 8, y, x + width - 8, y + height, radius=7, fill=theme.PANEL, outline=color,
                         dash=(4, 3))
        self.create_text(x + width / 2, y + 14, text=title, fill=color, font=theme.FONTS["bold"])
        for i, line in enumerate(lines):
            self.create_text(x + width / 2, y + 31 + 15 * i, text=line, fill=theme.MUTED, font=theme.FONTS["small"])
