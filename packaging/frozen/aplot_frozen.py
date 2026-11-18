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

On Windows the same folder is shipped two ways: inside the .msi, and as the
portable APlot-<version>-Windows-portable.zip, which is only unpacked and
started (no installation, no Python on the computer).  The portable folder
has the file PORTABLE beside APlot.exe; About APlot says so.

`APlot.exe --self-test REPORT [graph.aplt ...]` checks the built program
itself - every library loads, the windows open, a diagram is drawn, saved
and opened again - writes what it found into the text file REPORT and ends
with exit code 0 (all good) or 1.  build_frozen.py runs it after building.
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

PORTABLE_MARK = "PORTABLE"      # beside APlot.exe in the portable zip
SELF_TEST = "--self-test"


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


def is_portable():
    """True for the portable Windows folder (the file PORTABLE beside the
    program), which is unpacked and started instead of installed."""
    try:
        return (Path(sys.executable).resolve().parent / PORTABLE_MARK).is_file()
    except OSError:
        return False


def kind():
    """What kind of package this is, as APlot names it."""
    if sys.platform == "darwin":
        return "dmg"
    if os.name == "nt":
        return "portable" if is_portable() else "msi"
    if os.environ.get("FLATPAK_ID") or os.path.exists("/.flatpak-info"):
        return "flatpak"
    return "frozen"


def chosen_program():
    """The aplot.py to run: the newer of the bundled one and an update."""
    bundled, updated = bundled_program(), updated_program()
    return updated if version_of(updated) > version_of(bundled) else bundled


def self_test(report, graphs=()):
    """Check the built program and write the findings into `report`;
    0 when everything works, 1 when something does not."""
    import importlib.util
    import io
    import tempfile
    import time
    import traceback

    lines, failed = [], []
    folder = tempfile.mkdtemp(prefix="aplot-self-test-")

    def step(name, action):
        try:
            said = action()
        except BaseException as error:   # a SystemExit of aplot.py as well
            failed.append(name)
            lines.append(f"FAIL  {name}: {type(error).__name__}: {error}")
            lines.extend("      " + one for one in
                         traceback.format_exc().rstrip().splitlines())
            return None
        lines.append(f"ok    {name}" + (f": {said}" if said else ""))
        return said

    def python():
        return f"{sys.version.split()[0]} ({sys.executable}), package {kind()}"

    def libraries():
        import numpy, pandas, matplotlib, PIL  # noqa: E401
        from PIL import Image, ImageDraw, ImageTk  # noqa: F401
        return (f"numpy {numpy.__version__}, pandas {pandas.__version__}, "
                f"matplotlib {matplotlib.__version__}, pillow {PIL.__version__}")

    def excel():
        import openpyxl
        import pandas
        data = io.BytesIO()
        pandas.DataFrame({"x": [1.0, 2.0], "y": [3.0, 4.0]}).to_excel(data, index=False)
        data.seek(0)
        back = pandas.read_excel(data)
        assert back["y"].tolist() == [3.0, 4.0], back
        return f"openpyxl {openpyxl.__version__}: an .xlsx written and read"

    def tk_window():
        import tkinter
        root = tkinter.Tk()
        root.withdraw()
        root.update()
        said = f"Tk {root.call('info', 'patchlevel')}"
        try:
            import tkinterdnd2
        except ImportError:
            said += "; tkinterdnd2 is not in this build (no dropping of pictures)"
        else:
            tkinterdnd2.TkinterDnD._require(root)
            said += "; tkinterdnd2 (dropping pictures) loads"
        root.destroy()
        return said

    def load_aplot():
        program = chosen_program()
        spec = importlib.util.spec_from_file_location("aplot", program)
        module = importlib.util.module_from_spec(spec)
        sys.modules["aplot"] = module
        spec.loader.exec_module(module)
        for name in ("showinfo", "showwarning", "showerror"):
            setattr(module.messagebox, name, lambda *a, **k: None)
        module.messagebox.askyesno = lambda *a, **k: True
        module.messagebox.askyesnocancel = lambda *a, **k: False
        return module, f"APlot {module.APP_VERSION} from {program}"

    os.environ["APLOT_FROZEN"] = kind()
    os.environ["APLOT_UPDATE_TARGET"] = str(updated_program())
    step("Python", python)
    step("libraries", libraries)
    step("Excel files", excel)
    step("Tk window", tk_window)
    try:
        aplot, said = load_aplot()
        lines.append(f"ok    aplot.py: {said}")
    except BaseException as error:
        aplot = None
        failed.append("aplot.py")
        lines.append(f"FAIL  aplot.py: {type(error).__name__}: {error}")
        lines.extend("      " + one for one in
                     traceback.format_exc().rstrip().splitlines())

    if aplot is not None:
        import numpy as np
        import pandas as pd
        import tkinter
        state = {}

        def settle(times=6):
            for _ in range(times):
                state["root"].update()
                time.sleep(0.03)

        def start():
            state["root"] = tkinter.Tk()
            settings = aplot.Config(os.path.join(folder, "settings.json"))
            state["app"] = aplot.App(state["root"], settings)
            settle()
            return "the spreadsheet window is open"

        def line_plot():
            x = np.linspace(0.0, 10.0, 25)
            state["app"].table.set_dataframe(
                pd.DataFrame({"x": x, "sin": np.sin(x), "cos": np.cos(x)}),
                check_all=True)
            settle(2)
            plot = state["app"].open_plot("line_symbol")
            settle(8)
            suffixes = ("png", "jpg", "tif", "webp", "pdf", "svg", "svgz", "eps", "ps")
            for suffix in suffixes:      # what the Save dialog offers
                path = os.path.join(folder, f"diagram.{suffix}")
                plot.fig.savefig(path)
                assert os.path.getsize(path) > 0, path
            return "drawn, and saved as " + ", ".join("." + one for one in suffixes)

        def surface_plot():
            xs, ys = np.linspace(-3.0, 3.0, 13), np.linspace(-2.0, 2.0, 9)
            gx, gy = np.meshgrid(xs, ys, indexing="ij")
            state["app"].table.set_dataframe(pd.DataFrame({
                "x": gx.ravel(), "y": gy.ravel(),
                "z": np.exp(-(gx.ravel() ** 2 + gy.ravel() ** 2) / 2.0)}),
                check_all=True)
            settle(2)
            plot = state["app"].open_plot("surface3d")
            settle(8)
            assert plot.is_3d(), "not in 3D"
            return "drawn"

        def save_and_open():
            app = state["app"]
            path = os.path.join(folder, "self-test.aplt")
            assert app.save_project(path) == path, "not saved"
            for window in app.open_windows():
                window.destroy()
            settle(2)
            assert app.load_project(path) is True, "not opened again"
            settle(8)
            return f"{len(app.open_windows())} diagram(s) saved and opened again"

        def open_given():
            state["app"].open_documents(*graphs)
            settle(10)
            return f"{', '.join(graphs)} opened"

        if step("APlot window", start) is not None:
            step("line diagram", line_plot)
            step("3D surface", surface_plot)
            step("save and open a graph", save_and_open)
            if graphs:
                step("the graphs given", open_given)
            try:
                state["root"].destroy()
            except Exception:
                pass

    good = not failed
    text = (f"APlot self-test: {'ALL OK' if good else 'FAILED: ' + ', '.join(failed)}\n\n"
            + "\n".join(lines) + "\n")
    try:
        with open(report, "w", encoding="utf-8") as handle:
            handle.write(text)
    except OSError:
        pass
    if sys.stdout is not None:            # no console under --windowed
        try:
            print(text, end="")
        except Exception:
            pass
    return 0 if good else 1


def main():
    if len(sys.argv) > 2 and sys.argv[1] == SELF_TEST:
        sys.exit(self_test(sys.argv[2], [os.path.abspath(one) for one in sys.argv[3:]]))
    program = chosen_program()
    os.environ["APLOT_FROZEN"] = kind()
    os.environ["APLOT_UPDATE_TARGET"] = str(updated_program())
    # a restart after an update hands the program file on: it is not a graph
    sys.argv = [sys.argv[0]] + [one for one in sys.argv[1:]
                                if not one.endswith("aplot.py")]
    runpy.run_path(str(program), run_name="__main__")


if __name__ == "__main__":
    main()
