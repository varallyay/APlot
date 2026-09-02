#!/usr/bin/env python3
"""
APlot - Data Visualizer
=======================

A Tkinter application to edit tabular data and plot it interactively with
Matplotlib.

Spreadsheet window
------------------
* toolbar: Plot / Update plot / Add row / Delete row / Add column /
  Delete column / Random data / Settings
* "Plot" opens a new diagram, "Update plot" sends the edited values to the
  diagrams that are already open without changing any of their styling
* "Random data" fills the table in its present shape, extra columns included
* click a cell to edit it; Enter, Tab, Shift+Tab, Up and Down move around,
  Left/Right move the text cursor, Esc cancels
* moving below the last row appends a new row automatically, so the table
  grows as long as you keep typing
* cell text can be selected with the mouse, with Shift+arrows or Ctrl/Cmd+A
  and copied with Ctrl/Cmd+C; Ctrl/Cmd+C on a selected row copies the row
* click a column heading to rename it; the name is the legend text of that
  curve and, for the first column, the label of the X axis

Files
-----
* csv / txt / dat / tsv text data files with any separator (tabulator,
  semicolon, comma, spaces) and both decimal signs - recognised
  automatically
* .aplt (JSON) for the data together with every property of every open
  diagram - File > Save graph / Open graph
* Help > Documentation shows README.md (the same text is in this file)

Plot window
-----------
* click a curve            -> line, marker and fill properties separately
                              (marker "None" available), legend follows
* click an axis label/title -> its text, font size and font colour
* every curve has its own legend box: drag its frame to move it, click its
  text to change the text and the font size of that box
* double-click an axis      -> combined axes dialog (X / Y / Frame tabs) with
                              range, step, minor ticks, grid, font sizes,
                              frame style and the size/origin of the axes
* click the frame           -> the "Frame and origin" tab of that dialog
* Plot menu                 -> axes dialog, title and font sizes, legend

Settings
--------
The "APlot" menu (and the application menu on macOS) has a Settings dialog
that edits every default of the program.  The values are stored in
~/.aplot/config.json and are read again on the next start.

Module layout
-------------
Config / SETTINGS_SPEC   persistent defaults and their description
ColorSwatch, ToolDialog  reusable widgets
SettingsDialog           editor of the configuration file
SeriesStyleDialog        line + marker properties, legend label
AxisTab / AxesDialog     both axes in one window with two tabs
TitleFontDialog          title text, title / legend font size
DataTable                spreadsheet-like Treeview with in-place editing
PlotWindow               the interactive figure window
App                      main window, menus, file I/O
"""

from __future__ import annotations

import copy
import json
import re
import sys
import tkinter as tk
from pathlib import Path
from tkinter import ttk, filedialog, colorchooser, messagebox, simpledialog

import numpy as np
import pandas as pd

import matplotlib
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.colors import to_hex, to_rgba
from matplotlib.figure import Figure
from matplotlib.legend import Legend
from matplotlib.lines import Line2D
from matplotlib.ticker import (AutoLocator, AutoMinorLocator, FixedLocator,
                               MultipleLocator, NullLocator)

APP_NAME = "APlot"
PROJECT_SUFFIX = ".aplt"
CONFIG_FILE = Path.home() / ".aplot" / "config.json"

# --------------------------------------------------------------------------
# option tables
# --------------------------------------------------------------------------

MARKERS = [
    ("None", "None"), ("Point", "."), ("Circle", "o"), ("Square", "s"),
    ("Triangle up", "^"), ("Triangle down", "v"), ("Diamond", "D"),
    ("Thin diamond", "d"), ("Plus", "+"), ("X", "x"), ("Star", "*"),
    ("Pentagon", "p"), ("Hexagon", "h"),
]

LINE_STYLES = [
    ("Solid", "-"), ("Dashed", "--"), ("Dash-dot", "-."), ("Dotted", ":"),
    ("None", "None"),
]

GRID_STYLES = [("Solid", "-"), ("Dashed", "--"), ("Dash-dot", "-."), ("Dotted", ":")]

HATCH_PATTERNS = [
    ("None (plain colour)", ""), ("Diagonal /", "/"), ("Back diagonal \\", "\\"),
    ("Vertical |", "|"), ("Horizontal -", "-"), ("Crossed +", "+"),
    ("Diagonal cross x", "x"), ("Small circles o", "o"),
    ("Large circles O", "O"), ("Dots .", "."), ("Stars *", "*"),
    ("Dense diagonal //", "//"), ("Dense back diagonal \\\\", "\\\\"),
    ("Dense vertical ||", "||"), ("Dense horizontal --", "--"),
]

FILL_BASES = [("Zero line", "zero"), ("Bottom of the axes", "bottom")]

FRAME_STYLES = [
    ("No frame (X and Y only) (default)", "none"),
    ("Full frame", "box"),
    ("Frame with ticks (inward)", "box_in"),
    ("Frame with ticks (outward)", "box_out"),
]

# matplotlib's own subplot position: left, bottom, width, height
DEFAULT_POSITION = (0.125, 0.11, 0.775, 0.77)
SIZE_UNITS = ["Fraction of window", "cm", "inch"]

LEGEND_LOCATIONS = ["best", "upper right", "upper left", "lower left",
                    "lower right", "right", "center left", "center right",
                    "lower center", "upper center", "center"]

# where the first legend box is placed (axes coordinates) and which of its
# corners sits on that point; the further boxes are stacked from there
LEGEND_ANCHORS = {
    "best": (0.98, 0.98, "upper right"),
    "upper right": (0.98, 0.98, "upper right"),
    "upper left": (0.02, 0.98, "upper left"),
    "lower left": (0.02, 0.02, "lower left"),
    "lower right": (0.98, 0.02, "lower right"),
    "right": (0.98, 0.50, "center right"),
    "center left": (0.02, 0.50, "center left"),
    "center right": (0.98, 0.50, "center right"),
    "lower center": (0.50, 0.02, "lower center"),
    "upper center": (0.50, 0.98, "upper center"),
    "center": (0.50, 0.50, "center"),
}
LEGEND_STACK_STEP = 0.085

PALETTE_FALLBACK = "#1f77b4"


def names(table):
    """Human readable names of a (name, code) table."""
    return [name for name, _ in table]


def code_of(table, name, default):
    """Matplotlib code belonging to a human readable name."""
    for label, code in table:
        if label == name:
            return code
    return default


def name_of(table, code, default):
    """Human readable name belonging to a matplotlib code."""
    if code is None:
        code = "None"
    for label, value in table:
        if value == code:
            return label
    return default


def safe_hex(color, fallback=PALETTE_FALLBACK):
    """to_hex() that never raises (e.g. for the special value 'none')."""
    try:
        return to_hex(color)
    except (ValueError, TypeError):
        return fallback


def store_color(color):
    """Colour in a form that survives a save/load cycle ('none' included)."""
    if isinstance(color, str) and color.lower() == "none":
        return "none"
    return safe_hex(color)


def json_default(value):
    """Make numpy scalars written by pandas JSON serialisable."""
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return float(value)
    if isinstance(value, np.ndarray):
        return value.tolist()
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return ""
    return str(value)


def coerce(text):
    """Convert a cell string to int / float when it looks numeric."""
    s = str(text).strip()
    if s == "":
        return ""
    try:
        return int(s)
    except ValueError:
        pass
    try:
        return float(s)
    except ValueError:
        return text


def to_float(text, default=None):
    try:
        return float(str(text).strip().replace(",", "."))
    except (ValueError, AttributeError, TypeError):
        return default


def to_int(text, default=0):
    value = to_float(text, None)
    return default if value is None else int(round(value))


# --------------------------------------------------------------------------
# reading data files (csv / txt / dat with any separator)
# --------------------------------------------------------------------------

WHITESPACE_SEP = r"\s+"
COMMENT_MARKERS = ("#", "%", "!", "//")
DATA_PATTERNS = [("Data files", "*.csv *.txt *.dat *.tsv *.asc"),
                 ("CSV files", "*.csv"), ("Text files", "*.txt"),
                 ("Data files", "*.dat"), ("All files", "*.*")]

# what the "separator" setting may contain
SEPARATOR_WORDS = {
    "auto": None, "": None,
    ",": ",", "comma": ",",
    ";": ";", "semicolon": ";",
    "\t": "\t", "\\t": "\t", "tab": "\t",
    " ": WHITESPACE_SEP, "space": WHITESPACE_SEP, "whitespace": WHITESPACE_SEP,
    "|": "|", "pipe": "|",
}
SEPARATOR_LABELS = {",": "comma", ";": "semicolon", "\t": "tab",
                    WHITESPACE_SEP: "space", "|": "pipe"}


def separator_from_setting(value):
    """The separator a setting asks for, or None for automatic detection."""
    key = str(value if value is not None else "").strip().lower()
    if key in SEPARATOR_WORDS:
        return SEPARATOR_WORDS[key]
    return str(value)[0] if str(value) else None


def split_fields(line, separator):
    return line.split() if separator == WHITESPACE_SEP else line.split(separator)


def looks_numeric(field, decimal="."):
    text = str(field).strip().replace(" ", "")
    if decimal == ",":
        text = text.replace(".", "").replace(",", ".")
    if text == "" or text.lower() in ("nan", "inf", "-inf"):
        return True
    try:
        float(text)
        return True
    except ValueError:
        return False


def read_sample(path, limit=60):
    """Leading lines of a file: (data lines, lines to skip, encoding, comment)."""
    for encoding in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            with open(path, "r", encoding=encoding) as handle:
                lines, skip, marker, counting = [], 0, None, True
                for raw in handle:
                    text = raw.strip()
                    is_comment = text.startswith(COMMENT_MARKERS)
                    if not text or is_comment:
                        if counting:
                            skip += 1
                        if is_comment and marker is None:
                            marker = text[:2] if text.startswith("//") else text[0]
                        continue
                    counting = False
                    lines.append(text)
                    if len(lines) >= limit:
                        break
                return lines, skip, encoding, marker
        except (UnicodeDecodeError, UnicodeError):
            continue
    return [], 0, "latin-1", None


def _first_consistent(lines, order, agreement=0.6):
    """First separator of `order` that gives the same field count everywhere."""
    for separator in order:
        counts = [len(split_fields(line, separator)) for line in lines]
        if not counts:
            continue
        modal = max(set(counts), key=counts.count)
        if modal >= 2 and counts.count(modal) >= agreement * len(counts):
            return separator
    return None


def detect_dialect(lines):
    """Guess the separator and the decimal sign from a few data lines."""
    text = "\n".join(lines)
    # "1,5" style numbers with no dotted numbers anywhere: decimal comma
    comma_decimal = (bool(re.search(r"\d,\d", text))
                     and not re.search(r"\d\.\d", text))
    order = ["\t", ";", "|", ",", WHITESPACE_SEP]
    separator = _first_consistent(
        lines, [s for s in order if not (comma_decimal and s == ",")])
    if separator is None:                 # comma after all (e.g. "1,2,3")
        separator = _first_consistent(lines, order)
        comma_decimal = comma_decimal and separator != ","
    if separator is None:                 # a single column
        separator, comma_decimal = ",", False
    return separator, ("," if comma_decimal and separator != "," else ".")


def read_table(path, separator="auto", decimal="auto"):
    """Read a csv/txt/dat file into a DataFrame; returns (frame, info)."""
    lines, skip, encoding, marker = read_sample(path)
    if not lines:
        raise ValueError("the file contains no data")

    chosen = separator_from_setting(separator)
    wanted = str(decimal if decimal is not None else "").strip().lower()
    dec = None if wanted in ("auto", "") else wanted[0]
    if chosen is None or dec is None:
        auto_separator, auto_decimal = detect_dialect(lines)
        chosen = chosen if chosen is not None else auto_separator
        dec = dec if dec is not None else auto_decimal

    fields = split_fields(lines[0], chosen)
    has_header = not all(looks_numeric(field, dec) for field in fields)

    options = {"sep": chosen, "decimal": dec, "encoding": encoding,
               "skiprows": skip, "skip_blank_lines": True,
               "header": 0 if has_header else None}
    if chosen == WHITESPACE_SEP:
        options["engine"] = "python"
    if marker and len(marker) == 1 and marker != chosen:
        options["comment"] = marker

    try:
        frame = pd.read_csv(path, **options)
        skipped = False
    except Exception:                       # ragged lines: keep the good ones
        frame = pd.read_csv(path, on_bad_lines="skip", engine="python",
                            **{k: v for k, v in options.items() if k != "engine"})
        skipped = True

    frame = frame.dropna(axis="columns", how="all")    # trailing separators
    if not has_header:
        frame.columns = (["X"] + [f"Y{i}" for i in range(1, len(frame.columns))])
    else:
        frame.columns = [str(name).strip() for name in frame.columns]

    info = {"separator": SEPARATOR_LABELS.get(chosen, chosen), "decimal": dec,
            "header": has_header, "skipped_lines": skip, "bad_lines": skipped,
            "rows": len(frame), "columns": len(frame.columns)}
    return frame, info


# --------------------------------------------------------------------------
# persistent configuration
# --------------------------------------------------------------------------

DEFAULTS = {
    "window": {
        "main_width": 950, "main_height": 400,
        "plot_width": 960, "plot_height": 720,
    },
    "table": {
        "rows": 12,
        "columns": "X,Y1,Y2,Y3",
        "column_width": 110,
        "font_size": 10,
        "auto_extend": True,
    },
    "plot": {
        "fig_width": 6.5, "fig_height": 4.8, "dpi": 100,
        "title_template": "Data visualization as a function of {x}",
        "y_label": "Y values",
        "line_style": "Dashed", "line_width": 1.5,
        "marker": "Circle", "marker_size": 8.0,
        "marker_edge_width": 1.0, "hollow_markers": False,
        "legend_visible": True, "legend_location": "best",
        "legend_frame": False, "legend_edge_color": "#000000",
        "legend_background": "#ffffff", "legend_transparent": True,
        "fill_under": False, "fill_color": "#1f77b4", "fill_alpha": 0.35,
        "fill_pattern": "None (plain colour)", "fill_base": "Zero line",
        "fill_follows_line": True,
    },
    "fonts": {
        "title": 18, "axis_label": 18, "tick_label": 16, "legend": 14,
        "title_color": "#000000", "axis_label_color": "#000000",
        "tick_label_color": "#000000", "legend_color": "#000000",
    },
    "grid": {
        "major": False, "minor": False, "color": "#b0b0b0",
        "style": "Dotted", "width": 0.8, "minor_ticks": 1,
    },
    "frame": {
        "style": "No frame (X and Y only) (default)", "width": 1.8,
        "color": "#000000",
        "major_tick_length": 8.0, "minor_tick_length": 4.0,
        "background": "#ffffff", "transparent_background": True,
        "figure_background": "#ffffff",
        "left": DEFAULT_POSITION[0], "bottom": DEFAULT_POSITION[1],
        "x_length": DEFAULT_POSITION[2], "y_length": DEFAULT_POSITION[3],
    },
    "csv": {
        "separator": "auto", "decimal": "auto",
    },
}

# (key, label, kind, extra) - kind: int / float / bool / text / choice / color
SETTINGS_SPEC = [
    ("window", "Windows", [
        ("main_width", "Main window width [px]", "int"),
        ("main_height", "Main window height [px]", "int"),
        ("plot_width", "Plot window width [px]", "int"),
        ("plot_height", "Plot window height [px]", "int"),
    ]),
    ("table", "Spreadsheet", [
        ("rows", "Number of rows at start", "int"),
        ("columns", "Column names at start (comma separated)", "text"),
        ("column_width", "Column width [px]", "int"),
        ("font_size", "Font size", "int"),
        ("auto_extend", "Add a new row when leaving the last one", "bool"),
    ]),
    ("plot", "Plot", [
        ("fig_width", "Figure width [inch]", "float"),
        ("fig_height", "Figure height [inch]", "float"),
        ("dpi", "Resolution [dpi]", "int"),
        ("title_template", "Title ({x} = name of the X column)", "text"),
        ("y_label", "Default Y axis label", "text"),
        ("line_style", "Line style", "choice", names(LINE_STYLES)),
        ("line_width", "Line width", "float"),
        ("marker", "Marker", "choice", names(MARKERS)),
        ("marker_size", "Marker size", "float"),
        ("marker_edge_width", "Marker edge width", "float"),
        ("hollow_markers", "Hollow markers (no fill)", "bool"),
        ("legend_visible", "Show legend", "bool"),
        ("legend_location", "Legend position", "choice", LEGEND_LOCATIONS),
        ("legend_frame", "Legend box frame", "bool"),
        ("legend_edge_color", "Legend frame colour", "color"),
        ("legend_background", "Legend background", "color"),
        ("legend_transparent", "Transparent legend background", "bool"),
        ("fill_under", "Fill under the curves", "bool"),
        ("fill_follows_line", "Fill colour follows the curve", "bool"),
        ("fill_color", "Fill colour (when it does not)", "color"),
        ("fill_alpha", "Fill opacity (0-1)", "float"),
        ("fill_pattern", "Fill pattern", "choice", names(HATCH_PATTERNS)),
        ("fill_base", "Fill down to", "choice", names(FILL_BASES)),
    ]),
    ("fonts", "Fonts", [
        ("title", "Plot title size", "int"),
        ("title_color", "Plot title colour", "color"),
        ("axis_label", "Axis label size", "int"),
        ("axis_label_color", "Axis label colour", "color"),
        ("tick_label", "Axis numbers (ticks) size", "int"),
        ("tick_label_color", "Axis numbers (ticks) colour", "color"),
        ("legend", "Legend size", "int"),
        ("legend_color", "Legend colour", "color"),
    ]),
    ("grid", "Grid", [
        ("major", "Major grid lines", "bool"),
        ("minor", "Minor grid lines", "bool"),
        ("color", "Grid colour", "color"),
        ("style", "Grid style", "choice", names(GRID_STYLES)),
        ("width", "Grid width", "float"),
        ("minor_ticks", "Minor ticks between majors", "int"),
    ]),
    ("frame", "Frame", [
        ("style", "Frame style", "choice", names(FRAME_STYLES)),
        ("width", "Frame thickness", "float"),
        ("color", "Frame colour", "color"),
        ("major_tick_length", "Major tick length", "float"),
        ("minor_tick_length", "Minor tick length", "float"),
        ("background", "Plot area background", "color"),
        ("transparent_background", "Transparent plot area", "bool"),
        ("figure_background", "Window background", "color"),
        ("x_length", "X axis length (fraction of window)", "float"),
        ("y_length", "Y axis length (fraction of window)", "float"),
        ("left", "Y axis distance from the left", "float"),
        ("bottom", "X axis distance from the bottom", "float"),
    ]),
    ("csv", "Data files", [
        ("separator", "Field separator (auto, comma, semicolon, tab, space)", "text"),
        ("decimal", "Decimal sign (auto, . or ,)", "text"),
    ]),
]


class Config:
    """Defaults of the program, stored as JSON in the user's home folder."""

    def __init__(self, path=CONFIG_FILE):
        self.path = Path(path)
        self.data = copy.deepcopy(DEFAULTS)
        self.load()

    def load(self):
        try:
            with open(self.path, "r", encoding="utf-8") as handle:
                stored = json.load(handle)
        except (OSError, ValueError):
            return False
        for section, values in (stored or {}).items():
            if section in self.data and isinstance(values, dict):
                for key, value in values.items():
                    if key in self.data[section]:
                        self.data[section][key] = value
        return True

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as handle:
            json.dump(self.data, handle, indent=2, sort_keys=True)

    def reset(self):
        self.data = copy.deepcopy(DEFAULTS)

    def get(self, section, key):
        return self.data[section][key]

    def section(self, name):
        return dict(self.data[name])

    def set(self, section, key, value):
        self.data[section][key] = value


def set_macos_app_name(name=APP_NAME):
    """Make the first (application) menu show `name` instead of "Python".

    Must run before the first Tk window is created.  It needs pyobjc
    (`pip install pyobjc-framework-Cocoa`); without it the menu keeps the
    name of the interpreter, but everything else works unchanged.
    """
    if sys.platform != "darwin":
        return False
    try:
        from Foundation import NSBundle  # type: ignore
    except ImportError:
        return False
    try:
        bundle = NSBundle.mainBundle()
        info = bundle.localizedInfoDictionary() or bundle.infoDictionary()
        if info is None:
            return False
        info["CFBundleName"] = name
        info["CFBundleDisplayName"] = name
        info["CFBundleExecutable"] = name
        return True
    except Exception:
        return False


# --------------------------------------------------------------------------
# reusable widgets
# --------------------------------------------------------------------------

class ColorSwatch(ttk.Frame):
    """Colour preview + 'Choose...' button. Cross platform (uses a Canvas)."""

    def __init__(self, master, color=PALETTE_FALLBACK, command=None):
        super().__init__(master)
        self._color = safe_hex(color)
        self._command = command

        self.preview = tk.Canvas(self, width=32, height=18, cursor="hand2",
                                 highlightthickness=1, highlightbackground="#777")
        self.preview.pack(side="left")
        self.preview.bind("<Button-1>", lambda _e: self.choose())
        ttk.Button(self, text="Choose...", width=10, command=self.choose).pack(
            side="left", padx=(5, 0))
        self._redraw()

    @property
    def color(self):
        return self._color

    def set_color(self, color, notify=False):
        self._color = safe_hex(color, self._color)
        self._redraw()
        if notify and self._command:
            self._command(self._color)

    def _redraw(self):
        self.preview.configure(background=self._color)

    def choose(self):
        _rgb, hex_value = colorchooser.askcolor(color=self._color,
                                                parent=self.winfo_toplevel())
        if hex_value:
            self.set_color(hex_value, notify=True)


class ToolDialog(tk.Toplevel):
    """Base class of the small property windows."""

    def __init__(self, master, title, on_close=None):
        super().__init__(master)
        self.title(title)
        self.transient(master)
        self.resizable(False, False)
        self._on_close = on_close
        self.body = ttk.Frame(self, padding=12)
        self.body.pack(fill="both", expand=True)
        self.bind("<Escape>", lambda _e: self.close())
        self.protocol("WM_DELETE_WINDOW", self.close)

    def close(self):
        if self._on_close:
            self._on_close(self)
        self.destroy()

    @staticmethod
    def field(parent, row, text, widget, pady=3):
        ttk.Label(parent, text=text).grid(row=row, column=0, sticky="w",
                                          padx=(0, 8), pady=pady)
        widget.grid(row=row, column=1, sticky="w", pady=pady)
        return widget


# --------------------------------------------------------------------------
# settings (configuration file editor)
# --------------------------------------------------------------------------

class SettingsDialog(ToolDialog):
    """Edits every default of the program and writes the configuration file."""

    def __init__(self, master, config: Config, on_saved=None, on_close=None):
        super().__init__(master, f"{APP_NAME} settings", on_close=on_close)
        self.config_obj = config
        self.on_saved = on_saved
        self._getters = {}

        notebook = ttk.Notebook(self.body)
        notebook.pack(fill="both", expand=True)
        for section, title, fields in SETTINGS_SPEC:
            page = ttk.Frame(notebook, padding=12)
            notebook.add(page, text=title)
            for row, spec in enumerate(fields):
                self._add_field(page, row, section, spec)

        info = ttk.Label(self.body, foreground="#666", justify="left",
                         text=f"Saved to: {config.path}\n"
                              "Window sizes and plot defaults are used by "
                              "windows opened after saving.")
        info.pack(anchor="w", pady=(10, 0))

        bar = ttk.Frame(self.body)
        bar.pack(fill="x", pady=(12, 0))
        ttk.Button(bar, text="Restore defaults", command=self._restore).pack(side="left")
        ttk.Button(bar, text="Cancel", command=self.close).pack(side="right")
        ttk.Button(bar, text="Save", command=self._save).pack(side="right", padx=(0, 6))

    # -- construction ------------------------------------------------------
    def _add_field(self, page, row, section, spec):
        key, label, kind = spec[0], spec[1], spec[2]
        extra = spec[3] if len(spec) > 3 else None
        value = self.config_obj.get(section, key)

        if kind == "bool":
            var = tk.BooleanVar(value=bool(value))
            widget = ttk.Checkbutton(page, text=label, variable=var)
            widget.grid(row=row, column=0, columnspan=2, sticky="w", pady=3)
            getter = var.get
        elif kind == "choice":
            var = tk.StringVar(value=str(value))
            widget = ttk.Combobox(page, textvariable=var, state="readonly",
                                  values=extra, width=18)
            self.field(page, row, label, widget)
            getter = var.get
        elif kind == "color":
            widget = ColorSwatch(page, safe_hex(value))
            self.field(page, row, label, widget)
            getter = lambda w=widget: w.color
        else:
            var = tk.StringVar(value=str(value))
            widget = ttk.Entry(page, textvariable=var, width=30)
            self.field(page, row, label, widget)
            if kind == "int":
                getter = lambda v=var, la=label: self._parse(v.get(), la, int)
            elif kind == "float":
                getter = lambda v=var, la=label: self._parse(v.get(), la, float)
            else:
                getter = var.get
        self._getters[(section, key)] = getter

    @staticmethod
    def _parse(text, label, kind):
        value = to_float(text, None)
        if value is None:
            raise ValueError(f"'{label}' is not a number: {text!r}")
        return kind(round(value)) if kind is int else kind(value)

    # -- behaviour ---------------------------------------------------------
    def _restore(self):
        if not messagebox.askyesno(
                "Restore defaults",
                "Reset every setting to the built-in default value?", parent=self):
            return
        self.config_obj.reset()
        self._write_file()
        if self.on_saved:
            self.on_saved()
        self.close()

    def _save(self):
        try:
            values = {key: getter() for key, getter in self._getters.items()}
        except ValueError as error:
            messagebox.showerror("Invalid value", str(error), parent=self)
            return
        for (section, key), value in values.items():
            self.config_obj.set(section, key, value)
        if not self._write_file():
            return
        if self.on_saved:
            self.on_saved()
        self.close()

    def _write_file(self):
        try:
            self.config_obj.save()
            return True
        except OSError as error:
            messagebox.showerror("Error",
                                 f"The settings could not be saved:\n{error}",
                                 parent=self)
            return False


# --------------------------------------------------------------------------
# text + font size (title, axis labels, legend entries)
# --------------------------------------------------------------------------

class TextStyleDialog(ToolDialog):
    """One text with its font size and colour: `on_apply(text, size, colour)`."""

    def __init__(self, master, title, text, size, on_apply,
                 color="#000000", hint=None, on_close=None):
        super().__init__(master, title, on_close=on_close)
        self.on_apply = on_apply
        self.text_var = tk.StringVar(value=text)
        self.size_var = tk.StringVar(value=str(int(size)))

        box = ttk.Frame(self.body)
        box.pack(fill="x")
        entry = self.field(box, 0, "Text:",
                           ttk.Entry(box, textvariable=self.text_var, width=34))
        self.field(box, 1, "Font size:",
                   ttk.Spinbox(box, from_=4, to=72, increment=1, width=8,
                               textvariable=self.size_var, command=self.apply))
        self.color = ColorSwatch(box, color, command=lambda _c: self.apply())
        self.field(box, 2, "Font colour:", self.color)
        if hint:
            ttk.Label(self.body, text=hint, foreground="#666").pack(
                anchor="w", pady=(6, 0))

        bar = ttk.Frame(self.body)
        bar.pack(fill="x", pady=(12, 0))
        ttk.Button(bar, text="Apply", command=self.apply).pack(side="left")
        ttk.Button(bar, text="Close", command=self.close).pack(side="right")
        ttk.Button(bar, text="OK", command=self._ok).pack(side="right", padx=(0, 6))
        self.bind("<Return>", lambda _e: self.apply())
        entry.focus_set()
        entry.select_range(0, "end")

    def apply(self):
        self.on_apply(self.text_var.get(), to_int(self.size_var.get(), 10),
                      self.color.color)

    def _ok(self):
        self.apply()
        self.close()


# --------------------------------------------------------------------------
# curve (line + marker) properties
# --------------------------------------------------------------------------

class SeriesStyleDialog(ToolDialog):
    """Line and marker properties of one curve; changes are applied live."""

    def __init__(self, master, line: Line2D, on_change, on_close=None,
                 legend_size=None, legend_color="#000000", on_legend_style=None,
                 fill=None, on_fill=None):
        super().__init__(master, "Curve properties", on_close=on_close)
        self.line = line
        self.on_change = on_change
        self.on_legend_style = on_legend_style
        self.on_fill = on_fill
        self._fill = dict(fill or {})
        self.legend_size_var = tk.StringVar(
            value=str(int(legend_size if legend_size is not None else 10)))
        self._legend_color = safe_hex(legend_color, "#000000")
        self._loading = True

        label = line.get_label()
        self.label_var = tk.StringVar(value="" if label.startswith("_") else label)
        self.lstyle_var = tk.StringVar(
            value=name_of(LINE_STYLES, line.get_linestyle(), "Solid"))
        self.lwidth_var = tk.StringVar(value=f"{line.get_linewidth():g}")
        self.mstyle_var = tk.StringVar(
            value=name_of(MARKERS, line.get_marker(), "None"))
        self.msize_var = tk.StringVar(value=f"{line.get_markersize():g}")
        self.mwidth_var = tk.StringVar(value=f"{line.get_markeredgewidth():g}")

        face = line.get_markerfacecolor()
        self.hollow_var = tk.BooleanVar(
            value=isinstance(face, str) and face == "none")

        self.fill_on_var = tk.BooleanVar(value=bool(self._fill.get("on")))
        self.fill_follow_var = tk.BooleanVar(value=bool(self._fill.get("follow", True)))
        self.fill_alpha_var = tk.StringVar(value=f"{self._fill.get('alpha', 0.35):g}")
        self.fill_hatch_var = tk.StringVar(
            value=name_of(HATCH_PATTERNS, self._fill.get("hatch", ""),
                          names(HATCH_PATTERNS)[0]))
        self.fill_base_var = tk.StringVar(
            value=name_of(FILL_BASES, self._fill.get("base", "zero"), "Zero line"))

        line_color = safe_hex(line.get_color())
        self._build_legend_box()
        self._build_line_box(line_color)
        self._build_marker_box(line_color, face)
        self._build_fill_box(line_color)
        self._build_buttons()
        self._loading = False

    # -- construction ------------------------------------------------------
    def _build_legend_box(self):
        box = ttk.LabelFrame(self.body, text="Legend", padding=8)
        box.pack(fill="x")
        self.field(box, 0, "Text:", ttk.Entry(box, textvariable=self.label_var, width=30))
        self.label_var.trace_add("write", self._apply)
        self.field(box, 1, "Font size:",
                   ttk.Spinbox(box, from_=4, to=72, increment=1, width=8,
                               textvariable=self.legend_size_var,
                               command=self._apply))
        self.legend_size_var.trace_add("write", self._apply)
        self.legend_color = ColorSwatch(box, self._legend_color,
                                        command=lambda _c: self._apply())
        self.field(box, 2, "Font colour:", self.legend_color)
        ttk.Label(box, text="Empty text hides this curve's legend box.",
                  foreground="#666").grid(row=3, column=0, columnspan=2,
                                          sticky="w", pady=(4, 0))

    def _build_line_box(self, line_color):
        box = ttk.LabelFrame(self.body, text="Line", padding=8)
        box.pack(fill="x", pady=(10, 0))

        combo = ttk.Combobox(box, textvariable=self.lstyle_var, state="readonly",
                             values=names(LINE_STYLES), width=14)
        self.field(box, 0, "Style:", combo)
        combo.bind("<<ComboboxSelected>>", self._apply)

        self.field(box, 1, "Width:",
                   ttk.Spinbox(box, from_=0, to=20, increment=0.5, width=8,
                               textvariable=self.lwidth_var, command=self._apply))
        self.lwidth_var.trace_add("write", self._apply)

        self.line_color = ColorSwatch(box, line_color, command=lambda _c: self._apply())
        self.field(box, 2, "Colour:", self.line_color)

    def _build_marker_box(self, line_color, face):
        box = ttk.LabelFrame(self.body, text="Marker", padding=8)
        box.pack(fill="x", pady=(10, 0))

        combo = ttk.Combobox(box, textvariable=self.mstyle_var, state="readonly",
                             values=names(MARKERS), width=14)
        self.field(box, 0, "Style:", combo)
        combo.bind("<<ComboboxSelected>>", self._apply)

        self.field(box, 1, "Size:",
                   ttk.Spinbox(box, from_=0, to=40, increment=1, width=8,
                               textvariable=self.msize_var, command=self._apply))
        self.msize_var.trace_add("write", self._apply)

        self.face_color = ColorSwatch(box, safe_hex(face, line_color),
                                      command=lambda _c: self._apply())
        self.field(box, 2, "Fill colour:", self.face_color)
        self.field(box, 3, "", ttk.Checkbutton(box, text="Hollow (no fill)",
                                               variable=self.hollow_var,
                                               command=self._apply))

        self.edge_color = ColorSwatch(
            box, safe_hex(self.line.get_markeredgecolor(), line_color),
            command=lambda _c: self._apply())
        self.field(box, 4, "Edge colour:", self.edge_color)

        self.field(box, 5, "Edge width:",
                   ttk.Spinbox(box, from_=0, to=10, increment=0.5, width=8,
                               textvariable=self.mwidth_var, command=self._apply))
        self.mwidth_var.trace_add("write", self._apply)

    def _build_fill_box(self, line_color):
        box = ttk.LabelFrame(self.body, text="Fill under the curve", padding=8)
        box.pack(fill="x", pady=(10, 0))

        self.field(box, 0, "", ttk.Checkbutton(box, text="Fill the area",
                                               variable=self.fill_on_var,
                                               command=self._apply))
        self.field(box, 1, "", ttk.Checkbutton(box, text="Same colour as the curve",
                                               variable=self.fill_follow_var,
                                               command=self._apply))
        self.fill_color = ColorSwatch(box, self._fill.get("color", line_color),
                                      command=lambda _c: self._apply())
        self.field(box, 2, "Fill colour:", self.fill_color)
        self.field(box, 3, "Opacity (0-1):",
                   ttk.Spinbox(box, from_=0, to=1, increment=0.05, width=8,
                               textvariable=self.fill_alpha_var, command=self._apply))
        self.fill_alpha_var.trace_add("write", self._apply)

        pattern = ttk.Combobox(box, textvariable=self.fill_hatch_var,
                               state="readonly", values=names(HATCH_PATTERNS),
                               width=22)
        self.field(box, 4, "Pattern:", pattern)
        pattern.bind("<<ComboboxSelected>>", self._apply)

        base = ttk.Combobox(box, textvariable=self.fill_base_var, state="readonly",
                            values=names(FILL_BASES), width=22)
        self.field(box, 5, "Fill down to:", base)
        base.bind("<<ComboboxSelected>>", self._apply)

    def _build_buttons(self):
        bar = ttk.Frame(self.body)
        bar.pack(fill="x", pady=(12, 0))
        ttk.Button(bar, text="Marker colour = line colour",
                   command=self._sync_colors).pack(side="left")
        ttk.Button(bar, text="Close", command=self.close).pack(side="right")

    # -- behaviour ---------------------------------------------------------
    def _sync_colors(self):
        color = self.line_color.color
        self.face_color.set_color(color)
        self.edge_color.set_color(color)
        self._apply()

    def _apply(self, *_args):
        if self._loading:
            return
        line = self.line

        line.set_linestyle(code_of(LINE_STYLES, self.lstyle_var.get(), "-"))
        line.set_linewidth(to_float(self.lwidth_var.get(), line.get_linewidth()))
        line.set_color(self.line_color.color)

        line.set_marker(code_of(MARKERS, self.mstyle_var.get(), "None"))
        line.set_markersize(to_float(self.msize_var.get(), line.get_markersize()))
        line.set_markerfacecolor("none" if self.hollow_var.get()
                                 else self.face_color.color)
        line.set_markeredgecolor(self.edge_color.color)
        line.set_markeredgewidth(to_float(self.mwidth_var.get(),
                                          line.get_markeredgewidth()))

        text = self.label_var.get().strip()
        line.set_label(text if text else "_nolegend_")
        if self.on_legend_style:
            self.on_legend_style(to_int(self.legend_size_var.get(), 10),
                                 self.legend_color.color)
        if self.on_fill:
            self.on_fill({
                "on": self.fill_on_var.get(),
                "follow": self.fill_follow_var.get(),
                "color": self.fill_color.color,
                "alpha": to_float(self.fill_alpha_var.get(), 0.35),
                "hatch": code_of(HATCH_PATTERNS, self.fill_hatch_var.get(), ""),
                "base": code_of(FILL_BASES, self.fill_base_var.get(), "zero"),
            })
        self.on_change()


# --------------------------------------------------------------------------
# axes properties: one window, one tab per axis
# --------------------------------------------------------------------------

class AxisTab(ttk.Frame):
    """One page of the axes dialog (X or Y)."""

    def __init__(self, master, plot, which):
        super().__init__(master, padding=12)
        self.plot = plot
        self.which = which

        cfg = plot.axis_cfg[which]
        low, high = plot.current_limits(which)
        grid = cfg["grid"]

        self.label_var = tk.StringVar(value=plot.axis_label(which))
        self.label_size_var = tk.StringVar(value=str(cfg["label_size"]))
        self.tick_size_var = tk.StringVar(value=str(cfg["tick_size"]))
        self._label_color = cfg["label_color"]
        self._tick_color = cfg["tick_color"]
        self.auto_var = tk.BooleanVar(value=cfg["auto"])
        self.min_var = tk.StringVar(value=f"{low:g}")
        self.max_var = tk.StringVar(value=f"{high:g}")
        self.step_var = tk.StringVar(
            value="" if cfg["step"] in (None, 0) else f"{cfg['step']:g}")
        self.minor_var = tk.StringVar(value=str(cfg["minor"]))
        self.gmajor_var = tk.BooleanVar(value=grid["major"])
        self.gminor_var = tk.BooleanVar(value=grid["minor"])
        self.gstyle_var = tk.StringVar(value=name_of(GRID_STYLES, grid["style"], "Dotted"))
        self.gwidth_var = tk.StringVar(value=f"{grid['width']:g}")

        self._build_label_box()
        self._build_range_box()
        self._build_grid_box(grid["color"])
        self._toggle_auto()

    # -- construction ------------------------------------------------------
    def _build_label_box(self):
        box = ttk.LabelFrame(self, text="Axis label and fonts", padding=8)
        box.pack(fill="x")
        ToolDialog.field(box, 0, "Label text:",
                         ttk.Entry(box, textvariable=self.label_var, width=30))
        ToolDialog.field(box, 1, "Label font size:",
                         ttk.Spinbox(box, from_=4, to=48, increment=1, width=8,
                                     textvariable=self.label_size_var))
        self.label_color = ColorSwatch(box, self._label_color)
        ToolDialog.field(box, 2, "Label font colour:", self.label_color)
        ToolDialog.field(box, 3, "Numbers (ticks) font size:",
                         ttk.Spinbox(box, from_=4, to=48, increment=1, width=8,
                                     textvariable=self.tick_size_var))
        self.tick_color = ColorSwatch(box, self._tick_color)
        ToolDialog.field(box, 4, "Numbers (ticks) font colour:", self.tick_color)

    def _build_range_box(self):
        box = ttk.LabelFrame(self, text="Range and ticks", padding=8)
        box.pack(fill="x", pady=(10, 0))
        ttk.Checkbutton(box, text="Automatic range and ticks",
                        variable=self.auto_var, command=self._toggle_auto
                        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 4))
        self.min_entry = ToolDialog.field(
            box, 1, "From:", ttk.Entry(box, textvariable=self.min_var, width=12))
        self.max_entry = ToolDialog.field(
            box, 2, "To:", ttk.Entry(box, textvariable=self.max_var, width=12))
        self.step_entry = ToolDialog.field(
            box, 3, "Step (major ticks):",
            ttk.Entry(box, textvariable=self.step_var, width=12))
        ToolDialog.field(box, 4, "Minor ticks between majors:",
                         ttk.Spinbox(box, from_=0, to=20, increment=1, width=8,
                                     textvariable=self.minor_var))

    def _build_grid_box(self, color):
        box = ttk.LabelFrame(self, text="Grid of this axis", padding=8)
        box.pack(fill="x", pady=(10, 0))
        ttk.Checkbutton(box, text="Major grid lines", variable=self.gmajor_var
                        ).grid(row=0, column=0, columnspan=2, sticky="w")
        ttk.Checkbutton(box, text="Minor grid lines", variable=self.gminor_var
                        ).grid(row=1, column=0, columnspan=2, sticky="w")
        self.grid_color = ColorSwatch(box, color)
        ToolDialog.field(box, 2, "Colour:", self.grid_color)
        ToolDialog.field(box, 3, "Style:",
                         ttk.Combobox(box, textvariable=self.gstyle_var,
                                      state="readonly", values=names(GRID_STYLES),
                                      width=12))
        ToolDialog.field(box, 4, "Width:",
                         ttk.Spinbox(box, from_=0.2, to=5, increment=0.2, width=8,
                                     textvariable=self.gwidth_var))

    # -- behaviour ---------------------------------------------------------
    def _toggle_auto(self):
        state = "disabled" if self.auto_var.get() else "normal"
        for widget in (self.min_entry, self.max_entry, self.step_entry):
            widget.configure(state=state)

    def values(self):
        low, high = self.plot.current_limits(self.which)
        return {
            "auto": self.auto_var.get(),
            "min": to_float(self.min_var.get(), low),
            "max": to_float(self.max_var.get(), high),
            "step": to_float(self.step_var.get(), None),
            "minor": max(0, to_int(self.minor_var.get(), 0)),
            "label": self.label_var.get(),
            "label_size": to_int(self.label_size_var.get(), 11),
            "tick_size": to_int(self.tick_size_var.get(), 10),
            "label_color": self.label_color.color,
            "tick_color": self.tick_color.color,
            "grid": {
                "major": self.gmajor_var.get(),
                "minor": self.gminor_var.get(),
                "color": self.grid_color.color,
                "style": code_of(GRID_STYLES, self.gstyle_var.get(), ":"),
                "width": to_float(self.gwidth_var.get(), 0.8),
            },
        }


class FrameTab(ttk.Frame):
    """Frame (spines) and the size/position of the axes inside the window."""

    def __init__(self, master, plot):
        super().__init__(master, padding=12)
        self.plot = plot
        cfg = plot.frame_cfg

        self.style_var = tk.StringVar(
            value=name_of(FRAME_STYLES, cfg["style"], names(FRAME_STYLES)[0]))
        self.width_var = tk.StringVar(value=f"{cfg['width']:g}")
        self.major_len_var = tk.StringVar(value=f"{cfg['major_tick_length']:g}")
        self.minor_len_var = tk.StringVar(value=f"{cfg['minor_tick_length']:g}")
        background = cfg.get("background", "#ffffff")
        self.transparent_var = tk.BooleanVar(value=background == "none")
        self.unit_var = tk.StringVar(value=SIZE_UNITS[0])
        self._unit = SIZE_UNITS[0]

        left, bottom, width, height = plot.ax.get_position().bounds
        self._fractions = {"left": left, "bottom": bottom,
                           "x_length": width, "y_length": height}
        self.value_vars = {key: tk.StringVar() for key in self._fractions}

        self._build_frame_box(cfg["color"])
        self._build_background_box(cfg)
        self._build_size_box()
        self._show_values()

    # -- construction ------------------------------------------------------
    def _build_frame_box(self, color):
        box = ttk.LabelFrame(self, text="Frame", padding=8)
        box.pack(fill="x")
        ToolDialog.field(box, 0, "Style:",
                         ttk.Combobox(box, textvariable=self.style_var,
                                      state="readonly", values=names(FRAME_STYLES),
                                      width=26))
        ToolDialog.field(box, 1, "Thickness:",
                         ttk.Spinbox(box, from_=0, to=10, increment=0.2, width=8,
                                     textvariable=self.width_var))
        self.color = ColorSwatch(box, color)
        ToolDialog.field(box, 2, "Colour:", self.color)
        ToolDialog.field(box, 3, "Major tick length:",
                         ttk.Spinbox(box, from_=0, to=30, increment=0.5, width=8,
                                     textvariable=self.major_len_var))
        ToolDialog.field(box, 4, "Minor tick length:",
                         ttk.Spinbox(box, from_=0, to=30, increment=0.5, width=8,
                                     textvariable=self.minor_len_var))
        ttk.Label(box, foreground="#666", justify="left",
                  text="\"No frame\" hides the top and the right side; the two\n"
                       "\"with ticks\" styles put ticks on all four sides.\n"
                       "Clicking any side of the frame opens this dialog.").grid(
            row=5, column=0, columnspan=2, sticky="w", pady=(6, 0))

    def _build_background_box(self, cfg):
        box = ttk.LabelFrame(self, text="Background", padding=8)
        box.pack(fill="x", pady=(10, 0))
        background = cfg.get("background", "#ffffff")
        self.background = ColorSwatch(
            box, "#ffffff" if background == "none" else background)
        ToolDialog.field(box, 0, "Plot area:", self.background)
        ToolDialog.field(box, 1, "",
                         ttk.Checkbutton(box, text="Transparent plot area",
                                         variable=self.transparent_var))
        self.figure_background = ColorSwatch(
            box, cfg.get("figure_background", "#ffffff"))
        ToolDialog.field(box, 2, "Around the axes:", self.figure_background)

    def _build_size_box(self):
        box = ttk.LabelFrame(self, text="Size and origin of the axes", padding=8)
        box.pack(fill="x", pady=(10, 0))

        units = ttk.Combobox(box, textvariable=self.unit_var, state="readonly",
                             values=SIZE_UNITS, width=18)
        ToolDialog.field(box, 0, "Units:", units)
        units.bind("<<ComboboxSelected>>", self._change_unit)

        labels = [("x_length", "Width (length of the X axis):"),
                  ("y_length", "Height (length of the Y axis):"),
                  ("left", "Y axis distance from the left:"),
                  ("bottom", "X axis distance from the bottom:")]
        for row, (key, text) in enumerate(labels, start=1):
            ToolDialog.field(box, row, text,
                             ttk.Entry(box, textvariable=self.value_vars[key],
                                       width=12))
        ttk.Button(box, text="Default layout", command=self._reset).grid(
            row=5, column=1, sticky="w", pady=(6, 0))
        self.hint = ttk.Label(box, foreground="#666")
        self.hint.grid(row=6, column=0, columnspan=2, sticky="w", pady=(6, 0))

    # -- units -------------------------------------------------------------
    def _factor(self, key, unit=None):
        unit = unit or self._unit
        if unit == SIZE_UNITS[0]:
            return 1.0
        inches = self.plot.fig.get_size_inches()
        size = inches[0] if key in ("left", "x_length") else inches[1]
        return size * 2.54 if unit == "cm" else size

    def _show_values(self):
        for key, var in self.value_vars.items():
            var.set(f"{self._fractions[key] * self._factor(key):.4g}")
        width_cm = self._fractions["x_length"] * self._factor("x_length", "cm")
        height_cm = self._fractions["y_length"] * self._factor("y_length", "cm")
        self.hint.configure(
            text=f"Current size on the screen: {width_cm:.1f} x {height_cm:.1f} cm "
                 "(fractions keep it when the window is resized).")

    def _read_values(self):
        for key, var in self.value_vars.items():
            value = to_float(var.get(), None)
            if value is not None:
                self._fractions[key] = value / self._factor(key)

    def _change_unit(self, _event=None):
        self._read_values()                 # still in the previous unit
        self._unit = self.unit_var.get()
        self._show_values()

    def _reset(self):
        self._fractions = dict(zip(("left", "bottom", "x_length", "y_length"),
                                   self.plot.default_position))
        self._show_values()

    # -- result ------------------------------------------------------------
    def values(self):
        self._read_values()
        return {
            "style": code_of(FRAME_STYLES, self.style_var.get(), "none"),
            "width": max(0.0, to_float(self.width_var.get(), 1.0)),
            "color": self.color.color,
            "major_tick_length": max(0.0, to_float(self.major_len_var.get(), 3.5)),
            "minor_tick_length": max(0.0, to_float(self.minor_len_var.get(), 2.0)),
            "background": ("none" if self.transparent_var.get()
                           else self.background.color),
            "figure_background": self.figure_background.color,
            "left": self._fractions["left"], "bottom": self._fractions["bottom"],
            "x_length": self._fractions["x_length"],
            "y_length": self._fractions["y_length"],
        }


class AxesDialog(ToolDialog):
    """Both axes and the frame in a single window, selected with the tabs."""

    def __init__(self, master, plot, initial="x", on_close=None):
        super().__init__(master, "Axes properties", on_close=on_close)
        self.plot = plot

        notebook = ttk.Notebook(self.body)
        notebook.pack(fill="both", expand=True)
        self.tabs = {}
        for which in ("x", "y"):
            tab = AxisTab(notebook, plot, which)
            notebook.add(tab, text=f"{which.upper()} axis")
            self.tabs[which] = tab
        self.frame_tab = FrameTab(notebook, plot)
        notebook.add(self.frame_tab, text="Frame and origin")
        self.notebook = notebook
        self.select_tab(initial)

        bar = ttk.Frame(self.body)
        bar.pack(fill="x", pady=(12, 0))
        ttk.Button(bar, text="Apply", command=self.apply).pack(side="left")
        ttk.Button(bar, text="Close", command=self.close).pack(side="right")
        ttk.Button(bar, text="OK", command=self._ok).pack(side="right", padx=(0, 6))
        self.bind("<Return>", lambda _e: self.apply())

    def select_tab(self, which):
        """which: 'x', 'y' or 'frame'."""
        if which == "frame":
            self.notebook.select(self.frame_tab)
        else:
            self.notebook.select(self.tabs.get(which, self.tabs["x"]))

    def apply(self):
        for which, tab in self.tabs.items():
            cfg = tab.values()
            if not cfg["auto"] and cfg["min"] == cfg["max"]:
                messagebox.showwarning(
                    "Axis range",
                    f"'From' and 'To' must be different on the "
                    f"{which.upper()} axis.", parent=self)
                return False
            self.plot.apply_axis(which, cfg, redraw=False)

        frame = self.frame_tab.values()
        problem = self.plot.check_frame(frame)
        if problem:
            messagebox.showwarning("Frame and origin", problem, parent=self)
            return False
        self.plot.apply_frame(frame, redraw=False)
        self.frame_tab._show_values()
        self.plot.draw()
        return True

    def _ok(self):
        if self.apply():
            self.close()


class LegendDialog(ToolDialog):
    """One legend box: text, font, surrounding box and background."""

    def __init__(self, master, column, text, state, on_apply, on_close=None):
        super().__init__(master, f"Legend of '{column}'", on_close=on_close)
        self.on_apply = on_apply

        self.text_var = tk.StringVar(value=text)
        self.size_var = tk.StringVar(value=str(int(state.get("size", 10))))
        edge = state.get("edge", "#000000")
        face = state.get("face", "#ffffff")
        self.frame_var = tk.BooleanVar(value=edge != "none")
        self.transparent_var = tk.BooleanVar(value=face == "none")

        box = ttk.LabelFrame(self.body, text="Text", padding=8)
        box.pack(fill="x")
        entry = self.field(box, 0, "Text:",
                           ttk.Entry(box, textvariable=self.text_var, width=32))
        self.field(box, 1, "Font size:",
                   ttk.Spinbox(box, from_=4, to=72, increment=1, width=8,
                               textvariable=self.size_var, command=self.apply))
        self.color = ColorSwatch(box, state.get("color", "#000000"),
                                 command=lambda _c: self.apply())
        self.field(box, 2, "Font colour:", self.color)
        ttk.Label(box, text="An empty text hides this legend box.",
                  foreground="#666").grid(row=3, column=0, columnspan=2,
                                          sticky="w", pady=(4, 0))

        frame_box = ttk.LabelFrame(self.body, text="Surrounding box", padding=8)
        frame_box.pack(fill="x", pady=(10, 0))
        self.field(frame_box, 0, "",
                   ttk.Checkbutton(frame_box, text="Frame around the box",
                                   variable=self.frame_var, command=self.apply))
        self.edge_color = ColorSwatch(frame_box, "#000000" if edge == "none" else edge,
                                      command=lambda _c: self.apply())
        self.field(frame_box, 1, "Frame colour:", self.edge_color)
        self.face_color = ColorSwatch(frame_box,
                                      "#ffffff" if face == "none" else face,
                                      command=lambda _c: self.apply())
        self.field(frame_box, 2, "Background colour:", self.face_color)
        self.field(frame_box, 3, "",
                   ttk.Checkbutton(frame_box, text="Transparent background",
                                   variable=self.transparent_var,
                                   command=self.apply))
        ttk.Label(frame_box, text="Drag the frame of a box to move it.",
                  foreground="#666").grid(row=4, column=0, columnspan=2,
                                          sticky="w", pady=(4, 0))

        bar = ttk.Frame(self.body)
        bar.pack(fill="x", pady=(12, 0))
        ttk.Button(bar, text="Apply", command=self.apply).pack(side="left")
        ttk.Button(bar, text="Close", command=self.close).pack(side="right")
        ttk.Button(bar, text="OK", command=self._ok).pack(side="right", padx=(0, 6))
        self.bind("<Return>", lambda _e: self.apply())
        entry.focus_set()
        entry.select_range(0, "end")

    def values(self):
        return {
            "text": self.text_var.get(),
            "size": to_int(self.size_var.get(), 10),
            "color": self.color.color,
            "edge": self.edge_color.color if self.frame_var.get() else "none",
            "face": "none" if self.transparent_var.get() else self.face_color.color,
        }

    def apply(self):
        self.on_apply(self.values())

    def _ok(self):
        self.apply()
        self.close()


class TitleFontDialog(ToolDialog):
    """Plot title text and the font sizes that do not belong to an axis."""

    def __init__(self, master, plot, on_close=None):
        super().__init__(master, "Title and fonts", on_close=on_close)
        self.plot = plot

        self.title_var = tk.StringVar(value=plot.ax.get_title())
        self.title_size_var = tk.StringVar(value=str(plot.fonts["title"]))
        self.legend_size_var = tk.StringVar(value=str(plot.fonts["legend"]))
        self.legend_loc_var = tk.StringVar(value=plot.legend_loc)
        self.legend_visible_var = tk.BooleanVar(value=plot.legend_visible)

        box = ttk.LabelFrame(self.body, text="Title", padding=8)
        box.pack(fill="x")
        self.field(box, 0, "Text:", ttk.Entry(box, textvariable=self.title_var, width=34))
        self.field(box, 1, "Font size:",
                   ttk.Spinbox(box, from_=4, to=48, increment=1, width=8,
                               textvariable=self.title_size_var))
        self.title_color = ColorSwatch(
            box, safe_hex(plot.fonts["title_color"], "#000000"))
        self.field(box, 2, "Font colour:", self.title_color)

        legend_box = ttk.LabelFrame(self.body, text="Legend boxes", padding=8)
        legend_box.pack(fill="x", pady=(10, 0))
        self.field(legend_box, 0, "", ttk.Checkbutton(legend_box, text="Show legends",
                                                      variable=self.legend_visible_var))
        self.field(legend_box, 1, "Font size (all):",
                   ttk.Spinbox(legend_box, from_=4, to=72, increment=1, width=8,
                               textvariable=self.legend_size_var))
        self.legend_color = ColorSwatch(
            legend_box, safe_hex(plot.fonts["legend_color"], "#000000"))
        self.field(legend_box, 2, "Font colour (all):", self.legend_color)
        self.field(legend_box, 3, "Start position:",
                   ttk.Combobox(legend_box, textvariable=self.legend_loc_var,
                                state="readonly", values=LEGEND_LOCATIONS, width=16))
        ttk.Button(legend_box, text="Reset positions",
                   command=self._reset_positions).grid(row=4, column=1, sticky="w",
                                                       pady=(6, 0))
        ttk.Label(legend_box, foreground="#666", justify="left",
                  text="Every curve has its own legend box: drag its frame to move\n"
                       "it, click its text to change its text, size and colour.").grid(
            row=5, column=0, columnspan=2, sticky="w", pady=(6, 0))

        bar = ttk.Frame(self.body)
        bar.pack(fill="x", pady=(12, 0))
        ttk.Button(bar, text="Apply", command=self.apply).pack(side="left")
        ttk.Button(bar, text="Close", command=self.close).pack(side="right")
        self.bind("<Return>", lambda _e: self.apply())

    def apply(self):
        plot = self.plot
        plot.fonts["title"] = to_int(self.title_size_var.get(), plot.fonts["title"])
        plot.fonts["title_color"] = self.title_color.color
        size = to_int(self.legend_size_var.get(), plot.fonts["legend"])
        color = self.legend_color.color
        plot.fonts["legend"] = size
        plot.fonts["legend_color"] = color
        for state in plot.legend_state.values():   # one size/colour for all
            state["size"] = size
            state["color"] = color
        plot.legend_loc = self.legend_loc_var.get()
        plot.legend_visible = self.legend_visible_var.get()
        plot.ax.set_title(self.title_var.get(), fontsize=plot.fonts["title"],
                          color=plot.fonts["title_color"])
        plot.ax.title.set_picker(True)
        plot.refresh_legend()
        plot.draw()

    def _reset_positions(self):
        self.plot.legend_loc = self.legend_loc_var.get()
        self.plot.reset_legend_positions()


# --------------------------------------------------------------------------
# data table
# --------------------------------------------------------------------------

class DataTable(ttk.Frame):
    """Treeview based table with in-place cell editing."""

    def __init__(self, master, config: Config, on_change=None, on_rename=None):
        super().__init__(master)
        self.config_obj = config
        self.on_change = on_change
        self.on_rename = on_rename
        self.df = pd.DataFrame()
        self.current_column = None      # column of the last clicked cell/heading
        self._editor = None
        self._heading_editor = None

        self.style = ttk.Style(self)
        self.tree = ttk.Treeview(self, show="headings", selectmode="browse",
                                 style="APlot.Treeview")
        v_scroll = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        h_scroll = ttk.Scrollbar(self, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        v_scroll.grid(row=0, column=1, sticky="ns")
        h_scroll.grid(row=1, column=0, sticky="ew")
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

        self.tree.bind("<Button-1>", self._on_click)
        for sequence in ("<Control-c>", "<Control-C>", "<Command-c>", "<Command-C>"):
            self.tree.bind(sequence, self._copy_rows)
        self.apply_config()

    # -- appearance --------------------------------------------------------
    def apply_config(self):
        size = max(6, int(self.config_obj.get("table", "font_size")))
        self.style.configure("APlot.Treeview", font=("TkDefaultFont", size),
                             rowheight=int(size * 2.2))
        self.style.configure("APlot.Treeview.Heading", font=("TkDefaultFont", size))
        width = max(40, int(self.config_obj.get("table", "column_width")))
        for column in self.tree["columns"]:
            self.tree.column(column, width=width)

    # -- data --------------------------------------------------------------
    def set_dataframe(self, df):
        self.df = df.reset_index(drop=True)
        self.df.columns = self._unique_columns(self.df.columns)
        self.refresh()

    @staticmethod
    def _unique_columns(columns):
        seen, result = {}, []
        for col in columns:
            name = str(col)
            if name in seen:
                seen[name] += 1
                name = f"{name}.{seen[name]}"
            else:
                seen[name] = 0
            result.append(name)
        return result

    def refresh(self):
        self._cancel_edit()
        self._cancel_heading_edit()
        self.tree.delete(*self.tree.get_children())
        columns = list(self.df.columns)
        width = max(40, int(self.config_obj.get("table", "column_width")))
        self.tree["columns"] = columns
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=width, anchor="center", stretch=True)
        self.update_idletasks()
        for index, row in enumerate(self.df.itertuples(index=False, name=None)):
            self.tree.insert("", "end", iid=str(index),
                             values=["" if pd.isna(v) else str(v) for v in row])
        self._changed()

    def _changed(self):
        if self.on_change:
            self.on_change()

    def selected_row(self):
        selection = self.tree.selection()
        return int(selection[0]) if selection else None

    def add_row(self, focus=False):
        """Append one empty row (cheap: no full rebuild) and return its index."""
        if self.df.empty and not len(self.df.columns):
            return None
        index = len(self.df)
        self.df.loc[index] = ["" for _ in self.df.columns]
        self.tree.insert("", "end", iid=str(index),
                         values=["" for _ in self.df.columns])
        self._changed()
        if focus:
            self.tree.see(str(index))
            self.after(1, lambda: self._begin_edit(str(index), 0))
        return index

    def delete_row(self, index=None):
        index = self.selected_row() if index is None else index
        if index is None:
            return False
        self.set_dataframe(self.df.drop(index=index))
        return True

    def add_column(self, name):
        if name in self.df.columns:
            return False
        self.df[name] = ["" for _ in range(len(self.df))]
        self.refresh()
        return True

    def rename_column(self, old, new):
        """Rename one column; returns False if the name is taken or invalid."""
        new = str(new).strip()
        if not new or new == old:
            return False
        if new in self.df.columns:
            return False
        index = list(self.df.columns).index(old)
        self.df = self.df.rename(columns={old: new})
        self.refresh()
        self.current_column = new
        if self.on_rename:
            self.on_rename(old, new, index)
        return True

    # -- editing -----------------------------------------------------------
    def _on_click(self, event):
        region = self.tree.identify_region(event.x, event.y)
        column_id = self.tree.identify_column(event.x)
        if region == "heading" and column_id:
            self.after(1, lambda: self._begin_heading_edit(column_id))
            return
        if region != "cell":
            return
        row_id = self.tree.identify_row(event.y)
        if not row_id or not column_id:
            return
        col_index = int(column_id[1:]) - 1
        self.after(1, lambda: self._begin_edit(row_id, col_index))

    # -- column names ------------------------------------------------------
    def _heading_geometry(self, column_id):
        """Position of a column heading: (x, y, width, height)."""
        children = self.tree.get_children()
        if not children:
            return None
        bbox = self.tree.bbox(children[0], column_id)
        if not bbox:
            return None
        x, y, width, _height = bbox
        return x, 0, width, max(16, y)

    def _begin_heading_edit(self, column_id):
        self._commit_edit()
        self._cancel_heading_edit()
        col_index = int(column_id[1:]) - 1
        if not (0 <= col_index < len(self.df.columns)):
            return
        old = self.df.columns[col_index]
        self.current_column = old

        geometry = self._heading_geometry(column_id)
        if geometry is None:  # empty table: fall back to a small dialog
            new = simpledialog.askstring("Column name", "New column name:",
                                         initialvalue=old, parent=self)
            if new and not self.rename_column(old, new):
                messagebox.showerror("Error", f"'{new}' cannot be used.", parent=self)
            return

        x, y, width, height = geometry
        var = tk.StringVar(value=old)
        entry = tk.Entry(self.tree, textvariable=var, exportselection=False,
                         justify="center", borderwidth=1, relief="solid")
        entry.place(x=x, y=y, width=width, height=height)
        entry.focus_set()
        entry.select_range(0, "end")
        self._heading_editor = (entry, var, old)

        entry.bind("<Return>", lambda _e: self._commit_heading_edit())
        entry.bind("<KP_Enter>", lambda _e: self._commit_heading_edit())
        entry.bind("<Escape>", lambda _e: self._cancel_heading_edit())
        entry.bind("<FocusOut>", lambda _e: self._commit_heading_edit())
        self._bind_text_editing(entry)

    def _cancel_heading_edit(self):
        if self._heading_editor:
            entry, *_ = self._heading_editor
            self._heading_editor = None
            entry.destroy()
        return "break"

    def _commit_heading_edit(self):
        if not self._heading_editor:
            return "break"
        entry, var, old = self._heading_editor
        self._heading_editor = None
        new = var.get().strip()
        entry.destroy()
        if new and new != old and not self.rename_column(old, new):
            messagebox.showerror(
                "Error", f"'{new}' cannot be used as a column name "
                         "(it is empty or already exists).", parent=self)
        return "break"

    # -- selection / clipboard --------------------------------------------
    def _bind_text_editing(self, entry):
        """Selection and copy bindings shared by the cell and heading editors."""
        for sequence in ("<Control-a>", "<Control-A>", "<Command-a>", "<Command-A>"):
            entry.bind(sequence, self._select_all)
        for sequence in ("<Control-c>", "<Control-C>", "<Command-c>", "<Command-C>"):
            entry.bind(sequence, self._copy_text)
        # Shift+Up / Shift+Down extend the selection to the start / end
        entry.bind("<Shift-Up>", lambda e: self._extend_selection(e, "start"))
        entry.bind("<Shift-Down>", lambda e: self._extend_selection(e, "end"))

    @staticmethod
    def _select_all(event):
        event.widget.select_range(0, "end")
        event.widget.icursor("end")
        return "break"

    @staticmethod
    def _copy_text(event):
        widget = event.widget
        if widget.selection_present():
            text = widget.get()[widget.index("sel.first"):widget.index("sel.last")]
        else:
            text = widget.get()
        widget.clipboard_clear()
        widget.clipboard_append(text)
        return "break"

    @staticmethod
    def _extend_selection(event, where):
        """Shift+Up / Shift+Down: extend the selection from the anchor."""
        widget = event.widget
        target = 0 if where == "start" else len(widget.get())
        if not widget.selection_present():
            widget.selection_from(widget.index("insert"))  # set the anchor
        widget.selection_to(target)
        widget.icursor(target)
        return "break"

    def _copy_rows(self, _event=None):
        """Ctrl/Cmd+C on the table copies the selected row (tab separated)."""
        rows = self.tree.selection()
        if not rows:
            return "break"
        lines = ["\t".join(str(value) for value in self.tree.item(row, "values"))
                 for row in rows]
        self.clipboard_clear()
        self.clipboard_append("\n".join(lines))
        return "break"

    def _begin_edit(self, row_id, col_index, retry=True):
        self._commit_edit()
        if not self.tree.exists(row_id) or not (0 <= col_index < len(self.df.columns)):
            return
        self.tree.selection_set(row_id)
        self.tree.see(row_id)
        self.update_idletasks()
        bbox = self.tree.bbox(row_id, f"#{col_index + 1}")
        if not bbox:
            if retry:  # the row was scrolled into view only now
                self.after(20, lambda: self._begin_edit(row_id, col_index, False))
            return

        x, y, width, height = bbox
        column = self.df.columns[col_index]
        self.current_column = column
        var = tk.StringVar(value=self.tree.set(row_id, column))
        # exportselection=False keeps the highlighted text visible even when
        # another widget (e.g. the Treeview) takes over the X selection.
        entry = tk.Entry(self.tree, textvariable=var, exportselection=False,
                         borderwidth=1, relief="solid", justify="center")
        entry.place(x=x, y=y, width=width, height=height)
        entry.focus_set()
        entry.icursor("end")
        entry.select_range(0, "end")
        self._editor = (entry, var, row_id, col_index)

        for sequence, delta in (("<Return>", (1, 0)), ("<KP_Enter>", (1, 0)),
                                ("<Down>", (1, 0)), ("<Up>", (-1, 0)),
                                ("<Tab>", (0, 1)), ("<Shift-Tab>", (0, -1)),
                                ("<ISO_Left_Tab>", (0, -1))):
            entry.bind(sequence, lambda _e, d=delta: self._move(*d))
        # Left / Right walk inside the text and step to the neighbouring cell
        # when the cursor is already at the end of it
        entry.bind("<Left>", lambda e: self._arrow(e, 0, -1))
        entry.bind("<Right>", lambda e: self._arrow(e, 0, 1))
        for prefix in ("Control", "Command", "Alt"):
            for key, delta in (("Left", (0, -1)), ("Right", (0, 1)),
                               ("Up", (-1, 0)), ("Down", (1, 0))):
                entry.bind(f"<{prefix}-{key}>", lambda _e, d=delta: self._move(*d))
        entry.bind("<Escape>", lambda _e: self._cancel_edit())
        entry.bind("<FocusOut>", lambda _e: self._commit_edit())
        self._bind_text_editing(entry)

    def _arrow(self, event, d_row, d_col):
        """Left/Right: move the text cursor, or jump to the neighbour cell."""
        entry = event.widget
        if entry.selection_present():
            return None                     # let the selection collapse first
        cursor = entry.index("insert")
        if d_col < 0 and cursor > 0:
            return None                     # still text to walk through
        if d_col > 0 and cursor < len(entry.get()):
            return None
        return self._move(d_row, d_col)

    def _move(self, d_row, d_col):
        if not self._editor:
            return "break"
        _entry, _var, row_id, col_index = self._editor
        columns = len(self.df.columns)
        self._commit_edit()

        row = int(row_id) + d_row
        col = col_index + d_col
        if col >= columns:
            col, row = 0, row + 1
        elif col < 0:
            col, row = columns - 1, row - 1

        if row >= len(self.df):
            if self.config_obj.get("table", "auto_extend"):
                while row >= len(self.df):  # grow the table as needed
                    self.add_row()
            else:
                row = len(self.df) - 1
        row = max(0, min(len(self.df) - 1, row))
        col = max(0, min(columns - 1, col))
        self.after(1, lambda: self._begin_edit(str(row), col))
        return "break"

    def _cancel_edit(self):
        if self._editor:
            entry, *_ = self._editor
            self._editor = None
            entry.destroy()
        return "break"

    def _commit_edit(self):
        if not self._editor:
            return
        entry, var, row_id, col_index = self._editor
        self._editor = None
        text = var.get()
        entry.destroy()

        row = int(row_id)
        if row >= len(self.df) or col_index >= len(self.df.columns):
            return
        column = self.df.columns[col_index]
        value = coerce(text)
        try:
            self.df.iat[row, col_index] = value
        except (ValueError, TypeError):
            self.df[column] = self.df[column].astype(object)
            self.df.iat[row, col_index] = value
        if self.tree.exists(row_id):
            self.tree.set(row_id, column, "" if value == "" else str(value))
        self._changed()


# --------------------------------------------------------------------------
# interactive plot window
# --------------------------------------------------------------------------

class PlotWindow(tk.Toplevel):
    """Figure window: all plot related interaction lives here."""

    HINT = ("Click a curve: line and marker properties   |   "
            "Click the title, an axis label or a legend text: text, size, colour\n"
            "Drag the frame of a legend box: move it   |   "
            "Click the frame: frame and origin   |   "
            "Double-click next to an axis: axes properties")

    def __init__(self, master, df: pd.DataFrame, config: Config, app=None):
        super().__init__(master)
        self.title("Interactive Graph")
        self.settings = config
        self.app = app          # gives this window the full application menu
        plot_cfg = config.section("plot")
        grid_cfg = config.section("grid")
        self.geometry(f"{config.get('window', 'plot_width')}x"
                      f"{config.get('window', 'plot_height')}")

        self.df = df
        self.lines: list[Line2D] = []
        self.series: dict = {}          # Y column name -> curve
        self.x_col = str(df.columns[0]) if len(df.columns) else ""
        self.legends: dict = {}         # Y column name -> its own legend box
        self.legend_state: dict = {}    # Y column name -> {pos, loc, size, ...}
        self.fills: dict = {}           # Y column name -> filled area
        self.fill_state: dict = {}      # Y column name -> fill settings
        self._drag = None
        self._cursor = ""
        self._dialogs: dict = {}
        self.fonts = config.section("fonts")
        self.legend_loc = plot_cfg["legend_location"]
        self.legend_visible = bool(plot_cfg["legend_visible"])

        grid_defaults = {
            "major": bool(grid_cfg["major"]), "minor": bool(grid_cfg["minor"]),
            "color": safe_hex(grid_cfg["color"], "#b0b0b0"),
            "style": code_of(GRID_STYLES, grid_cfg["style"], ":"),
            "width": float(grid_cfg["width"]),
        }
        self.axis_cfg = {
            which: {"auto": True, "step": None,
                    "minor": max(0, int(grid_cfg["minor_ticks"])),
                    "label_size": int(self.fonts["axis_label"]),
                    "tick_size": int(self.fonts["tick_label"]),
                    "label_color": safe_hex(self.fonts["axis_label_color"], "#000000"),
                    "tick_color": safe_hex(self.fonts["tick_label_color"], "#000000"),
                    "grid": dict(grid_defaults)}
            for which in ("x", "y")
        }

        self.fig = Figure(figsize=(plot_cfg["fig_width"], plot_cfg["fig_height"]),
                          dpi=plot_cfg["dpi"])
        self.ax = self.fig.add_subplot(111)
        self.default_position = DEFAULT_POSITION
        frame = config.section("frame")
        self.frame_cfg = {
            "style": code_of(FRAME_STYLES, frame["style"], "none"),
            "width": float(frame["width"]),
            "color": safe_hex(frame["color"], "#000000"),
            "major_tick_length": float(frame["major_tick_length"]),
            "minor_tick_length": float(frame["minor_tick_length"]),
            "background": ("none" if frame.get("transparent_background")
                           else safe_hex(frame.get("background"), "#ffffff")),
            "figure_background": safe_hex(frame.get("figure_background"), "#ffffff"),
            "left": float(frame["left"]), "bottom": float(frame["bottom"]),
            "x_length": float(frame["x_length"]),
            "y_length": float(frame["y_length"]),
        }

        self._build_widgets()
        if not self._plot_data(plot_cfg):
            self.destroy()
            messagebox.showinfo("Plot", "There is no numeric data to plot.",
                                parent=master)
            return

        self._init_axes(plot_cfg)
        self.refresh_legend()
        self._connect_events()
        self.draw()

    # -- construction ------------------------------------------------------
    def _build_widgets(self):
        if self.app is not None:
            # the same menu bar as the spreadsheet window, plus this
            # diagram's own commands in the Plot menu
            self.app.build_menubar(self, plot=self)
        else:                       # stand-alone window without the App
            menubar = tk.Menu(self, tearoff=0)
            plot_menu = tk.Menu(menubar, tearoff=0)
            plot_menu.add_command(label="Axes properties...",
                                  command=lambda: self.open_axes_dialog("x"))
            plot_menu.add_command(label="Frame and origin...",
                                  command=lambda: self.open_axes_dialog("frame"))
            plot_menu.add_command(label="Title and fonts...",
                                  command=self.open_title_dialog)
            plot_menu.add_separator()
            plot_menu.add_command(label="Close", command=self.destroy)
            menubar.add_cascade(label="Plot", menu=plot_menu)
            self.configure(menu=menubar)

        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        toolbar = NavigationToolbar2Tk(self.canvas, self, pack_toolbar=False)
        toolbar.update()
        toolbar.pack(side="top", fill="x")
        self.canvas.get_tk_widget().pack(side="top", fill="both", expand=True)
        ttk.Label(self, text=self.HINT, anchor="center", justify="center",
                  padding=4, foreground="#444").pack(side="bottom", fill="x")

    @staticmethod
    def _series_data(df, x_col, y_col):
        """Numeric X/Y pairs of one column, empty cells dropped."""
        data = pd.DataFrame({
            "x": pd.to_numeric(df[x_col], errors="coerce"),
            "y": pd.to_numeric(df[y_col], errors="coerce"),
        }).dropna()
        return data["x"].to_numpy(), data["y"].to_numpy()

    def _create_line(self, x, y, y_col, x_col):
        """New curve drawn with the defaults of the configuration file."""
        plot_cfg = self.settings.section("plot")
        line, = self.ax.plot(
            x, y,
            linestyle=code_of(LINE_STYLES, plot_cfg["line_style"], "-"),
            linewidth=float(plot_cfg["line_width"]),
            marker=code_of(MARKERS, plot_cfg["marker"], "o"),
            markersize=float(plot_cfg["marker_size"]),
            markeredgewidth=float(plot_cfg["marker_edge_width"]),
            label=str(y_col))          # the column name is the legend text
        if plot_cfg["hollow_markers"]:
            line.set_markerfacecolor("none")
            line.set_markeredgecolor(line.get_color())
        line.set_picker(True)
        line.set_pickradius(6)
        line.aplot_series = str(y_col)  # used to detect custom legend texts
        self.lines.append(line)
        self.series[y_col] = line
        self.fill_state.setdefault(y_col, self.default_fill_state(plot_cfg))
        self.refresh_fill(y_col)
        return line

    # -- filled area under a curve -----------------------------------------
    @staticmethod
    def default_fill_state(plot_cfg):
        return {
            "on": bool(plot_cfg.get("fill_under", False)),
            "follow": bool(plot_cfg.get("fill_follows_line", True)),
            "color": safe_hex(plot_cfg.get("fill_color"), PALETTE_FALLBACK),
            "alpha": float(plot_cfg.get("fill_alpha", 0.35)),
            "hatch": code_of(HATCH_PATTERNS, plot_cfg.get("fill_pattern"), ""),
            "base": code_of(FILL_BASES, plot_cfg.get("fill_base"), "zero"),
        }

    def refresh_fill(self, column):
        """Draw (or remove) the filled area belonging to one curve."""
        old = self.fills.pop(column, None)
        if old is not None:
            try:
                old.remove()
            except (ValueError, AttributeError):
                pass
        line = self.series.get(column)
        cfg = self.fill_state.get(column)
        if line is None or not cfg or not cfg.get("on"):
            return None
        x_data, y_data = line.get_data()
        if len(x_data) == 0:
            return None

        color = line.get_color() if cfg.get("follow") else cfg["color"]
        alpha = min(1.0, max(0.0, float(cfg.get("alpha", 0.35))))
        hatch = cfg.get("hatch") or None
        base = 0.0 if cfg.get("base", "zero") == "zero" else self.ax.get_ylim()[0]
        fill = self.ax.fill_between(
            x_data, y_data, base,
            facecolor=to_rgba(color, alpha),
            edgecolor=to_rgba(color, 1.0) if hatch else "none",
            hatch=hatch, linewidth=0.0, label="_nolegend_",
            zorder=line.get_zorder() - 0.5)
        self.fills[column] = fill
        return fill

    def refresh_fills(self):
        for column in list(self.series):
            self.refresh_fill(column)

    def rename_series(self, old, new, is_x_column=False):
        """Follow a column rename in the spreadsheet.

        Legend texts and the X axis label are only changed when they still
        carry the automatic (column) name - custom texts are kept.
        """
        if is_x_column:
            if self.ax.get_xlabel() == old:
                self.ax.set_xlabel(new)
                self.ax.xaxis.label.set_picker(True)
            self.x_col = new
            self.draw()
            return
        line = self.series.get(old)
        if line is None:
            return
        # rebuild both dictionaries so that the column order is kept
        self.series = {(new if key == old else key): value
                       for key, value in self.series.items()}
        self.legend_state = {(new if key == old else key): value
                             for key, value in self.legend_state.items()}
        self.fill_state = {(new if key == old else key): value
                           for key, value in self.fill_state.items()}
        self.fills = {(new if key == old else key): value
                      for key, value in self.fills.items()}
        if line.get_label() == getattr(line, "aplot_series", None):
            line.set_label(str(new))
        line.aplot_series = str(new)
        self.refresh_legend()
        self.draw()

    def _plot_data(self, _plot_cfg=None):
        columns = list(self.df.columns)
        x_col = columns[0]
        for y_col in columns[1:]:
            x, y = self._series_data(self.df, x_col, y_col)
            if len(x):
                self._create_line(x, y, y_col, x_col)
        return len(self.lines)

    def update_data(self, df):
        """Replace the plotted values but keep every style setting.

        Curves are matched by column name: existing ones only get new data,
        a new column becomes a new curve, a deleted column disappears.
        """
        columns = list(df.columns)
        if len(columns) < 2:
            return False
        self.df = df
        x_col = columns[0]
        self.x_col = x_col

        for y_col in columns[1:]:
            x, y = self._series_data(df, x_col, y_col)
            line = self.series.get(y_col)
            if line is None:
                if len(x):
                    self._create_line(x, y, y_col, x_col)
            else:
                line.set_data(x, y)

        for y_col in [name for name in self.series if name not in columns[1:]]:
            line = self.series.pop(y_col)
            if line in self.lines:
                self.lines.remove(line)
            dialog = self._dialogs.pop(id(line), None)
            if dialog is not None and dialog.winfo_exists():
                dialog.destroy()
            fill = self.fills.pop(y_col, None)
            if fill is not None:
                fill.remove()
            self.fill_state.pop(y_col, None)
            line.remove()

        auto_x = self.axis_cfg["x"]["auto"]
        auto_y = self.axis_cfg["y"]["auto"]
        if auto_x or auto_y:  # manual ranges are left untouched
            self.ax.relim()
            self.ax.autoscale_view(scalex=auto_x, scaley=auto_y)
        self.refresh_fills()
        self.refresh_legend()
        self.draw()
        return True

    # -- saving / restoring the whole diagram ------------------------------
    def to_state(self):
        """Everything that makes this diagram look the way it looks."""
        axes = {}
        for which in ("x", "y"):
            low, high = self.current_limits(which)
            cfg = self.axis_cfg[which]
            axes[which] = {
                "label": self.axis_label(which), "auto": cfg["auto"],
                "min": float(low), "max": float(high),
                "step": cfg["step"], "minor": cfg["minor"],
                "label_size": cfg["label_size"], "tick_size": cfg["tick_size"],
                "label_color": cfg["label_color"], "tick_color": cfg["tick_color"],
                "grid": dict(cfg["grid"]),
            }
        series = []
        for y_col, line in self.series.items():
            state = self.legend_state.get(y_col) or self.default_legend_state(0)
            series.append({
                "column": str(y_col), "label": line.get_label(),
                "legend_pos": [float(state["pos"][0]), float(state["pos"][1])],
                "legend_loc": state["loc"], "legend_size": int(state["size"]),
                "legend_color": safe_hex(state.get("color", "#000000"), "#000000"),
                "legend_edge": state.get("edge", "#000000"),
                "legend_face": state.get("face", "#ffffff"),
                "fill": dict(self.fill_state.get(y_col)
                             or self.default_fill_state(self.settings.section("plot"))),
                "auto_label": line.get_label() == getattr(line, "aplot_series", None),
                "color": store_color(line.get_color()),
                "linestyle": str(line.get_linestyle()),
                "linewidth": float(line.get_linewidth()),
                "marker": str(line.get_marker()),
                "markersize": float(line.get_markersize()),
                "markerfacecolor": store_color(line.get_markerfacecolor()),
                "markeredgecolor": store_color(line.get_markeredgecolor()),
                "markeredgewidth": float(line.get_markeredgewidth()),
                "visible": bool(line.get_visible()),
            })
        return {
            "geometry": self.geometry(),
            "figure": {"width": float(self.fig.get_figwidth()),
                       "height": float(self.fig.get_figheight()),
                       "dpi": float(self.fig.get_dpi())},
            "title": {"text": self.ax.get_title(), "size": self.fonts["title"],
                      "color": safe_hex(self.fonts["title_color"], "#000000")},
            "legend": {"visible": self.legend_visible, "location": self.legend_loc,
                       "size": self.fonts["legend"],
                       "color": safe_hex(self.fonts["legend_color"], "#000000")},
            "frame": dict(self.frame_cfg),
            "axes": axes,
            "series": series,
        }

    def apply_state(self, state):
        """Rebuild the appearance stored by to_state()."""
        figure = state.get("figure") or {}
        if figure:
            self.fig.set_size_inches(figure.get("width", self.fig.get_figwidth()),
                                     figure.get("height", self.fig.get_figheight()))
            self.fig.set_dpi(figure.get("dpi", self.fig.get_dpi()))

        legend = state.get("legend") or {}
        self.legend_visible = bool(legend.get("visible", self.legend_visible))
        self.legend_loc = legend.get("location", self.legend_loc)
        self.fonts["legend"] = int(legend.get("size", self.fonts["legend"]))
        self.fonts["legend_color"] = legend.get("color", self.fonts["legend_color"])

        for index, entry in enumerate(state.get("series", [])):
            column = entry.get("column")
            line = self.series.get(column)
            if line is None:
                continue
            saved = self.default_legend_state(index)
            position = entry.get("legend_pos")
            self.legend_state[column] = {
                "pos": tuple(position) if position else saved["pos"],
                "loc": entry.get("legend_loc", saved["loc"]),
                "size": int(entry.get("legend_size", saved["size"])),
                "color": entry.get("legend_color", saved["color"]),
                "edge": entry.get("legend_edge", saved["edge"]),
                "face": entry.get("legend_face", saved["face"]),
            }
            fill = entry.get("fill")
            if fill:
                self.fill_state[column] = {
                    **self.default_fill_state(self.settings.section("plot")), **fill}
            line.set_label(entry.get("label", line.get_label()))
            line.set_color(entry.get("color", line.get_color()))
            line.set_linestyle(entry.get("linestyle", line.get_linestyle()))
            line.set_linewidth(entry.get("linewidth", line.get_linewidth()))
            line.set_marker(entry.get("marker", line.get_marker()))
            line.set_markersize(entry.get("markersize", line.get_markersize()))
            line.set_markerfacecolor(entry.get("markerfacecolor",
                                               line.get_markerfacecolor()))
            line.set_markeredgecolor(entry.get("markeredgecolor",
                                               line.get_markeredgecolor()))
            line.set_markeredgewidth(entry.get("markeredgewidth",
                                               line.get_markeredgewidth()))
            line.set_visible(entry.get("visible", True))

        for which, cfg in (state.get("axes") or {}).items():
            if which in ("x", "y"):
                self.apply_axis(which, cfg, redraw=False)

        frame = state.get("frame")
        if frame:
            self.apply_frame({**self.frame_cfg, **frame}, redraw=False)

        title = state.get("title") or {}
        self.fonts["title"] = int(title.get("size", self.fonts["title"]))
        self.fonts["title_color"] = title.get("color", self.fonts["title_color"])
        self.ax.set_title(title.get("text", self.ax.get_title()),
                          fontsize=self.fonts["title"],
                          color=safe_hex(self.fonts["title_color"], "#000000"))
        self.ax.title.set_picker(True)

        geometry = state.get("geometry")
        if geometry:
            try:
                self.geometry(geometry)
            except tk.TclError:
                pass
        self.refresh_fills()
        self.refresh_legend()
        self.draw()

    def _init_axes(self, plot_cfg):
        x_col = str(self.df.columns[0])
        try:
            title = str(plot_cfg["title_template"]).format(x=x_col)
        except (KeyError, IndexError, ValueError):
            title = str(plot_cfg["title_template"])
        self.ax.set_title(title, fontsize=self.fonts["title"],
                          color=safe_hex(self.fonts["title_color"], "#000000"))
        self.ax.set_xlabel(x_col)
        self.ax.set_ylabel(str(plot_cfg["y_label"]))
        for which in ("x", "y"):
            self.apply_axis(which, {**self.axis_cfg[which],
                                    "label": self.axis_label(which)}, redraw=False)
        self.apply_frame(self.frame_cfg, redraw=False)
        for text in (self.ax.title, self.ax.xaxis.label, self.ax.yaxis.label):
            text.set_picker(True)

    def _connect_events(self):
        self.canvas.mpl_connect("pick_event", self._on_pick)
        self.canvas.mpl_connect("button_press_event", self._on_button_press)
        self.canvas.mpl_connect("motion_notify_event", self._on_motion)
        self.canvas.mpl_connect("button_release_event", self._on_release)

    # -- drawing / legend --------------------------------------------------
    def draw(self):
        self.canvas.draw_idle()

    def default_legend_state(self, index):
        """Start position of the index-th legend box, from the chosen corner."""
        x, y, loc = LEGEND_ANCHORS.get(self.legend_loc, LEGEND_ANCHORS["best"])
        direction = -1 if y >= 0.5 else 1
        plot_cfg = self.settings.section("plot")
        edge = ("none" if not plot_cfg.get("legend_frame", True)
                else safe_hex(plot_cfg.get("legend_edge_color"), "#000000"))
        face = ("none" if plot_cfg.get("legend_transparent") else
                safe_hex(plot_cfg.get("legend_background"), "#ffffff"))
        return {"pos": (x, y + index * LEGEND_STACK_STEP * direction),
                "loc": loc, "size": int(self.fonts["legend"]),
                "color": safe_hex(self.fonts["legend_color"], "#000000"),
                "edge": edge, "face": face}

    def reset_legend_positions(self):
        """Stack the legend boxes again from the configured corner."""
        for index, y_col in enumerate(self.series):
            self.legend_state[y_col] = self.default_legend_state(index)
        self.refresh_legend()
        self.draw()

    def refresh_legend(self):
        """One legend box per curve, each at its own (movable) position."""
        for legend in self.legends.values():
            legend.remove()
        self.legends.clear()
        for y_col in [name for name in self.legend_state if name not in self.series]:
            del self.legend_state[y_col]
        if not self.legend_visible:
            return
        index = 0
        for y_col, line in self.series.items():
            label = line.get_label()
            if not label or label.startswith("_") or not line.get_visible():
                continue
            state = self.legend_state.get(y_col)
            if state is None:
                state = self.default_legend_state(index)
                self.legend_state[y_col] = state
            legend = Legend(self.ax, [line], [label], loc=state["loc"],
                            bbox_to_anchor=state["pos"],
                            bbox_transform=self.ax.transAxes,
                            prop={"size": state["size"]}, framealpha=1.0)
            for text in legend.get_texts():
                text.set_color(state.get("color", "#000000"))
            box = legend.get_frame()            # surrounding box of this legend
            edge = state.get("edge", "#000000")
            face = state.get("face", "#ffffff")
            box.set_edgecolor("none" if edge == "none" else edge)
            box.set_linewidth(0.0 if edge == "none" else 0.8)
            box.set_facecolor("none" if face == "none" else face)
            self.ax.add_artist(legend)
            self.legends[y_col] = legend
            index += 1

    # -- legend hit testing / dragging -------------------------------------
    def _renderer(self):
        try:
            return self.canvas.get_renderer()
        except AttributeError:
            return None

    def legend_at(self, x, y):
        """(column, legend) of the legend box under the pointer."""
        if x is None or y is None:
            return None, None
        renderer = self._renderer()
        for y_col, legend in self.legends.items():
            try:
                box = legend.get_window_extent(renderer)
            except (RuntimeError, ValueError, AttributeError):
                continue
            if box.contains(x, y):
                return y_col, legend
        return None, None

    def _legend_text_hit(self, legend, x, y):
        renderer = self._renderer()
        for text in legend.get_texts():
            try:
                box = text.get_window_extent(renderer)
            except (RuntimeError, ValueError, AttributeError):
                continue
            if box.expanded(1.25, 1.6).contains(x, y):
                return True
        return False

    def _axes_point(self, event):
        return tuple(self.ax.transAxes.inverted().transform((event.x, event.y)))

    def _start_legend_drag(self, y_col, event):
        pos = self.legend_state[y_col]["pos"]
        point = self._axes_point(event)
        self._drag = {"column": y_col,
                      "dx": pos[0] - point[0], "dy": pos[1] - point[1]}

    def _on_motion(self, event):
        if self._drag is None:
            self._update_cursor(event)
            return
        if event.x is None or event.y is None:
            return
        y_col = self._drag["column"]
        legend = self.legends.get(y_col)
        if legend is None:
            self._drag = None
            return
        point = self._axes_point(event)
        pos = (point[0] + self._drag["dx"], point[1] + self._drag["dy"])
        self.legend_state[y_col]["pos"] = pos
        legend.set_bbox_to_anchor(pos, transform=self.ax.transAxes)
        self.draw()

    def _on_release(self, _event):
        self._drag = None

    def _update_cursor(self, event):
        cursor = ""
        _y_col, legend = self.legend_at(event.x, event.y)
        if legend is not None:
            cursor = ("xterm" if self._legend_text_hit(legend, event.x, event.y)
                      else "fleur")
        elif self.frame_hit(event.x, event.y):
            cursor = "hand2"
        if cursor != self._cursor:
            self._cursor = cursor
            try:
                self.canvas.get_tk_widget().configure(cursor=cursor)
            except tk.TclError:
                pass

    # -- axis helpers ------------------------------------------------------
    def axis_label(self, which):
        return self.ax.get_xlabel() if which == "x" else self.ax.get_ylabel()

    def current_limits(self, which):
        return self.ax.get_xlim() if which == "x" else self.ax.get_ylim()

    # -- frame and axes geometry -------------------------------------------
    @staticmethod
    def check_frame(cfg):
        """Returns an error message when the geometry is not usable."""
        if cfg["x_length"] <= 0.02 or cfg["y_length"] <= 0.02:
            return "The width and the height of the axes must be positive."
        if cfg["left"] < 0 or cfg["bottom"] < 0:
            return "The distances from the edges cannot be negative."
        if cfg["left"] + cfg["x_length"] > 1.001:
            return ("The width plus the distance from the left is larger than "
                    "the window.")
        if cfg["bottom"] + cfg["y_length"] > 1.001:
            return ("The height plus the distance from the bottom is larger "
                    "than the window.")
        return None

    def apply_frame(self, cfg, redraw=True):
        """Frame style, thickness, colour and the size/origin of the axes."""
        style = cfg.get("style", "box")
        width = float(cfg.get("width", 1.0))
        color = cfg.get("color", "#000000")
        major_length = max(0.0, to_float(cfg.get("major_tick_length"), 3.5))
        minor_length = max(0.0, to_float(cfg.get("minor_tick_length"), 2.0))
        closed = style != "none"

        for name, spine in self.ax.spines.items():
            spine.set_visible(closed or name in ("left", "bottom"))
            spine.set_linewidth(width)
            spine.set_color(color)
            spine.set_picker(6)          # clicking the frame opens this dialog

        self.ax.tick_params(
            which="both", color=color, width=width,
            top=(style == "box_in" or style == "box_out"),
            right=(style == "box_in" or style == "box_out"),
            direction="in" if style == "box_in" else "out")
        self.ax.tick_params(which="major", length=major_length)
        self.ax.tick_params(which="minor", length=minor_length)

        background = cfg.get("background", "#ffffff")
        figure_background = cfg.get("figure_background", "#ffffff")
        self.ax.set_facecolor("none" if background == "none" else background)
        self.fig.set_facecolor("none" if figure_background == "none"
                               else figure_background)

        self.ax.set_position([cfg["left"], cfg["bottom"],
                              cfg["x_length"], cfg["y_length"]])
        self.frame_cfg = {"style": style, "width": width, "color": color,
                          "major_tick_length": major_length,
                          "minor_tick_length": minor_length,
                          "background": background,
                          "figure_background": figure_background,
                          "left": float(cfg["left"]), "bottom": float(cfg["bottom"]),
                          "x_length": float(cfg["x_length"]),
                          "y_length": float(cfg["y_length"])}
        if redraw:
            self.draw()

    def apply_axis(self, which, cfg, redraw=True):
        """Range / ticks / minor ticks / grid / fonts of one axis."""
        ax = self.ax
        axis = ax.xaxis if which == "x" else ax.yaxis

        if "label" in cfg:
            (ax.set_xlabel if which == "x" else ax.set_ylabel)(cfg["label"])
        label_size = int(cfg.get("label_size", self.fonts["axis_label"]))
        tick_size = int(cfg.get("tick_size", self.fonts["tick_label"]))
        # font colours: 'labelcolor' is the text of the numbers, while the
        # colour of the tick marks themselves belongs to the frame
        label_color = safe_hex(cfg.get("label_color",
                                       self.fonts["axis_label_color"]), "#000000")
        tick_color = safe_hex(cfg.get("tick_color",
                                      self.fonts["tick_label_color"]), "#000000")
        axis.label.set_fontsize(label_size)
        axis.label.set_color(label_color)
        axis.label.set_picker(True)
        ax.tick_params(axis=which, which="both", labelsize=tick_size,
                       labelcolor=tick_color)

        if cfg["auto"]:
            axis.set_major_locator(AutoLocator())
            ax.autoscale(enable=True, axis=which)
            ax.relim()
            ax.autoscale_view()
        else:
            now_low, now_high = self.current_limits(which)
            low = cfg.get("min") if cfg.get("min") is not None else now_low
            high = cfg.get("max") if cfg.get("max") is not None else now_high
            low, high = sorted((low, high))
            (ax.set_xlim if which == "x" else ax.set_ylim)(low, high)
            step = cfg.get("step")
            if step and step > 0:
                count = int(round((high - low) / step)) + 1
                if 1 < count <= 1000:
                    axis.set_major_locator(FixedLocator(low + step * np.arange(count)))
                else:
                    axis.set_major_locator(MultipleLocator(step))
            else:
                axis.set_major_locator(AutoLocator())

        minor = max(0, int(cfg.get("minor", 0)))
        axis.set_minor_locator(AutoMinorLocator(minor + 1) if minor else NullLocator())

        grid = cfg.get("grid", self.axis_cfg[which]["grid"])
        if grid["major"]:
            ax.grid(True, which="major", axis=which, color=grid["color"],
                    linestyle=grid["style"], linewidth=grid["width"])
        else:
            ax.grid(False, which="major", axis=which)
        if grid["minor"] and minor:
            ax.grid(True, which="minor", axis=which, color=grid["color"],
                    linestyle=grid["style"], linewidth=max(0.3, grid["width"] * 0.6))
        else:
            ax.grid(False, which="minor", axis=which)

        self.axis_cfg[which] = {
            "auto": cfg["auto"], "step": cfg.get("step"), "minor": minor,
            "label_size": label_size, "tick_size": tick_size,
            "label_color": label_color, "tick_color": tick_color,
            "grid": dict(grid),
        }
        if which == "y":   # fills reaching the bottom follow the new range
            for column, fill_cfg in self.fill_state.items():
                if fill_cfg.get("on") and fill_cfg.get("base") == "bottom":
                    self.refresh_fill(column)
        if redraw:
            self.draw()

    # -- events ------------------------------------------------------------
    def _on_pick(self, event):
        mouse = event.mouseevent
        if getattr(mouse, "dblclick", False):
            return  # double click belongs to the axes dialog
        if self.legend_at(mouse.x, mouse.y)[1] is not None:
            return  # the legend boxes are handled by the press handler
        artist = event.artist

        if artist in self.ax.spines.values() or self.frame_hit(mouse.x, mouse.y):
            self.open_axes_dialog("frame")
        elif artist is self.ax.title:
            self.edit_title()
        elif artist is self.ax.xaxis.label:
            self.edit_axis_label("x")
        elif artist is self.ax.yaxis.label:
            self.edit_axis_label("y")
        elif isinstance(artist, Line2D) and artist in self.lines:
            self.open_series_dialog(artist)

    def _on_button_press(self, event):
        if event.dblclick:
            which = self._axis_hit(event)
            if which:
                self.open_axes_dialog(which)
            return
        if event.button != 1:
            return
        y_col, legend = self.legend_at(event.x, event.y)
        if legend is None:
            if self.frame_hit(event.x, event.y):
                # a click on any side of the frame: frame and origin settings
                self.after(1, lambda: self.open_axes_dialog("frame"))
            return
        if self._legend_text_hit(legend, event.x, event.y):
            # clicking the text edits it; the frame around it moves the box
            self.after(1, lambda column=y_col: self.edit_legend_entry(column))
            return
        self._start_legend_drag(y_col, event)

    def frame_hit(self, x, y):
        """True when the pointer is on one of the visible frame sides."""
        if x is None or y is None:
            return False
        box = self.ax.get_window_extent()
        tolerance = max(4.0, self.frame_cfg["width"] + 3.0)
        vertical = box.y0 - tolerance <= y <= box.y1 + tolerance
        horizontal = box.x0 - tolerance <= x <= box.x1 + tolerance
        sides = {"left": horizontal and vertical and abs(x - box.x0) <= tolerance,
                 "right": horizontal and vertical and abs(x - box.x1) <= tolerance,
                 "bottom": horizontal and vertical and abs(y - box.y0) <= tolerance,
                 "top": horizontal and vertical and abs(y - box.y1) <= tolerance}
        return any(hit and self.ax.spines[name].get_visible()
                   for name, hit in sides.items())

    def _axis_hit(self, event):
        """Which axis region (tick labels / axis label) was clicked?"""
        if event.x is None or event.y is None:
            return None
        box = self.ax.get_window_extent()
        if box.x0 <= event.x <= box.x1 and box.y0 - 80 <= event.y < box.y0:
            return "x"
        if box.y0 <= event.y <= box.y1 and box.x0 - 90 <= event.x < box.x0:
            return "y"
        return None

    # -- dialogs -----------------------------------------------------------
    def _show_dialog(self, key, factory):
        existing = self._dialogs.get(key)
        if existing is not None and existing.winfo_exists():
            existing.lift()
            existing.focus_force()
            return existing
        dialog = factory()
        self._dialogs[key] = dialog
        return dialog

    def open_series_dialog(self, line):
        column = getattr(line, "aplot_series", None)
        state = self.legend_state.get(column) or {}

        def set_legend_style(size, color):
            if column in self.legend_state:
                self.legend_state[column]["size"] = size
                self.legend_state[column]["color"] = color

        def set_fill(values):
            if column is not None:
                self.fill_state[column] = values
                self.refresh_fill(column)

        return self._show_dialog(id(line), lambda: SeriesStyleDialog(
            self, line,
            on_change=lambda: (self.refresh_legend(), self.draw()),
            on_close=lambda _d: self._dialogs.pop(id(line), None),
            legend_size=state.get("size", self.fonts["legend"]),
            legend_color=state.get("color", self.fonts["legend_color"]),
            on_legend_style=set_legend_style,
            fill=self.fill_state.get(column),
            on_fill=set_fill))

    def open_axes_dialog(self, which="x"):
        existing = self._dialogs.get("axes")
        if existing is not None and existing.winfo_exists():
            existing.select_tab(which)      # jump to the requested tab
            existing.lift()
            existing.focus_force()
            return existing
        return self._show_dialog("axes", lambda: AxesDialog(
            self, self, which, on_close=lambda _d: self._dialogs.pop("axes", None)))

    def open_title_dialog(self):
        return self._show_dialog("title", lambda: TitleFontDialog(
            self, self, on_close=lambda _d: self._dialogs.pop("title", None)))

    def edit_title(self):
        def apply(text, size, color):
            self.fonts["title"] = size
            self.fonts["title_color"] = color
            self.ax.set_title(text, fontsize=size, color=color)
            self.ax.title.set_picker(True)
            self.draw()

        return self._show_dialog("title-text", lambda: TextStyleDialog(
            self, "Plot title", self.ax.get_title(), self.fonts["title"], apply,
            color=safe_hex(self.fonts["title_color"], "#000000"),
            on_close=lambda _d: self._dialogs.pop("title-text", None)))

    def edit_axis_label(self, which):
        def apply(text, size, color):
            cfg = dict(self.axis_cfg[which])
            cfg.update({"label": text, "label_size": size, "label_color": color})
            self.apply_axis(which, cfg)

        return self._show_dialog(f"label-{which}", lambda: TextStyleDialog(
            self, f"{which.upper()} axis label", self.axis_label(which),
            self.axis_cfg[which]["label_size"], apply,
            color=self.axis_cfg[which]["label_color"],
            hint="The colour of the numbers is on the axis tab of the\n"
                 "axes properties dialog.",
            on_close=lambda _d: self._dialogs.pop(f"label-{which}", None)))

    def edit_legend_entry(self, column):
        line = self.series.get(column)
        if line is None:
            return None
        state = self.legend_state.setdefault(column, self.default_legend_state(0))

        def apply(values):
            text = values.pop("text", "").strip()
            line.set_label(text if text else "_nolegend_")
            state.update(values)
            self.refresh_legend()
            self.draw()

        return self._show_dialog(f"legend-{column}", lambda: LegendDialog(
            self, column, line.get_label(), state, apply,
            on_close=lambda _d: self._dialogs.pop(f"legend-{column}", None)))


# --------------------------------------------------------------------------
# documentation
# --------------------------------------------------------------------------

DOCUMENTATION = """\
# APlot - Data Visualizer

APlot is a small desktop program for typing or loading tabular data and
turning it into a Matplotlib diagram whose every detail can be changed by
clicking on it.  It is a single Python file and needs only `tkinter`,
`pandas`, `numpy` and `matplotlib`.

Start it with:

    python3 aplot.py


## 0. The name

APlot may mean AlphaPlot or AdvancedPlot or AgilePlot or ArticulatePlot
and maybe some other word composition can be looked for.  This software
is an easy to use start (alpha) to create good looking (articulate)
scientific (advanced) plots quickly (agile).


## 1. The spreadsheet window

The main window holds the data table.  The first column is always the
independent variable (the X axis); every further column is drawn as a
separate curve.

### Toolbar

| Button | What it does |
| --- | --- |
| Plot | Opens a NEW diagram from the current data, with the default style. |
| Update plot | Sends the current data to the diagrams that are already open, keeping every style setting. |
| Add row | Appends an empty row and starts editing it. |
| Delete row | Deletes the selected row. |
| Add column | Asks for a name and appends an empty column. |
| Delete column | Deletes the column you last clicked in (after a confirmation). |
| Random data | Fills the table with random numbers, keeping its present size. |
| Settings... | Opens the settings editor (see section 4). |

### Editing cells

* Click a cell to edit it.  The text is selected, so typing replaces it.
* `Enter` or `Down` moves one row down, `Up` one row up.
* `Tab` moves right, `Shift+Tab` moves left; at the end of a row the cursor
  wraps to the beginning of the next one.
* Leaving the last row appends a new row automatically, so the table grows
  as long as you keep typing.  This can be switched off in the settings.
* `Left` and `Right` move the text cursor inside the cell, and step to the
  neighbouring cell once the cursor has reached the end of the text (at the
  end of a row they wrap to the next one, exactly like `Tab`).
* `Ctrl`, `Cmd` or `Alt` together with any arrow key always jumps to the
  neighbouring cell, whatever the text cursor is doing.
* `Esc` cancels the edit and keeps the previous value.
* Text can be selected with the mouse, with `Shift+Left/Right` and with
  `Shift+Up/Down` (to the beginning / end of the cell).  `Ctrl+A` (`Cmd+A`
  on macOS) selects everything, `Ctrl+C` (`Cmd+C`) copies it.
* Pressing `Ctrl+C` / `Cmd+C` while a row is selected copies the whole row
  as tab separated text, ready to be pasted into another program.

Values that look like numbers are stored as numbers; everything else is
kept as text and is ignored when plotting.

### Column names

Click a column heading to edit its name.  The name is used

* as the legend text of that curve, and
* for the first column, as the label of the X axis.

Renaming a column later also renames the legend entry and the X axis label
of every open diagram - unless you gave them your own text, which is never
overwritten.


## 2. The diagram window

Every curve, label and axis reacts to the mouse.

| Action | Result |
| --- | --- |
| Click a curve | Curve properties: line and marker settings separately. |
| Click the title | Its text, font size and font colour. |
| Click an axis label | Its text, font size and font colour. |
| Click the text of a legend box | Its text, font size and font colour (an empty text hides that box). |
| Drag the frame of a legend box | Moves that legend box anywhere on the diagram. |
| Click the frame (any axis line) | Frame and origin settings. |
| Double-click beside an axis (on the numbers or the label) | Axes properties, opened on the tab of that axis. |
| Plot menu | The axes dialog (axes, frame and origin) and the title/fonts dialog, plus closing this diagram. |
| Toolbar | The standard Matplotlib toolbar: pan, zoom, and saving the figure as an image. |

### Legend boxes

Every curve has its **own** legend box, so they can be placed
independently.

* Grab a box anywhere on its frame - that is, next to the sample line, not
  on the text - and drag it to a new place.  The pointer turns into a move
  cross over the frame and into a text cursor over the text.
* Click the text of a box to open its own dialog: the text, the font size
  and the font colour, the **frame** around the box (its colour, or no
  frame at all) and the **background** (its colour, or fully transparent).
  An empty text hides the box.
* The boxes keep their position when the data is updated, when the curve
  style changes and when a column is renamed, and they are stored in
  `.aplt` files.
* `Plot > Title and fonts...` sets one font size for every box, the corner
  where new boxes start, and can stack all boxes again with
  `Reset positions`.

### Curve properties

* **Legend**: the text of this curve's legend box with its font size and
  font colour.  An empty text removes the box.
* **Line**: style (solid, dashed, dash-dot, dotted, none), width, colour.
* **Marker**: style (13 shapes plus "None"), size, fill colour, "Hollow"
  (unfilled marker), edge colour, edge width.
* **Fill under the curve**: fills the area between the curve and the zero
  line (or the bottom of the axes).  The fill takes the colour of the curve
  or an own colour, has an adjustable opacity, and can carry a **pattern**
  (diagonal, vertical, horizontal, crossed, circles, dots, stars and their
  dense variants).  The pattern is drawn in the full colour over the
  semi-transparent area, so both stay visible.
* **Marker colour = line colour** copies the line colour into both marker
  colours.

The line and the marker are independent: a red line with green markers is
perfectly possible.  The legend always mirrors what the curve looks like.

### Axes properties

One window with an **X axis**, a **Y axis** and a **Frame and origin** tab.
The two axis tabs have:

* **Axis label and fonts**: the label text, the font size and font colour
  of the label, and the font size and font colour of the numbers (ticks).
  The colour of the tick *marks* is not set here - it belongs to the frame,
  so a black frame can carry grey numbers.
* **Range and ticks**: automatic range, or an explicit `From`, `To` and
  `Step` for the major ticks, plus the number of minor ticks between two
  major ticks.
* **Grid of this axis**: major and minor grid lines with their own colour,
  style and width.

### Frame and origin

The third tab of the axes dialog, also reachable with
`Plot > Frame and origin...`.

**Frame**

* **Style**:
  * `No frame (X and Y only) (default)` - only the left and the bottom side
    are drawn, there is no top X axis and no right Y axis,
  * `Full frame` - all four sides, ticks on the bottom and on the left, as
    matplotlib draws it by default,
  * `Frame with ticks (inward)` - all four sides with ticks on every side,
    pointing into the diagram,
  * `Frame with ticks (outward)` - all four sides with ticks on every side,
    pointing outwards.
* **Thickness** and **Colour** of the frame; the tick marks follow them, so
  the whole frame stays consistent.
* **Major tick length** and **Minor tick length** in points.  Zero hides
  that kind of tick mark.

**Background**

* **Plot area**: the colour behind the curves, or **Transparent plot area**
  to let the colour around the axes show through (a transparent plot area
  is also saved transparently into a PNG).
* **Around the axes**: the colour of the rest of the window.

Clicking any side of the frame on the diagram (the X axis line, the Y axis
line, or the top and right sides when they are drawn) opens this dialog;
the pointer becomes a hand over the frame.

### The menu bar of the diagram window

A diagram window carries the same menu bar as the spreadsheet window
(`APlot`, `File`, `Plot`, `Help`), so files can be opened and saved and the
settings and the documentation can be reached without going back to the
main window.  This matters on macOS, where the menu bar always belongs to
the window that has the focus.  In a diagram window the `Plot` menu holds
the commands of that diagram after a separator: `Axes properties...`,
`Frame and origin...`, `Title and fonts...` and `Close this diagram`.

**Size and origin of the axes**

* **Units**: `Fraction of window`, `cm` or `inch`.  Fractions are kept when
  the window is resized; the centimetre and inch values are converted with
  the current window size, and the line under the fields always shows the
  present size in centimetres.
* **Width (length of the X axis)** and **Height (length of the Y axis)**.
* **Y axis distance from the left** and **X axis distance from the bottom**
  - the position of the origin inside the window.
* **Default layout** puts back matplotlib's own margins.

The four numbers are the same values as `left`, `bottom`, `width` and
`height` of a matplotlib axes, so `left + width` and `bottom + height` must
stay inside the window; the dialog says so if they do not.

`Apply` applies all three tabs, `OK` applies them and closes the window.

### Title and fonts

Font **size** and font **colour** can be set in three places, always
together:

* the **title**: click it on the diagram, or use
  `Plot > Title and fonts...`,
* the **axis labels** and the **axis numbers**: click the label (label text,
  size and colour), or use the matching tab of the axes dialog (label and
  numbers, size and colour),
* the **legend boxes**: click the text of a box for that box alone, the
  curve properties dialog for the same box, or
  `Plot > Title and fonts...` for all of them at once.

`Plot > Title and fonts...` also switches the legend boxes on and off,
chooses the corner where they start, and puts them back into a stack.

The starting colours of all four (title, axis labels, axis numbers, legend)
come from the `Fonts` tab of the settings.


## 3. Files

| Menu item | Format |
| --- | --- |
| Open data file (CSV, TXT, DAT) | Reads a text data file into the table; the separator is recognised automatically. |
| Save data file | Writes the table into a text data file. |
| Open graph (.aplt) | Loads a complete APlot document: the data and the diagrams. |
| Save graph (.aplt) | Saves the data together with every diagram that is open. |

An `.aplt` file is a readable JSON document.  Besides the table it stores,
for each open diagram:

* the curves with their colour, line style and width, marker type, size,
  fill and edge colour, edge width, visibility, legend text, the position,
  corner, font, frame and background of their own legend box, and the
  settings of the filled area under the curve,
* the title with its font size and colour, and the visibility, starting
  corner, default font size and colour of the legend boxes,
* both axes: label, the size and colour of the label and of the numbers,
  automatic or fixed range, step, number of minor ticks, and the grid
  settings of the axis,
* the frame: style, thickness, colour, major and minor tick length, the
  background of the plot area and of the window, and the size and origin of
  the axes inside the window,
* the figure size, resolution and the window geometry.

Loading an `.aplt` file replaces the table and closes the diagrams that are
open, then reopens the saved ones exactly as they were saved.

### Data files with any separator

`Open data file` reads `.csv`, `.txt`, `.dat`, `.tsv` and `.asc` files (and
anything else, with `All files`).  Nothing has to be prepared by hand:

* the **separator** is recognised from the first lines of the file, in this
  order: tabulator, semicolon, `|`, comma, then one or more spaces.  It is
  accepted when it gives the same number of values in most of the lines, so
  a `;` separated file lands in as many columns as it has values;
* the **decimal sign** is recognised too: numbers written as `1,5` (with no
  dotted numbers in the file) are read as decimal comma, and then the comma
  is never taken for a separator;
* **comment and header lines** at the top starting with `#`, `%`, `!` or
  `//` are skipped, and empty lines are ignored everywhere;
* the **column names** come from the first line when it is not numeric;
  otherwise the columns are named `X`, `Y1`, `Y2`, ... automatically;
* **UTF-8** and Latin-1 files are both read, and a line with a wrong number
  of values is left out with a warning instead of stopping the reading.

The title bar of the spreadsheet window shows the file name together with
what was recognised, for example
`APlot - Meas057_Acquisition_Spectrum.csv  [semicolon separated, decimal
'.', 1296 rows x 3 columns]`.

If a file is unusual, the recognition can be overridden in the settings:
`Field separator` accepts `auto`, `comma`, `semicolon`, `tab`, `space` or
`|`, and `Decimal sign` accepts `auto`, `.` or `,`.  These settings are also
used when a data file is written.


## 4. Settings

`Settings...` on the toolbar, in the `APlot` menu, or `Cmd+,` in the
application menu on macOS.  The values are written to

    ~/.aplot/config.json

and are read again at every start.  `Restore defaults` puts back the
built-in values.

| Tab | Contents |
| --- | --- |
| Windows | Start size of the main window and of the diagram windows. |
| Spreadsheet | Number of rows and column names at start, column width, font size, automatic row adding. |
| Plot | Figure size and resolution, the title pattern (`{x}` is the name of the X column), default Y label, default line style and width, default marker, size and edge width, hollow markers, legend visibility, starting corner, frame and background of the legend boxes, and the default fill under the curves (colour, opacity, pattern, baseline). |
| Fonts | Size and colour of the title, the axis labels, the axis numbers and the legend boxes. |
| Grid | Default grid: major and minor lines, colour, style, width, number of minor ticks. |
| Frame | Default frame style, thickness, colour, tick lengths, background colours, and the default size and origin of the axes (as fractions of the window). |
| Data files | Field separator and decimal sign of text data files (`auto` recognises them). |

Window sizes and plot defaults are used by windows opened after saving;
diagrams that are already open keep their settings.


## 5. Typical workflow

1. `Random data`, `Open data file` or type the numbers by hand.
2. Rename the columns by clicking their headings - these names become the
   legend texts and the X axis label.
3. `Plot`.
4. Click the curves, the labels and the axes until the diagram looks right,
   and drag the legend boxes where they do not cover the data.
5. Correct or extend the data in the table and press `Update plot`; the
   diagram keeps its appearance and only the values change.
6. `Save graph (.aplt)` to be able to continue later, or the save button of
   the Matplotlib toolbar to export a PNG/PDF image.


## 6. Notes

* On macOS the first (bold) menu is named after the running program.  APlot
  renames it to "APlot" through the Cocoa bundle information, which needs
  pyobjc: `pip install pyobjc-framework-Cocoa`.  Without it the menu keeps
  the name of the Python interpreter; everything else works the same way.
* Empty cells and cells that do not contain a number are simply left out of
  the curve.
* A curve whose line style AND marker are both "None" is invisible and can
  no longer be clicked; reach it again through its legend box.
* A legend box can be dragged outside the axes area (for example beside the
  diagram); `Reset positions` brings every box back.
"""


def load_documentation():
    """The README next to the program if it exists, otherwise the built-in text."""
    try:
        readme = Path(__file__).with_name("README.md")
        if readme.is_file():
            return readme.read_text(encoding="utf-8")
    except (OSError, NameError):
        pass
    return DOCUMENTATION


class HelpWindow(tk.Toplevel):
    """Read-only documentation viewer."""

    def __init__(self, master, text):
        super().__init__(master)
        self.title(f"{APP_NAME} documentation")
        self.geometry("820x640")
        frame = ttk.Frame(self, padding=8)
        frame.pack(fill="both", expand=True)

        widget = tk.Text(frame, wrap="word", padx=12, pady=10,
                         font=("TkFixedFont", 11), borderwidth=0)
        scroll = ttk.Scrollbar(frame, orient="vertical", command=widget.yview)
        widget.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        widget.pack(side="left", fill="both", expand=True)

        widget.insert("1.0", text)
        widget.configure(state="disabled")
        self.text = widget

        ttk.Button(self, text="Close", command=self.destroy).pack(pady=(0, 8))
        self.bind("<Escape>", lambda _e: self.destroy())


# --------------------------------------------------------------------------
# main application
# --------------------------------------------------------------------------

class App:
    def __init__(self, root, config: Config | None = None):
        self.root = root
        self.settings = config or Config()
        self.root.title(f"{APP_NAME} - Data Visualizer")
        self.root.geometry(f"{self.settings.get('window', 'main_width')}x"
                           f"{self.settings.get('window', 'main_height')}")
        self.root.wm_iconname(APP_NAME)
        self.plot_windows: list[PlotWindow] = []
        self._help_window = None

        self._build_toolbar()
        self.table = DataTable(self.root, self.settings,
                               on_rename=self._column_renamed)
        self.table.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.table.set_dataframe(self._empty_frame())

        self._build_menu()
        self.root.after_idle(self._focus)

    # -- helpers -----------------------------------------------------------
    def _empty_frame(self):
        rows = max(1, int(self.settings.get("table", "rows")))
        columns = [name.strip() for name
                   in str(self.settings.get("table", "columns")).split(",")
                   if name.strip()] or ["X", "Y1"]
        return pd.DataFrame({col: [""] * rows for col in columns})

    @property
    def df(self):
        return self.table.df

    def _focus(self):
        self.root.lift()
        self.root.attributes("-topmost", True)
        self.root.attributes("-topmost", False)
        self.root.focus_force()

    # -- user interface ----------------------------------------------------
    def _build_toolbar(self):
        bar = ttk.Frame(self.root, padding=(10, 8))
        bar.pack(fill="x")
        ttk.Button(bar, text="Plot", command=self.open_plot).pack(side="left")
        ttk.Button(bar, text="Update plot", command=self.update_plot).pack(
            side="left", padx=(6, 0))
        ttk.Separator(bar, orient="vertical").pack(side="left", fill="y", padx=8)
        ttk.Button(bar, text="Add row", command=self.add_row).pack(side="left")
        ttk.Button(bar, text="Delete row", command=self.delete_row).pack(side="left", padx=(6, 0))
        ttk.Button(bar, text="Add column", command=self.add_column).pack(side="left", padx=(6, 0))
        ttk.Button(bar, text="Delete column", command=self.delete_column).pack(side="left", padx=(6, 0))
        ttk.Separator(bar, orient="vertical").pack(side="left", fill="y", padx=8)
        ttk.Button(bar, text="Random data", command=self.random_csv).pack(side="left")
        ttk.Button(bar, text="Settings...", command=self.open_settings).pack(side="right")

    def _build_menu(self):
        self.build_menubar(self.root)

    def build_menubar(self, window, plot=None):
        """The application menu bar, attached to `window`.

        Every window gets its own copy with the same items, because on macOS
        the menu bar belongs to the window that has the focus.  For a diagram
        window the Plot menu carries that diagram's own commands as well.
        """
        menubar = tk.Menu(window, tearoff=0)

        if sys.platform == "darwin":
            # the bold application menu: About + Settings (Cmd+,) live there,
            # so no separate APlot cascade is added on macOS
            apple = tk.Menu(menubar, name="apple", tearoff=0)
            apple.add_command(label=f"About {APP_NAME}", command=self.show_about)
            apple.add_separator()
            menubar.add_cascade(menu=apple)
            try:  # interpreter wide, so only the first window registers it
                self.root.createcommand("tk::mac::ShowPreferences", self.open_settings)
            except tk.TclError:
                pass
        else:
            app_menu = tk.Menu(menubar, tearoff=0)
            app_menu.add_command(label="Settings...", command=self.open_settings)
            app_menu.add_command(label=f"About {APP_NAME}", command=self.show_about)
            app_menu.add_separator()
            app_menu.add_command(label="Quit", command=self.root.quit)
            menubar.add_cascade(label=APP_NAME, menu=app_menu)

        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Open data file (CSV, TXT, DAT)",
                              command=self.load_csv)
        file_menu.add_command(label="Save data file", command=self.save_csv)
        file_menu.add_separator()
        file_menu.add_command(label=f"Open graph ({PROJECT_SUFFIX})",
                              command=self.load_project)
        file_menu.add_command(label=f"Save graph ({PROJECT_SUFFIX})",
                              command=self.save_project)
        file_menu.add_separator()
        file_menu.add_command(label="Random data", command=self.random_csv)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        menubar.add_cascade(label="File", menu=file_menu)

        plot_menu = tk.Menu(menubar, tearoff=0)
        plot_menu.add_command(label="Open diagram", command=self.open_plot)
        plot_menu.add_command(label="Update diagram (keep style)",
                              command=self.update_plot)
        if plot is not None:            # commands of this diagram window
            plot_menu.add_separator()
            plot_menu.add_command(label="Axes properties...",
                                  command=lambda: plot.open_axes_dialog("x"))
            plot_menu.add_command(label="Frame and origin...",
                                  command=lambda: plot.open_axes_dialog("frame"))
            plot_menu.add_command(label="Title and fonts...",
                                  command=plot.open_title_dialog)
            plot_menu.add_separator()
            plot_menu.add_command(label="Close this diagram", command=plot.destroy)
        menubar.add_cascade(label="Plot", menu=plot_menu)

        help_menu = tk.Menu(menubar, tearoff=0, name="help")
        help_menu.add_command(label="Documentation", command=self.show_documentation)
        help_menu.add_command(label=f"About {APP_NAME}", command=self.show_about)
        menubar.add_cascade(label="Help", menu=help_menu)

        window.configure(menu=menubar)
        return menubar

    def show_documentation(self):
        if self._help_window is not None and self._help_window.winfo_exists():
            self._help_window.lift()
            self._help_window.focus_force()
            return self._help_window
        self._help_window = HelpWindow(self.root, load_documentation())
        return self._help_window

    def show_about(self):
        messagebox.showinfo(
            f"About {APP_NAME}",
            f"{APP_NAME} - Data Visualizer\n\n"
            "Spreadsheet editor and interactive Matplotlib plots.\n"
            f"Settings file: {self.settings.path}", parent=self.root)

    def open_settings(self):
        SettingsDialog(self.root, self.settings, on_saved=self._settings_saved)

    def _settings_saved(self):
        self.table.apply_config()
        self.root.geometry(f"{self.settings.get('window', 'main_width')}x"
                           f"{self.settings.get('window', 'main_height')}")
        messagebox.showinfo(
            "Settings",
            "The settings have been saved and will be used at the next start "
            "as well.\nPlot defaults apply to diagrams opened from now on.",
            parent=self.root)

    def _ask_column(self, title):
        columns = list(self.df.columns)
        if not columns:
            return None
        name = simpledialog.askstring(
            title, f"Column name ({', '.join(columns)}):",
            initialvalue=columns[-1], parent=self.root)
        if name is None:
            return None
        if name not in columns:
            messagebox.showerror("Error", f"There is no column named '{name}'.")
            return None
        return name

    # -- file I/O ----------------------------------------------------------
    def load_csv(self, path=None):
        """Open a csv / txt / dat file; the separator is detected by default."""
        if path is None:
            path = filedialog.askopenfilename(filetypes=DATA_PATTERNS)
        if not path:
            return None
        try:
            frame, info = read_table(path,
                                     separator=self.settings.get("csv", "separator"),
                                     decimal=self.settings.get("csv", "decimal"))
        except Exception as error:
            messagebox.showerror("Error", f"Could not read the file: {error}")
            return None
        if frame.empty or not len(frame.columns):
            messagebox.showerror("Error", "The file contains no usable data.")
            return None

        self.table.set_dataframe(frame)
        self.set_file_title(path, info)
        if info["bad_lines"]:
            messagebox.showwarning(
                "Data file",
                "Some lines had a different number of values and were skipped.")
        return info

    def set_file_title(self, path, info=None):
        """Show the file name (and what was detected) in the window title."""
        name = Path(path).name
        if info:
            self.root.title(f"{APP_NAME} - {name}  "
                            f"[{info['separator']} separated, "
                            f"decimal '{info['decimal']}', "
                            f"{info['rows']} rows x {info['columns']} columns]")
        else:
            self.root.title(f"{APP_NAME} - {name}")

    def save_csv(self):
        if self.df.empty:
            messagebox.showinfo("Information", "There is no data to save.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".csv",
                                            filetypes=DATA_PATTERNS)
        if not path:
            return
        separator = separator_from_setting(self.settings.get("csv", "separator"))
        if separator in (None, WHITESPACE_SEP):
            separator = "\t" if str(path).lower().endswith((".txt", ".dat")) else ","
        decimal = str(self.settings.get("csv", "decimal")).strip().lower()
        decimal = "." if decimal in ("auto", "") else decimal[0]
        try:
            self.df.to_csv(path, index=False, sep=separator, decimal=decimal)
            messagebox.showinfo("Successful", "The file has been saved.")
        except Exception as error:
            messagebox.showerror("Error", f"Could not save the file: {error}")

    # -- APlot documents (.aplt) -------------------------------------------
    def project_document(self):
        """Data plus the full state of every open diagram."""
        rows = [[value for value in row]
                for row in self.df.itertuples(index=False, name=None)]
        return {
            "format": "aplot", "version": 1, "application": APP_NAME,
            "data": {"columns": [str(name) for name in self.df.columns],
                     "rows": rows},
            "plots": [window.to_state() for window in self.open_windows()],
        }

    def save_project(self, path=None):
        self.table._commit_edit()
        if path is None:
            path = filedialog.asksaveasfilename(
                defaultextension=PROJECT_SUFFIX,
                filetypes=[(f"{APP_NAME} graph", f"*{PROJECT_SUFFIX}"),
                           ("All files", "*.*")])
        if not path:
            return None
        try:
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(self.project_document(), handle, indent=2,
                          default=json_default)
        except OSError as error:
            messagebox.showerror("Error", f"Could not save the file: {error}")
            return None
        plots = len(self.open_windows())
        messagebox.showinfo(
            "Successful",
            f"The data and {plots} diagram(s) have been saved.")
        return path

    def load_project(self, path=None):
        if path is None:
            path = filedialog.askopenfilename(
                filetypes=[(f"{APP_NAME} graph", f"*{PROJECT_SUFFIX}"),
                           ("All files", "*.*")])
        if not path:
            return False
        try:
            with open(path, "r", encoding="utf-8") as handle:
                document = json.load(handle)
        except (OSError, ValueError) as error:
            messagebox.showerror("Error", f"Could not read the file: {error}")
            return False
        if not isinstance(document, dict) or document.get("format") != "aplot":
            messagebox.showerror(
                "Error", f"This is not an {APP_NAME} ({PROJECT_SUFFIX}) file.")
            return False

        data = document.get("data") or {}
        columns = data.get("columns") or []
        rows = data.get("rows") or []
        if not columns:
            messagebox.showerror("Error", "The file contains no data.")
            return False
        frame = pd.DataFrame(rows, columns=columns)
        frame = frame.where(frame.notna(), "")   # JSON null -> empty cell
        self.table.set_dataframe(frame)

        for window in self.open_windows():   # replace the current diagrams
            window.destroy()
        self.plot_windows = []
        for state in document.get("plots") or []:
            window = PlotWindow(self.root, self.df.copy(), self.settings, app=self)
            if not window.winfo_exists():
                continue
            window.apply_state(state)
            self.plot_windows.append(window)
        return True

    def random_csv(self, low=0, high=100, rows=None, columns=None):
        """Fill the table with random values, keeping its present shape.

        Columns added by hand (Y5, Y6, ...) are filled as well; the number of
        rows also stays the same.  Only an empty table falls back to the
        defaults of the configuration file.
        """
        current = self.df
        if columns is None:
            columns = list(current.columns)
        elif isinstance(columns, int):  # number of columns instead of names
            columns = ["X"] + [f"Y{i}" for i in range(1, max(2, columns))]
        if not columns:
            columns = list(self._empty_frame().columns)

        if rows is None:
            rows = len(current)
        if not rows:
            rows = max(2, int(self.settings.get("table", "rows")))

        data = {name: (np.arange(rows) if index == 0
                       else np.random.randint(low, high, size=rows))
                for index, name in enumerate(columns)}
        self.table.set_dataframe(pd.DataFrame(data))

    # -- table operations --------------------------------------------------
    def add_row(self):
        self.table.add_row(focus=True)

    def delete_row(self):
        if not self.table.delete_row():
            messagebox.showinfo("Information", "Select a row first.")

    def add_column(self):
        name = simpledialog.askstring("Add column", "Name of the new column:",
                                      parent=self.root)
        if not name:
            return
        if not self.table.add_column(name):
            messagebox.showerror("Error", "This column already exists.")

    def _column_renamed(self, old, new, index):
        """A heading was edited: follow it in the open diagrams."""
        for window in self.open_windows():
            window.rename_series(old, new, is_x_column=(index == 0))

    def delete_column(self):
        name = self.table.current_column
        if name not in list(self.df.columns):
            name = self._ask_column("Delete column")
        if name is None:
            return
        if len(self.df.columns) <= 1:
            messagebox.showinfo("Information", "The last column cannot be deleted.")
            return
        if not messagebox.askyesno("Delete column",
                                   f"Delete the column '{name}' with its data?",
                                   parent=self.root):
            return
        self.table.current_column = None
        self.table.set_dataframe(self.df.drop(columns=[name]))

    # -- plotting ----------------------------------------------------------
    def _plottable(self):
        self.table._commit_edit()  # do not lose the cell being edited
        if self.df is None or self.df.empty or len(self.df.columns) < 2:
            messagebox.showerror(
                "Error", "At least two columns are needed (X and Y axes).")
            return False
        return True

    def open_windows(self):
        """The diagrams that are still open."""
        self.plot_windows = [window for window in self.plot_windows
                             if window.winfo_exists()]
        return self.plot_windows

    def open_plot(self):
        """Open a new diagram with the default style."""
        if not self._plottable():
            return None
        window = PlotWindow(self.root, self.df.copy(), self.settings, app=self)
        if window.winfo_exists():
            self.plot_windows.append(window)
            return window
        return None

    def update_plot(self):
        """Send the edited data to the open diagrams without touching style."""
        if not self._plottable():
            return
        windows = self.open_windows()
        if not windows:
            self.open_plot()  # nothing to update yet: open the first diagram
            return
        for window in windows:
            window.update_data(self.df.copy())
            window.lift()


def main():
    set_macos_app_name(APP_NAME)  # must run before the first Tk window
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
