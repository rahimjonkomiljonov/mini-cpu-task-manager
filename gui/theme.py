"""Colours, fonts and widget styles shared by the whole interface."""

import tkinter.font as tkfont
from tkinter import ttk

from core.pcb import NEW, READY, RUNNING, WAITING, SUSPENDED, TERMINATED

# ---- general colours ----
BG = "#EEF1F5"          # window background
PANEL = "#FFFFFF"       # background of panels and canvases
TEXT = "#1F2933"
MUTED = "#6B7785"
LINE = "#D3D9E0"
ACCENT = "#2563C9"

# ---- one colour per process state ----
STATE_COLORS = {
    NEW: "#7B8794",
    READY: "#2563C9",
    RUNNING: "#1B8E4B",
    WAITING: "#C77700",
    SUSPENDED: "#0E7C86",
    TERMINATED: "#6D4FC2",
}
MANAGE_COLOR = "#B4233C"   # something the user did to a live process (kill, suspend, ...)
STATE_TINTS = {            # light versions, used as row backgrounds in the PCB table
    NEW: "#FFFFFF",
    READY: "#E6EEFC",
    RUNNING: "#DDF3E4",
    WAITING: "#FCEFD6",
    SUSPENDED: "#DDF1F3",
    TERMINATED: "#EFEAF9",
}
STATE_HINTS = {
    NEW: "not arrived yet",
    READY: "queue, head on top",
    RUNNING: "on the CPU",
    WAITING: "doing I/O",
    SUSPENDED: "paused by the user",
    TERMINATED: "finished or killed",
}

# ---- one colour per process (the same in the state board and the Gantt chart) ----
PROCESS_COLORS = ["#4E79A7", "#F28E2B", "#59A14F", "#E15759", "#B07AA1", "#76B7B2",
                  "#EDC948", "#FF9DA7", "#9C755F", "#86BCB6", "#D37295", "#8CD17D"]
IDLE_COLOR = "#E1E5EA"
SWITCH_COLOR = "#39424E"

FONTS = {}              # filled by setup(): normal, bold, small, small_bold, title, mono


def text_on(color):
    """Black or white text, whichever is easier to read on the given background colour."""
    r, g, b = (int(color[i:i + 2], 16) for i in (1, 3, 5))
    return "#FFFFFF" if 0.299 * r + 0.587 * g + 0.114 * b < 150 else TEXT


def shade(color, factor=0.75):
    """A darker version of a colour (factor 1.0 = unchanged, 0.0 = black)."""
    r, g, b = (int(int(color[i:i + 2], 16) * factor) for i in (1, 3, 5))
    return f"#{r:02X}{g:02X}{b:02X}"


def process_colors(pids):
    """Give every PID its own colour."""
    return {pid: PROCESS_COLORS[i % len(PROCESS_COLORS)] for i, pid in enumerate(pids)}


def setup(root):
    """Create the fonts and configure the ttk styles. Call once, after creating the window."""
    family = tkfont.nametofont("TkDefaultFont").actual("family")
    FONTS["normal"] = tkfont.Font(family=family, size=10)
    FONTS["bold"] = tkfont.Font(family=family, size=10, weight="bold")
    FONTS["small"] = tkfont.Font(family=family, size=9)
    FONTS["small_bold"] = tkfont.Font(family=family, size=9, weight="bold")
    FONTS["title"] = tkfont.Font(family=family, size=12, weight="bold")
    FONTS["big"] = tkfont.Font(family=family, size=16, weight="bold")
    FONTS["mono"] = tkfont.Font(family=tkfont.nametofont("TkFixedFont").actual("family"), size=10)

    for name in ("TkDefaultFont", "TkTextFont", "TkMenuFont"):  # the fonts widgets use when no style sets one
        tkfont.nametofont(name).configure(size=10)
    root.configure(background=BG)

    style = ttk.Style(root)
    style.theme_use("clam")
    style.configure(".", background=BG, foreground=TEXT, font=FONTS["normal"])
    style.configure("TFrame", background=BG)
    style.configure("Panel.TFrame", background=PANEL)
    style.configure("TLabel", background=BG, foreground=TEXT)
    style.configure("Panel.TLabel", background=PANEL)
    style.configure("Muted.TLabel", foreground=MUTED, font=FONTS["small"])
    style.configure("PanelMuted.TLabel", background=PANEL, foreground=MUTED, font=FONTS["small"])
    style.configure("Title.TLabel", font=FONTS["title"])
    style.configure("Clock.TLabel", font=FONTS["big"], foreground=ACCENT)
    style.configure("TLabelframe", background=BG, bordercolor=LINE)
    style.configure("TLabelframe.Label", background=BG, foreground=TEXT, font=FONTS["bold"])
    style.configure("TButton", padding=(10, 5), background=PANEL, bordercolor=LINE, lightcolor=PANEL, darkcolor=PANEL)
    style.map("TButton", background=[("disabled", BG), ("pressed", "#D5DCE6"), ("active", "#E6EBF2")],
              foreground=[("disabled", "#A9B4C2")])
    style.configure("Small.TButton", padding=(8, 2), font=FONTS["small"])
    style.configure("Accent.TButton", background=ACCENT, foreground="#FFFFFF", font=FONTS["bold"], padding=(14, 5),
                    bordercolor=ACCENT, lightcolor=ACCENT, darkcolor=ACCENT)
    style.map("Accent.TButton",
              background=[("disabled", "#A9B4C2"), ("pressed", "#173F85"), ("active", "#1D4FA3")],
              foreground=[("disabled", "#FFFFFF")],
              bordercolor=[("disabled", "#A9B4C2")], lightcolor=[("disabled", "#A9B4C2")],
              darkcolor=[("disabled", "#A9B4C2")])
    style.configure("TCheckbutton", background=BG)
    style.map("TCheckbutton", background=[("active", BG)])
    style.configure("TNotebook", background=BG, bordercolor=LINE)
    style.configure("TNotebook.Tab", padding=(16, 6), font=FONTS["bold"], background="#DCE2EA", foreground=MUTED,
                    bordercolor=LINE, lightcolor="#DCE2EA")
    style.map("TNotebook.Tab", background=[("selected", BG)], foreground=[("selected", TEXT)],
              lightcolor=[("selected", BG)])
    for field in ("TEntry", "TCombobox", "TSpinbox"):
        style.configure(field, fieldbackground=PANEL, background=PANEL, bordercolor=LINE,
                        lightcolor=PANEL, darkcolor=PANEL, arrowcolor=TEXT)
    style.map("TCombobox", fieldbackground=[("readonly", PANEL)], background=[("readonly", PANEL)],
              selectbackground=[("readonly", PANEL)], selectforeground=[("readonly", TEXT)])
    style.map("TSpinbox", fieldbackground=[("disabled", BG)], foreground=[("disabled", "#A9B4C2")])
    style.configure("Horizontal.TScale", background=PANEL, troughcolor="#D5DCE6", bordercolor=LINE,
                    lightcolor=PANEL, darkcolor=PANEL)
    style.configure("TScrollbar", background="#D5DCE6", troughcolor=BG, bordercolor=LINE, arrowcolor=MUTED,
                    lightcolor="#D5DCE6", darkcolor="#D5DCE6")
    style.configure("Treeview", rowheight=24, fieldbackground=PANEL, background=PANEL, bordercolor=LINE)
    style.configure("Treeview.Heading", font=FONTS["small_bold"], padding=(2, 4), background="#E6EBF2", bordercolor=LINE)
    # Tk 8.6.9 ignores row tag colours in the clam theme unless these two entries are removed.
    for option in ("foreground", "background"):
        style.map("Treeview", **{option: [entry for entry in style.map("Treeview", query_opt=option)
                                          if entry[:2] != ("!disabled", "!selected")]})


def round_rect(canvas, x1, y1, x2, y2, radius=7, **options):
    """Draw a rectangle with rounded corners on a canvas."""
    r = max(0, min(radius, (x2 - x1) / 2, (y2 - y1) / 2))
    points = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
              x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
    return canvas.create_polygon(points, smooth=True, **options)
