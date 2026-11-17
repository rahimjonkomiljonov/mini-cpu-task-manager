"""Mini CPU Task Manager - start the graphical interface with:  python main.py"""

import os
import sys

try:
    import tkinter  # noqa: F401  (only checking that it is installed)
except ImportError:
    sys.exit("tkinter is not installed.\n"
             "  Ubuntu / Debian:  sudo apt install python3-tk\n"
             "  Windows / macOS:  install Python from python.org (tkinter is included)\n"
             "You can still use the text version:  python cli.py")

from gui.app import App


def set_icon(window):
    """Show our icon in the title bar and the task bar. The program also works without it."""
    # In the built application (see build_app.py) the files are unpacked in the folder sys._MEIPASS.
    folder = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    try:
        window.icon = tkinter.PhotoImage(file=os.path.join(folder, "assets", "icon.png"))
        window.iconphoto(True, window.icon)
    except tkinter.TclError:
        pass


if __name__ == "__main__":
    app = App()
    set_icon(app)
    app.mainloop()
