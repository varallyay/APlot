"""The entry point of the self-contained APlot (a Python inside it).

PyInstaller turns this file into the application - APlot.app on a Mac,
APlot.exe on Windows, the program of the flatpak - with Python, Tk, numpy,
pandas, matplotlib and the rest inside it.  APlot itself stays the plain
aplot.py it always is, carried beside the libraries; this bootstrap runs it.

Updates of APlot come from GitHub as a new aplot.py.  They cannot go into
the application (on a Mac it is signed, on Windows it may lie where only an
administrator writes), so the updater writes the new aplot.py into a folder
of the user instead:

    macOS     ~/Library/Application Support/APlot/aplot.py
    Windows   %LOCALAPPDATA%\\APlot\\aplot.py
    Linux     $XDG_DATA_HOME/aplot/aplot.py (in a flatpak: its own folder)

and this bootstrap starts whichever of the two is newer - so installing a
newer package later is never held back by an older update.
"""
import os
import re
import runpy
import sys
from pathlib import Path

# PyInstaller collects what APlot imports by reading this import; it never
# runs (aplot.py is started from its file, below)
if os.environ.get("APLOT_NEVER_SET_ONLY_FOR_PYINSTALLER"):
    import aplot  # noqa: F401


def bundled_program():
    """The aplot.py that came with the application."""
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base / "aplot.py"


def updated_program():
    """Where an update of this application writes the new aplot.py."""
    if sys.platform == "darwin":
        home = Path.home() / "Library" / "Application Support" / "APlot"
    elif os.name == "nt":
        home = Path(os.environ.get("LOCALAPPDATA") or Path.home()) / "APlot"
    else:
        data = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
        home = Path(data) / "aplot"
    return home / "aplot.py"


def version_of(path):
    """The version written in an aplot.py, as numbers; () if unreadable."""
    try:
        with open(path, encoding="utf-8", errors="replace") as handle:
            head = handle.read(32768)
    except OSError:
        return ()
    found = re.search(r'^APP_VERSION = "([^"]*)"', head, re.M)
    try:
        return tuple(int(part) for part in found.group(1).split(".")) if found else ()
    except ValueError:
        return ()


def kind():
    """What kind of package this is, as APlot names it."""
    if sys.platform == "darwin":
        return "dmg"
    if os.name == "nt":
        return "msi"
    if os.environ.get("FLATPAK_ID") or os.path.exists("/.flatpak-info"):
        return "flatpak"
    return "frozen"


def main():
    bundled, updated = bundled_program(), updated_program()
    program = bundled
    if version_of(updated) > version_of(bundled):
        program = updated
    os.environ["APLOT_FROZEN"] = kind()
    os.environ["APLOT_UPDATE_TARGET"] = str(updated)
    # a restart after an update hands the program file on: it is not a graph
    sys.argv = [sys.argv[0]] + [one for one in sys.argv[1:]
                                if not one.endswith("aplot.py")]
    runpy.run_path(str(program), run_name="__main__")


if __name__ == "__main__":
    main()
