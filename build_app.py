"""Build the program as a double-click application. No Python is needed to run the result.

    python build_app.py            (on macOS: python3 build_app.py)

Run it on the system you want the application for:

    Windows  ->  dist/Mini CPU Task Manager.exe         (one file)
    macOS    ->  dist/Mini CPU Task Manager.app         (and a .zip of it, for sending)

The tool that does the work is PyInstaller. It cannot build a Mac application on Windows
or a Windows application on a Mac, so each one must be built on its own system
(or by GitHub: see .github/workflows/build.yml).
"""

import os
import shutil
import subprocess
import sys

NAME = "Mini CPU Task Manager"
HERE = os.path.dirname(os.path.abspath(__file__))
MAC = sys.platform == "darwin"


def main():
    try:
        import PyInstaller  # noqa: F401  (only checking that it is installed)
    except ImportError:
        sys.exit("PyInstaller is not installed. Install it with:\n    "
                 + os.path.basename(sys.executable) + " -m pip install pyinstaller")

    try:
        import tkinter  # noqa: F401  (without it the application would close as soon as it starts)
    except ImportError:
        sys.exit("This Python has no tkinter, so the application cannot be built with it.\n"
                 "Install Python from python.org (tkinter is included) and run this script with that Python.")

    icon = os.path.join(HERE, "assets", "icon.icns" if MAC else "icon.ico")
    picture = os.path.join(HERE, "assets", "icon.png")       # the window icon, packed inside the application
    command = [
        sys.executable, "-m", "PyInstaller", os.path.join(HERE, "main.py"),
        "--name", NAME,
        "--windowed",                                        # no black console window
        "--noconfirm", "--clean",
        "--icon", icon,
        "--add-data", picture + os.pathsep + "assets",
        "--distpath", os.path.join(HERE, "dist"),
        "--workpath", os.path.join(HERE, "build"),
        "--specpath", os.path.join(HERE, "build"),
    ]
    if not MAC:
        command.append("--onefile")                          # Windows: a single .exe (a Mac .app is a folder anyway)
    subprocess.run(command, check=True, cwd=HERE)

    if MAC:
        app = os.path.join(HERE, "dist", NAME + ".app")
        # ditto keeps the application intact inside the zip (the usual way to send a Mac application)
        subprocess.run(["ditto", "-c", "-k", "--keepParent", app, app + ".zip"], check=True)
        shutil.rmtree(os.path.join(HERE, "dist", NAME), ignore_errors=True)     # an extra folder nobody needs
        print("\nBuilt:", app, "\nTo send it to somebody:", app + ".zip")
    else:
        print("\nBuilt:", os.path.join(HERE, "dist", NAME + ".exe"))


if __name__ == "__main__":
    main()
