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
* drawings and text boxes can be turned to any angle: drag the round
  control point above them (Shift: 15 degree steps) or type the angle in
  their property window
* one click selects any object, a second click opens its properties; a
  selected text (title, axis label, legend box, text box) is marked with a
  light blue veil, a drawing or an arrow with its control points
* a curve is the exception: one click opens its properties at once, where
  the line, the marker, the legend and the fill each have their own check
  button in front of the section name; the legend follows the curve
* everything that can be selected can be dragged with the pointer and
  moved with the arrow keys (Shift: ten pixels)
* every curve has its own legend box, with its own text, font and colours
* the "T" button of the toolbar adds a movable text box anywhere, the
  drawing tool next to it adds rectangles, triangles, circles and ellipses
  and the arrow tool adds arrows with triangle, chevron, concave or convex
  heads - all of them can be moved, resized and styled
* a selected text box, drawing or arrow can be copied and pasted with all
  of its properties (Ctrl/Cmd+C, Ctrl/Cmd+V), moved with the arrow keys
  (Shift: ten pixels) and removed with Delete
* Shift while drawing or resizing an arrow keeps it horizontal, vertical or
  at 45, 135, 225, 315 degrees
* two clicks beside an axis -> combined axes dialog (X / Y / Frame tabs) with
                              range, step, minor ticks, grid, font sizes,
                              frame style and the size/origin of the axes
* two clicks on the frame   -> the "Frame and origin" tab of that dialog
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
from matplotlib.patches import Ellipse, Polygon, Rectangle
from matplotlib.ticker import (AutoLocator, AutoMinorLocator, FixedLocator,
                               MultipleLocator, NullLocator)
from matplotlib.transforms import Affine2D

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

NOTE_KEY = "note:"          # prefix that marks a free text box while dragging

SHAPE_KINDS = [("Rectangle", "rect"), ("Triangle", "triangle"),
               ("Circle", "circle"), ("Ellipse", "ellipse")]

ARROW_HEADS = [("Triangle head", "triangle"), ("Chevron head", "chevron"),
               ("Concave head", "concave"), ("Convex head", "convex")]
# corners first, then the middle of the sides
HANDLE_COUNT = 8
ROTATE_HANDLE = 8           # the round control point above the object
ROTATE_GAP = 26.0           # pixels between the object and that point
ROTATE_SNAP = 15.0          # degrees, while Shift is held
MIN_SHAPE_SIZE = 0.01       # in axes coordinates

# copy / paste and the keyboard
OBJECT_NAMES = {"shape": "Drawing", "arrow": "Arrow", "note": "Text box",
                "legend": "Legend box", "text": "Text", "frame": "Frame"}
COPYABLE = ("shape", "arrow", "note")   # a legend or an axis label is not copied
PASTE_STEP = 14.0           # pixels: how far a pasted copy sits from the original
NUDGE_STEP = 1.0            # pixels: one press of an arrow key
NUDGE_BIG_STEP = 10.0       # pixels: with Shift
SNAP_ANGLE = np.pi / 4      # arrows snap to 45 degrees while Shift is held
SELECT_COLOR = "#1a5fb4"    # the blue of the selection
SELECT_FACE = to_rgba(SELECT_COLOR, 0.18)     # veil over a selected text
SELECT_EDGE = to_rgba(SELECT_COLOR, 0.90)
SELECT_BOX = {"boxstyle": "round,pad=0.28", "facecolor": SELECT_FACE,
              "edgecolor": SELECT_EDGE, "linewidth": 1.0}
MODIFIER = "Command" if sys.platform == "darwin" else "Control"
PASTE_HINT = "Cmd+V" if sys.platform == "darwin" else "Ctrl+V"
ACCEL_NAME = "Cmd" if sys.platform == "darwin" else "Ctrl"

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


def drawn_names(table):
    """Option names of a table without its "none" entry.

    The curve dialog switches the line, the marker, the legend and the fill on
    and off with a check button, so "None" is not offered in the lists.
    """
    return [name for name, code in table if str(code).lower() != "none"]


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


def make_letter_icon(letter="T", size=24, color="#000000"):
    """A small toolbar icon drawn as a letter, in the style of the others."""
    icon = tk.PhotoImage(width=size, height=size)
    thick = max(2, size // 8)
    left, right = size // 5, size - size // 5
    top, bottom = size // 5, size - size // 5
    middle = size // 2
    if letter == "T":
        icon.put(color, to=(left, top, right, top + thick))          # the bar
        icon.put(color, to=(middle - thick // 2 - 1, top,            # the stem
                            middle + thick // 2 + 1, bottom))
    return icon


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
        "dialogs_on_top": False,
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
        "marker_edge_width": 1.5, "hollow_markers": False,
        "legend_visible": True, "legend_location": "best",
        "legend_frame": False, "legend_edge_color": "#000000",
        "legend_background": "#ffffff", "legend_transparent": True,
        "fill_under": False, "fill_color": "#1f77b4", "fill_alpha": 0.36,
        "fill_pattern": "None (plain colour)", "fill_base": "Zero line",
        "fill_follows_line": True,
    },
    "fonts": {
        "title": 18, "axis_label": 18, "tick_label": 16, "legend": 14,
        "title_color": "#000000", "axis_label_color": "#000000",
        "tick_label_color": "#000000", "legend_color": "#000000",
        "title_pad": 8.0, "axis_label_pad": 7, "tick_label_pad": 10.0,
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
    "text": {
        "size": 14, "color": "#000000", "frame": True,
        "edge_color": "#000000", "background": "#ffffff", "transparent": False,
    },
    "shape": {
        "kind": "Rectangle", "line_style": "Solid", "line_width": 1.5,
        "line_color": "#000000", "fill_color": "#cfe3f7", "no_fill": False,
        "fill_alpha": 0.6,
    },
    "arrow": {
        "head": "Triangle head", "head_size": 14.0, "line_style": "Solid",
        "line_width": 1.6, "color": "#000000",
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
        ("dialogs_on_top", "Property windows always on top", "bool"),
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
        ("title_pad", "Title distance from the axes [px]", "float"),
        ("axis_label_pad", "Axis label distance [px]", "float"),
        ("tick_label_pad", "Axis numbers distance [px]", "float"),
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
    ("text", "Text boxes", [
        ("size", "Font size", "int"),
        ("color", "Font colour", "color"),
        ("frame", "Frame around the box", "bool"),
        ("edge_color", "Frame colour", "color"),
        ("background", "Background colour", "color"),
        ("transparent", "Transparent background", "bool"),
    ]),
    ("shape", "Drawings", [
        ("kind", "Shape of the drawing tool", "choice", names(SHAPE_KINDS)),
        ("line_style", "Line style", "choice", names(LINE_STYLES)),
        ("line_width", "Line thickness", "float"),
        ("line_color", "Line colour", "color"),
        ("fill_color", "Fill colour", "color"),
        ("no_fill", "No fill (outline only)", "bool"),
        ("fill_alpha", "Fill opacity (0-1)", "float"),
    ]),
    ("arrow", "Arrows", [
        ("head", "Arrow head", "choice", names(ARROW_HEADS)),
        ("head_size", "Head size [px]", "float"),
        ("line_style", "Line style", "choice", names(LINE_STYLES)),
        ("line_width", "Line thickness", "float"),
        ("color", "Colour", "color"),
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


class ShapeToolButton(tk.Canvas):
    """Toolbar button with an icon and a small menu arrow on its right.

    Clicking the icon starts drawing with the object that is shown; clicking
    the arrow opens the list of the available objects.  `family` selects
    what the icon draws: the shapes or the arrow heads.
    """

    ARROW_ZONE = 12

    def __init__(self, master, kind="rect", size=24, family="shape",
                 background=None, on_draw=None, on_menu=None):
        self._background = background or master.cget("background")
        super().__init__(master, width=size + ShapeToolButton.ARROW_ZONE,
                         height=size, highlightthickness=0, borderwidth=0,
                         background=self._background, cursor="hand2")
        self._size = size
        self.family = family
        self.kind = kind
        self._on_draw = on_draw
        self._on_menu = on_menu
        self.bind("<Button-1>", self._clicked)
        self.set_shape(kind)

    # -- drawing the icon --------------------------------------------------
    def set_shape(self, kind):
        self.kind = kind
        self.delete("icon")
        pad = 4
        x0, y0 = pad, pad
        x1, y1 = self._size - pad, self._size - pad
        style = {"outline": "#000000", "width": 2, "fill": "", "tags": "icon"}
        if self.family == "arrow":
            self._draw_arrow_icon(kind, x0, y0, x1, y1)
        elif kind == "triangle":
            self.create_polygon([(x0 + x1) / 2, y0, x0, y1, x1, y1],
                                outline="#000000", fill="", width=2, tags="icon")
        elif kind == "circle":
            self.create_oval(x0, y0, x1, y1, **style)
        elif kind == "ellipse":
            self.create_oval(x0, y0 + 3, x1, y1 - 3, **style)
        else:
            self.create_rectangle(x0, y0 + 2, x1, y1 - 2, **style)
        self._draw_menu_arrow()

    def _draw_arrow_icon(self, kind, x0, y0, x1, y1):
        """A right pointing arrow whose head shows the selected type."""
        middle = (y0 + y1) / 2
        tip, back = x1, x1 - 8
        half = 5
        self.create_line(x0, middle, back, middle, fill="#000000", width=2,
                         tags="icon")
        if kind == "chevron":
            self.create_line(back, middle - half, tip, middle, back,
                             middle + half, fill="#000000", width=2, tags="icon")
            return
        if kind == "concave":
            points = [tip, middle, back, middle - half,
                      back + 3, middle, back, middle + half]
        elif kind == "convex":
            points = [tip, middle, back, middle - half,
                      back - 2, middle, back, middle + half]
        else:                                    # triangle
            points = [tip, middle, back, middle - half, back, middle + half]
        self.create_polygon(points, fill="#000000", outline="#000000",
                            tags="icon")

    def _draw_menu_arrow(self):
        self.delete("arrow")
        width = int(self["width"])
        height = int(self["height"])
        x, y = width - 4, height - 4
        self.create_polygon([x - 7, y - 5, x, y - 5, x - 3.5, y],
                            fill="#000000", outline="#000000", tags="arrow")

    def set_active(self, active):
        self.configure(background="#b8b8b8" if active else self._background)

    # -- behaviour ---------------------------------------------------------
    def _clicked(self, event):
        if event.x >= int(self["width"]) - ShapeToolButton.ARROW_ZONE:
            if self._on_menu:
                self._on_menu(event)
        elif self._on_draw:
            self._on_draw()
        return "break"


class ToolDialog(tk.Toplevel):
    """Base class of the small property windows.

    These windows are ordinary windows, not transient children, so the
    diagram can be brought in front of them while the settings stay open.
    `Property windows always on top` in the settings restores the old
    behaviour for those who prefer it.
    """

    def __init__(self, master, title, on_close=None):
        super().__init__(master)
        self.title(title)
        self.resizable(False, False)
        self._on_close = on_close
        if self.keep_on_top(master):
            self.transient(master)      # stays above the diagram window
        self.body = ttk.Frame(self, padding=12)
        self.body.pack(fill="both", expand=True)
        self.bind("<Escape>", lambda _e: self.close())
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.after_idle(self.place_beside_parent)

    @staticmethod
    def keep_on_top(master):
        settings = getattr(master, "settings", None)
        try:
            return bool(settings.get("window", "dialogs_on_top"))
        except (AttributeError, KeyError, TypeError):
            return False

    def place_beside_parent(self):
        """Open next to the parent window instead of on top of it."""
        try:
            self.update_idletasks()
            parent = self.master.winfo_toplevel()
            px, py = parent.winfo_rootx(), parent.winfo_rooty()
            width, height = self.winfo_width(), self.winfo_height()
            screen_w = self.winfo_screenwidth()
            screen_h = self.winfo_screenheight()

            x = px + parent.winfo_width() + 12          # to the right
            if x + width > screen_w - 8:
                x = px - width - 12                     # or to the left
            if x < 8:
                x = max(8, screen_w - width - 8)
            y = min(max(8, py + 24), max(8, screen_h - height - 48))
            self.geometry(f"+{int(x)}+{int(y)}")
        except tk.TclError:
            pass

    def close(self):
        if self._on_close:
            self._on_close(self)
        self.destroy()
        # the diagram gets the keyboard back, so the arrow keys and the
        # copy/paste shortcuts keep working after a property window was used
        take_focus = getattr(self.master, "take_focus", None)
        if callable(take_focus):
            take_focus()

    @staticmethod
    def field(parent, row, text, widget, pady=3):
        ttk.Label(parent, text=text).grid(row=row, column=0, sticky="w",
                                          padx=(0, 8), pady=pady)
        widget.grid(row=row, column=1, sticky="w", pady=pady)
        return widget


class ArrowDialog(ToolDialog):
    """Head, line and colour of one arrow."""

    def __init__(self, master, state, on_apply, on_delete=None, on_close=None):
        super().__init__(master, "Arrow properties", on_close=on_close)
        self.on_apply = on_apply
        self.on_delete = on_delete

        self.head_var = tk.StringVar(
            value=name_of(ARROW_HEADS, state["head"], "Triangle head"))
        self.size_var = tk.StringVar(value=f"{state['size']:g}")
        self.style_var = tk.StringVar(
            value=name_of(LINE_STYLES, state["style"], "Solid"))
        self.width_var = tk.StringVar(value=f"{state['width']:g}")

        head = ttk.LabelFrame(self.body, text="Arrow head", padding=8)
        head.pack(fill="x")
        combo = ttk.Combobox(head, textvariable=self.head_var, state="readonly",
                             values=names(ARROW_HEADS), width=16)
        self.field(head, 0, "Type:", combo)
        combo.bind("<<ComboboxSelected>>", lambda _e: self.apply())
        self.field(head, 1, "Size [px]:",
                   ttk.Spinbox(head, from_=2, to=80, increment=1, width=8,
                               textvariable=self.size_var, command=self.apply))

        line = ttk.LabelFrame(self.body, text="Line", padding=8)
        line.pack(fill="x", pady=(10, 0))
        style = ttk.Combobox(line, textvariable=self.style_var, state="readonly",
                             values=names(LINE_STYLES), width=16)
        self.field(line, 0, "Style:", style)
        style.bind("<<ComboboxSelected>>", lambda _e: self.apply())
        self.field(line, 1, "Thickness:",
                   ttk.Spinbox(line, from_=0.2, to=20, increment=0.2, width=8,
                               textvariable=self.width_var, command=self.apply))
        self.color = ColorSwatch(line, state["color"],
                                 command=lambda _c: self.apply())
        self.field(line, 2, "Colour:", self.color)

        ttk.Label(self.body, foreground="#666", justify="left",
                  text="Drag the arrow to move it, drag the handle on its tip\n"
                       "or on its tail to change the direction and length."
                  ).pack(anchor="w", pady=(8, 0))

        bar = ttk.Frame(self.body)
        bar.pack(fill="x", pady=(12, 0))
        ttk.Button(bar, text="Apply", command=self.apply).pack(side="left")
        if on_delete is not None:
            ttk.Button(bar, text="Delete", command=self._delete).pack(
                side="left", padx=(6, 0))
        ttk.Button(bar, text="Close", command=self.close).pack(side="right")

    def values(self):
        return {
            "head": code_of(ARROW_HEADS, self.head_var.get(), "triangle"),
            "size": max(2.0, to_float(self.size_var.get(), 14.0)),
            "style": code_of(LINE_STYLES, self.style_var.get(), "-"),
            "width": max(0.2, to_float(self.width_var.get(), 1.6)),
            "color": self.color.color,
        }

    def apply(self):
        self.on_apply(self.values())

    def _delete(self):
        if self.on_delete:
            self.on_delete()
        self.close()


class ShapeDialog(ToolDialog):
    """Line and fill properties of one drawn object."""

    def __init__(self, master, state, on_apply, on_delete=None, on_close=None):
        super().__init__(master, f"{name_of(SHAPE_KINDS, state['kind'], 'Shape')}"
                                 " properties", on_close=on_close)
        self.on_apply = on_apply
        self.on_delete = on_delete

        self.style_var = tk.StringVar(
            value=name_of(LINE_STYLES, state["style"], "Solid"))
        self.width_var = tk.StringVar(value=f"{state['width']:g}")
        self.alpha_var = tk.StringVar(value=f"{state.get('alpha', 0.6):g}")
        self.no_fill_var = tk.BooleanVar(value=state["face"] == "none")
        self.angle_var = tk.StringVar(value=f"{float(state.get('angle', 0.0)):g}")

        line = ttk.LabelFrame(self.body, text="Line", padding=8)
        line.pack(fill="x")
        combo = ttk.Combobox(line, textvariable=self.style_var, state="readonly",
                             values=names(LINE_STYLES), width=14)
        self.field(line, 0, "Style:", combo)
        combo.bind("<<ComboboxSelected>>", lambda _e: self.apply())
        self.field(line, 1, "Thickness:",
                   ttk.Spinbox(line, from_=0, to=20, increment=0.5, width=8,
                               textvariable=self.width_var, command=self.apply))
        self.edge_color = ColorSwatch(line, state["edge"],
                                      command=lambda _c: self.apply())
        self.field(line, 2, "Colour:", self.edge_color)

        fill = ttk.LabelFrame(self.body, text="Fill", padding=8)
        fill.pack(fill="x", pady=(10, 0))
        self.face_color = ColorSwatch(
            fill, "#cfe3f7" if state["face"] == "none" else state["face"],
            command=lambda _c: self.apply())
        self.field(fill, 0, "Colour:", self.face_color)
        self.field(fill, 1, "", ttk.Checkbutton(fill, text="No fill (outline only)",
                                                variable=self.no_fill_var,
                                                command=self.apply))
        self.field(fill, 2, "Opacity (0-1):",
                   ttk.Spinbox(fill, from_=0, to=1, increment=0.05, width=8,
                               textvariable=self.alpha_var, command=self.apply))

        turn = ttk.LabelFrame(self.body, text="Rotation", padding=8)
        turn.pack(fill="x", pady=(10, 0))
        self.field(turn, 0, "Angle [deg]:",
                   ttk.Spinbox(turn, from_=-360, to=360, increment=5, width=8,
                               textvariable=self.angle_var, command=self.apply))
        ttk.Button(turn, text="Upright",
                   command=lambda: (self.angle_var.set("0"), self.apply())).grid(
            row=0, column=2, padx=(8, 0))

        ttk.Label(self.body, foreground="#666", justify="left",
                  text="Drag the object to move it, drag a square handle to\n"
                       "resize it and the round one above it to turn it\n"
                       "(Shift: 15 degree steps).").pack(anchor="w", pady=(8, 0))

        bar = ttk.Frame(self.body)
        bar.pack(fill="x", pady=(12, 0))
        ttk.Button(bar, text="Apply", command=self.apply).pack(side="left")
        if on_delete is not None:
            ttk.Button(bar, text="Delete", command=self._delete).pack(
                side="left", padx=(6, 0))
        ttk.Button(bar, text="Close", command=self.close).pack(side="right")

    def values(self):
        return {
            "style": code_of(LINE_STYLES, self.style_var.get(), "-"),
            "width": max(0.0, to_float(self.width_var.get(), 1.5)),
            "edge": self.edge_color.color,
            "face": "none" if self.no_fill_var.get() else self.face_color.color,
            "alpha": min(1.0, max(0.0, to_float(self.alpha_var.get(), 0.6))),
            "angle": to_float(self.angle_var.get(), 0.0) % 360.0,
        }

    def apply(self):
        self.on_apply(self.values())

    def _delete(self):
        if self.on_delete:
            self.on_delete()
        self.close()


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
        self.notebook = notebook
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
                 color="#000000", distance=None, distance_label="Distance [px]:",
                 hint=None, on_close=None):
        super().__init__(master, title, on_close=on_close)
        self.on_apply = on_apply
        self.text_var = tk.StringVar(value=text)
        self.size_var = tk.StringVar(value=str(int(size)))
        self.distance_var = (tk.StringVar(value=f"{float(distance):g}")
                             if distance is not None else None)

        box = ttk.Frame(self.body)
        box.pack(fill="x")
        entry = self.field(box, 0, "Text:",
                           ttk.Entry(box, textvariable=self.text_var, width=34))
        self.field(box, 1, "Font size:",
                   ttk.Spinbox(box, from_=4, to=72, increment=1, width=8,
                               textvariable=self.size_var, command=self.apply))
        self.color = ColorSwatch(box, color, command=lambda _c: self.apply())
        self.field(box, 2, "Font colour:", self.color)
        if self.distance_var is not None:
            self.field(box, 3, distance_label,
                       ttk.Spinbox(box, from_=-200, to=400, increment=1, width=8,
                                   textvariable=self.distance_var,
                                   command=self.apply))
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
        distance = (to_float(self.distance_var.get(), 0.0)
                    if self.distance_var is not None else None)
        self.on_apply(self.text_var.get(), to_int(self.size_var.get(), 10),
                      self.color.color, distance)

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
        self.column = getattr(line, "aplot_series", None)
        self.label_var = tk.StringVar(value="" if label.startswith("_") else label)

        # every section has its own check button: off means the line, the
        # marker, the legend box or the fill is simply not drawn
        self.line_on_var = tk.BooleanVar(value=not self.is_off(line.get_linestyle()))
        self.marker_on_var = tk.BooleanVar(value=not self.is_off(line.get_marker()))
        self.legend_on_var = tk.BooleanVar(value=not label.startswith("_"))

        self.lstyle_var = tk.StringVar(
            value=self.first_choice(LINE_STYLES, line.get_linestyle(), "Solid"))
        self.lwidth_var = tk.StringVar(value=f"{line.get_linewidth():g}")
        self.mstyle_var = tk.StringVar(
            value=self.first_choice(MARKERS, line.get_marker(),
                                    self.default_marker()))
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

    # -- helpers -----------------------------------------------------------
    @staticmethod
    def is_off(code):
        """True for every way matplotlib writes "not drawn"."""
        return str(code).strip().lower() in ("none", "", " ", "nothing")

    @staticmethod
    def first_choice(table, code, fallback):
        """The name of `code`, or `fallback` when it is switched off."""
        if SeriesStyleDialog.is_off(code):
            names_left = drawn_names(table)
            return fallback if fallback in names_left else names_left[0]
        return name_of(table, code, fallback)

    def default_marker(self):
        """The marker a curve gets when the marker is switched on."""
        settings = getattr(self.master, "settings", None)
        try:
            wanted = str(settings.get("plot", "marker"))
        except (AttributeError, KeyError, TypeError):
            wanted = ""
        choices = drawn_names(MARKERS)
        return wanted if wanted in choices else choices[0]

    def _section(self, title, variable, **pack):
        """A section whose title is its own check button."""
        box = ttk.LabelFrame(self.body, padding=8)
        check = ttk.Checkbutton(box, text=title, variable=variable,
                                command=self._apply)
        box.configure(labelwidget=check)
        box.pack(fill="x", **pack)
        return box

    # -- construction ------------------------------------------------------
    def _build_legend_box(self):
        box = self._section("Legend", self.legend_on_var)
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
        ttk.Label(box, text="Switch \"Legend\" off to hide this curve's box.",
                  foreground="#666").grid(row=3, column=0, columnspan=2,
                                          sticky="w", pady=(4, 0))

    def _build_line_box(self, line_color):
        box = self._section("Line", self.line_on_var, pady=(10, 0))

        combo = ttk.Combobox(box, textvariable=self.lstyle_var, state="readonly",
                             values=drawn_names(LINE_STYLES), width=14)
        self.field(box, 0, "Style:", combo)
        combo.bind("<<ComboboxSelected>>", self._apply)

        self.field(box, 1, "Width:",
                   ttk.Spinbox(box, from_=0, to=20, increment=0.5, width=8,
                               textvariable=self.lwidth_var, command=self._apply))
        self.lwidth_var.trace_add("write", self._apply)

        self.line_color = ColorSwatch(box, line_color, command=lambda _c: self._apply())
        self.field(box, 2, "Colour:", self.line_color)

    def _build_marker_box(self, line_color, face):
        box = self._section("Marker", self.marker_on_var, pady=(10, 0))

        combo = ttk.Combobox(box, textvariable=self.mstyle_var, state="readonly",
                             values=drawn_names(MARKERS), width=14)
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
        box = self._section("Fill under the curve", self.fill_on_var,
                            pady=(10, 0))

        self.field(box, 0, "", ttk.Checkbutton(box, text="Same colour as the curve",
                                               variable=self.fill_follow_var,
                                               command=self._apply))
        self.fill_color = ColorSwatch(box, self._fill.get("color", line_color),
                                      command=lambda _c: self._apply())
        self.field(box, 1, "Fill colour:", self.fill_color)
        self.field(box, 2, "Opacity (0-1):",
                   ttk.Spinbox(box, from_=0, to=1, increment=0.05, width=8,
                               textvariable=self.fill_alpha_var, command=self._apply))
        self.fill_alpha_var.trace_add("write", self._apply)

        pattern = ttk.Combobox(box, textvariable=self.fill_hatch_var,
                               state="readonly", values=names(HATCH_PATTERNS),
                               width=22)
        self.field(box, 3, "Pattern:", pattern)
        pattern.bind("<<ComboboxSelected>>", self._apply)

        base = ttk.Combobox(box, textvariable=self.fill_base_var, state="readonly",
                            values=names(FILL_BASES), width=22)
        self.field(box, 4, "Fill down to:", base)
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

        line.set_linestyle(code_of(LINE_STYLES, self.lstyle_var.get(), "-")
                           if self.line_on_var.get() else "none")
        line.set_linewidth(to_float(self.lwidth_var.get(), line.get_linewidth()))
        line.set_color(self.line_color.color)

        line.set_marker(code_of(MARKERS, self.mstyle_var.get(), "o")
                        if self.marker_on_var.get() else "None")
        line.set_markersize(to_float(self.msize_var.get(), line.get_markersize()))
        line.set_markerfacecolor("none" if self.hollow_var.get()
                                 else self.face_color.color)
        line.set_markeredgecolor(self.edge_color.color)
        line.set_markeredgewidth(to_float(self.mwidth_var.get(),
                                          line.get_markeredgewidth()))

        text = self.label_var.get().strip()
        if self.legend_on_var.get():
            if not text and self.column:     # switched on with an empty text
                self._loading = True         # the column name is a good start
                self.label_var.set(str(self.column))
                self._loading = False
                text = str(self.column)
            line.set_label(text if text else "_nolegend_")
        else:
            line.set_label("_nolegend_")
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
        self.label_pad_var = tk.StringVar(value=f"{cfg['label_pad']:g}")
        self.tick_pad_var = tk.StringVar(value=f"{cfg['tick_pad']:g}")
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
        ToolDialog.field(box, 3, "Label distance from the axis [px]:",
                         ttk.Spinbox(box, from_=-200, to=400, increment=1, width=8,
                                     textvariable=self.label_pad_var))
        ToolDialog.field(box, 4, "Numbers (ticks) font size:",
                         ttk.Spinbox(box, from_=4, to=48, increment=1, width=8,
                                     textvariable=self.tick_size_var))
        self.tick_color = ColorSwatch(box, self._tick_color)
        ToolDialog.field(box, 5, "Numbers (ticks) font colour:", self.tick_color)
        ToolDialog.field(box, 6, "Numbers distance from the axis [px]:",
                         ttk.Spinbox(box, from_=-200, to=400, increment=1, width=8,
                                     textvariable=self.tick_pad_var))

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
            "label_pad": to_float(self.label_pad_var.get(), 5.5),
            "tick_pad": to_float(self.tick_pad_var.get(), 5.0),
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


class TextBoxDialog(ToolDialog):
    """A legend box or a free text box: text, font, frame and background."""

    def __init__(self, master, title, text, state, on_apply, on_close=None,
                 hint=None, on_delete=None, rotation=False):
        super().__init__(master, title, on_close=on_close)
        self.on_apply = on_apply
        self.on_delete = on_delete
        self.rotation = rotation
        self.angle_var = tk.StringVar(
            value=f"{float(state.get('angle', 0.0) or 0.0):g}")

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
        ttk.Label(box, text=hint or "An empty text hides this box.",
                  foreground="#666", justify="left").grid(
            row=3, column=0, columnspan=2, sticky="w", pady=(4, 0))

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
        ttk.Label(frame_box, text="Drag the box with the pointer to move it.",
                  foreground="#666").grid(row=4, column=0, columnspan=2,
                                          sticky="w", pady=(4, 0))

        if rotation:
            turn = ttk.LabelFrame(self.body, text="Rotation", padding=8)
            turn.pack(fill="x", pady=(10, 0))
            self.field(turn, 0, "Angle [deg]:",
                       ttk.Spinbox(turn, from_=-360, to=360, increment=5,
                                   width=8, textvariable=self.angle_var,
                                   command=self.apply))
            ttk.Button(turn, text="Upright",
                       command=lambda: (self.angle_var.set("0"),
                                        self.apply())).grid(row=0, column=2,
                                                            padx=(8, 0))
            ttk.Label(turn, foreground="#666", justify="left",
                      text="Or drag the round handle above the box\n"
                           "(Shift: 15 degree steps).").grid(
                row=1, column=0, columnspan=3, sticky="w", pady=(4, 0))

        bar = ttk.Frame(self.body)
        bar.pack(fill="x", pady=(12, 0))
        ttk.Button(bar, text="Apply", command=self.apply).pack(side="left")
        if on_delete is not None:
            ttk.Button(bar, text="Delete", command=self._delete).pack(side="left",
                                                                      padx=(6, 0))
        ttk.Button(bar, text="Close", command=self.close).pack(side="right")
        ttk.Button(bar, text="OK", command=self._ok).pack(side="right", padx=(0, 6))
        self.bind("<Return>", lambda _e: self.apply())
        entry.focus_set()
        entry.select_range(0, "end")

    def values(self):
        values = {
            "text": self.text_var.get(),
            "size": to_int(self.size_var.get(), 10),
            "color": self.color.color,
            "edge": self.edge_color.color if self.frame_var.get() else "none",
            "face": "none" if self.transparent_var.get() else self.face_color.color,
        }
        if self.rotation:
            values["angle"] = to_float(self.angle_var.get(), 0.0) % 360.0
        return values

    def apply(self):
        self.on_apply(self.values())

    def _delete(self):
        if self.on_delete:
            self.on_delete()
        self.close()

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
        self.title_pad_var = tk.StringVar(value=f"{plot.fonts['title_pad']:g}")
        self.field(box, 3, "Distance from the axes [px]:",
                   ttk.Spinbox(box, from_=-200, to=400, increment=1, width=8,
                               textvariable=self.title_pad_var))

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
        ttk.Button(box, text="Reset dragged texts",
                   command=self.plot.reset_text_offsets).grid(row=4, column=1,
                                                              sticky="w",
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
        plot.fonts["title_pad"] = to_float(self.title_pad_var.get(),
                                           plot.fonts["title_pad"])
        plot.ax.set_title(self.title_var.get(), fontsize=plot.fonts["title"],
                          color=plot.fonts["title_color"],
                          pad=plot.points(plot.fonts["title_pad"]))
        plot.ax.title.set_picker(True)
        plot.apply_text_offset("title")
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

    # the copied object, shared by every diagram window of the program
    _clipboard = None

    HINT = ("One click selects (a text turns blue), a second click opens its "
            "properties   |   A curve: one click   |   Drag: move   |   "
            "Drag a control point: resize\n"
            "\"T\", the shape and the arrow button: add text, drawings and "
            "arrows   |   Shift: arrows at 45 deg steps   |   "
            f"{ACCEL_NAME}+C / {ACCEL_NAME}+V: copy and paste   |   "
            "Arrow keys: move   |   Delete: remove")

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
        self._text_drag = None
        self.notes: dict = {}           # key -> free text box
        self.note_state: dict = {}      # key -> {text, pos, size, colour, box}
        self._note_counter = 0
        self._pending_text = False
        self.shapes: dict = {}          # key -> drawn patch
        self.shape_state: dict = {}     # key -> {kind, x, y, w, h, line, fill}
        self._shape_counter = 0
        self._pending_shape = False
        self._shape_drag = None
        # ("shape"|"arrow"|"note"|"legend"|"text", key) - one click selects,
        # a second click opens the properties of the selected object
        self.selection = None
        self._marked = None             # the text that wears the blue veil
        self._shift_down = False        # Shift snaps the arrows to 45 degrees
        self._handles = None
        self._rotator = None            # the round rotation control point
        self.shape_kind = code_of(SHAPE_KINDS,
                                  config.get("shape", "kind"), "rect")
        self.arrows: dict = {}          # key -> [shaft, head]
        self.arrow_state: dict = {}     # key -> {head, tail, tip, size, line}
        self._arrow_counter = 0
        self._pending_arrow = False
        self.arrow_head = code_of(ARROW_HEADS,
                                  config.get("arrow", "head"), "triangle")
        # how far the title and the axis labels were dragged, in pixels
        self.text_offset = {"title": (0.0, 0.0), "x": (0.0, 0.0), "y": (0.0, 0.0)}
        self._text_base = {}
        self._cursor = ""
        self._dpi = float(plot_cfg["dpi"])
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
                    "label_pad": float(self.fonts["axis_label_pad"]),
                    "tick_pad": float(self.fonts["tick_label_pad"]),
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
            plot_menu.add_command(label="Copy object",
                                  accelerator=f"{ACCEL_NAME}+C",
                                  command=self.copy_selection)
            plot_menu.add_command(label="Paste object",
                                  accelerator=f"{ACCEL_NAME}+V",
                                  command=self.paste_clipboard)
            plot_menu.add_command(label="Delete object", accelerator="Del",
                                  command=self.delete_selection)
            plot_menu.add_separator()
            plot_menu.add_command(label="Close", command=self.destroy)
            menubar.add_cascade(label="Plot", menu=plot_menu)
            self.configure(menu=menubar)

        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self._bind_native_focus()
        toolbar = NavigationToolbar2Tk(self.canvas, self, pack_toolbar=False)
        toolbar.update()
        self.toolbar = toolbar
        # "add text" button, a little away from the save button
        tk.Frame(toolbar, width=26, height=1).pack(side="left")
        self._text_icon = make_letter_icon("T")
        self.text_button = tk.Button(toolbar, image=self._text_icon,
                                     command=self.arm_text_placement,
                                     relief="flat", borderwidth=1,
                                     highlightthickness=0)
        self.text_button.pack(side="left", padx=2, pady=2)
        self.text_button.bind(
            "<Enter>", lambda _e: toolbar.set_message(
                "Add text: click in the diagram to place a text box"))
        self.text_button.bind("<Leave>", lambda _e: toolbar.set_message(""))

        button_background = self.text_button.cget("background")
        self.shape_button = ShapeToolButton(
            toolbar, kind=self.shape_kind, family="shape",
            background=button_background,
            on_draw=lambda: self.arm_shape_drawing(armed=True),
            on_menu=self.show_shape_menu)
        self.shape_button.pack(side="left", padx=(4, 2), pady=2)
        self.shape_button.bind(
            "<Enter>", lambda _e: toolbar.set_message(
                "Draw: click the icon and drag in the diagram, "
                "the arrow selects the shape"), add="+")
        self.shape_button.bind("<Leave>", lambda _e: toolbar.set_message(""),
                               add="+")

        self.arrow_button = ShapeToolButton(
            toolbar, kind=self.arrow_head, family="arrow",
            background=button_background,
            on_draw=lambda: self.arm_arrow_drawing(armed=True),
            on_menu=self.show_arrow_menu)
        self.arrow_button.pack(side="left", padx=(4, 2), pady=2)
        self.arrow_button.bind(
            "<Enter>", lambda _e: toolbar.set_message(
                "Arrow: click the icon and drag in the diagram, "
                "the small arrow selects the head"), add="+")
        self.arrow_button.bind("<Leave>", lambda _e: toolbar.set_message(""),
                               add="+")

        try:            # the standard Save button must not save the marks
            save_button = toolbar._buttons.get("Save")
            if save_button is not None:
                save_button.configure(command=self.save_figure_clean)
        except (AttributeError, tk.TclError):
            pass

        self.bind("<Escape>", lambda _e: self.cancel_tools())
        self.canvas.get_tk_widget().bind("<Escape>",
                                         lambda _e: self.cancel_tools())
        self._bind_keys()
        toolbar.pack(side="top", fill="x")
        self.canvas.get_tk_widget().pack(side="top", fill="both", expand=True)
        ttk.Label(self, text=self.HINT, anchor="center", justify="center",
                  padding=4, foreground="#444").pack(side="bottom", fill="x")

    def take_focus(self, _event=None):
        """Give the keyboard to the diagram canvas.

        matplotlib runs the canvas clicks through its own event loop, which
        does not always hand the focus back to Tk - and after a property
        window has been used, the keyboard belongs to that window.  Setting
        the focus natively keeps the arrow keys, Delete and copy/paste alive.
        """
        try:
            widget = self.canvas.get_tk_widget()
            if widget.winfo_exists():
                widget.focus_set()
        except (tk.TclError, AttributeError):
            pass
        return None            # never "break": matplotlib needs the click too

    def _bind_native_focus(self):
        """Every click in the diagram brings the keyboard back, natively."""
        widget = self.canvas.get_tk_widget()
        try:
            widget.configure(takefocus=True)
        except tk.TclError:
            pass
        for sequence in ("<Button-1>", "<Button-2>", "<Button-3>"):
            # add="+" keeps matplotlib's own handlers of these events
            widget.bind(sequence, self.take_focus, add="+")
        # when the window itself is activated and nothing inside it holds the
        # keyboard, the diagram takes it
        self.bind("<FocusIn>", self._window_focused, add="+")

    def _window_focused(self, _event=None):
        try:
            current = self.focus_displayof()
        except (tk.TclError, KeyError):
            current = None
        if current is None or current is self:
            self.take_focus()
        return None

    def _bind_keys(self):
        """Copy, paste, deleting and moving the selected object."""
        def wrap(function, *args):
            def handler(_event=None):
                function(*args)
                return "break"
            return handler

        canvas_widget = self.canvas.get_tk_widget()

        def bind_both(sequence, handler):
            # on the canvas (which owns the focus while the diagram is used)
            # and on the window (for the toolbar and the rest of it)
            self.bind(sequence, handler)
            try:
                canvas_widget.bind(sequence, handler)
            except tk.TclError:
                pass

        for modifier in ("Control", "Command"):
            for letter in ("c", "C"):
                bind_both(f"<{modifier}-{letter}>", wrap(self.copy_selection))
            for letter in ("v", "V"):
                bind_both(f"<{modifier}-{letter}>", wrap(self.paste_clipboard))
        for sequence in ("<Delete>", "<BackSpace>"):
            bind_both(sequence, wrap(self.delete_selection))

        steps = {"Left": (-1, 0), "Right": (1, 0), "Up": (0, 1), "Down": (0, -1)}
        for name, (sx, sy) in steps.items():
            bind_both(f"<{name}>",
                      wrap(self.nudge_selection, sx * NUDGE_STEP, sy * NUDGE_STEP))
            bind_both(f"<Shift-{name}>",
                      wrap(self.nudge_selection,
                           sx * NUDGE_BIG_STEP, sy * NUDGE_BIG_STEP))

        # Shift snaps the arrows: remember whether it is held down
        for sequence in ("<KeyPress-Shift_L>", "<KeyPress-Shift_R>"):
            bind_both(sequence, lambda _e: setattr(self, "_shift_down", True))
        for sequence in ("<KeyRelease-Shift_L>", "<KeyRelease-Shift_R>"):
            bind_both(sequence, lambda _e: setattr(self, "_shift_down", False))
        self.bind("<FocusOut>", lambda _e: setattr(self, "_shift_down", False),
                  add="+")

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
                "label_pad": cfg["label_pad"], "tick_pad": cfg["tick_pad"],
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
                      "color": safe_hex(self.fonts["title_color"], "#000000"),
                      "pad": float(self.fonts["title_pad"])},
            "legend": {"visible": self.legend_visible, "location": self.legend_loc,
                       "size": self.fonts["legend"],
                       "color": safe_hex(self.fonts["legend_color"], "#000000")},
            "frame": dict(self.frame_cfg),
            "text_offsets": {name: [float(value[0]), float(value[1])]
                             for name, value in self.text_offset.items()},
            "shapes": [{key_: (float(value) if key_ in ("x", "y", "w", "h", "angle",
                                                        "width", "alpha")
                               else value)
                        for key_, value in state.items()}
                       for state in self.shape_state.values()],
            "arrows": [{"head": state["head"],
                        "tail": [float(state["tail"][0]), float(state["tail"][1])],
                        "tip": [float(state["tip"][0]), float(state["tip"][1])],
                        "size": float(state["size"]), "style": state["style"],
                        "width": float(state["width"]), "color": state["color"]}
                       for state in self.arrow_state.values()],
            "notes": [{"text": state["text"],
                       "pos": [float(state["pos"][0]), float(state["pos"][1])],
                       "angle": float(state.get("angle", 0.0) or 0.0),
                       "size": int(state["size"]), "color": state["color"],
                       "edge": state["edge"], "face": state["face"]}
                      for state in self.note_state.values()],
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
        self.fonts["title_pad"] = float(title.get("pad", self.fonts["title_pad"]))
        self.ax.set_title(title.get("text", self.ax.get_title()),
                          fontsize=self.fonts["title"],
                          color=safe_hex(self.fonts["title_color"], "#000000"),
                          pad=self.points(self.fonts["title_pad"]))
        self.ax.title.set_picker(True)

        for name, value in (state.get("text_offsets") or {}).items():
            if name in self.text_offset and value:
                self.text_offset[name] = (float(value[0]), float(value[1]))
        self.apply_text_offsets()

        for key in list(self.shape_state):          # replace the drawings
            self.remove_shape(key)
        for shape in state.get("shapes") or []:
            kind = shape.get("kind", "rect")
            base = self.default_shape_state(kind, 0.4, 0.4, 0.2, 0.15)
            self.add_shape(state={**base, **shape, "kind": kind})

        for key in list(self.arrow_state):           # replace the arrows
            self.remove_arrow(key)
        for arrow in state.get("arrows") or []:
            head = arrow.get("head", "triangle")
            base = self.default_arrow_state(head, arrow.get("tail", (0.3, 0.3)),
                                            arrow.get("tip", (0.5, 0.5)))
            merged = {**base, **arrow, "head": head}
            merged["tail"] = (float(merged["tail"][0]), float(merged["tail"][1]))
            merged["tip"] = (float(merged["tip"][0]), float(merged["tip"][1]))
            self.add_arrow(state=merged)

        for key in list(self.note_state):          # replace the text boxes
            self.remove_note(key)
        for note in state.get("notes") or []:
            position = note.get("pos") or (0.5, 0.5)
            self.add_note(position, state={
                **self.default_note_state(position),
                **{k: v for k, v in note.items() if k != "pos"},
                "pos": (float(position[0]), float(position[1]))})

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
                          color=safe_hex(self.fonts["title_color"], "#000000"),
                          pad=self.points(self.fonts["title_pad"]))
        self.ax.set_xlabel(x_col)
        self.ax.set_ylabel(str(plot_cfg["y_label"]))
        for which in ("x", "y"):
            self.apply_axis(which, {**self.axis_cfg[which],
                                    "label": self.axis_label(which)}, redraw=False)
        self.apply_frame(self.frame_cfg, redraw=False)
        for text in (self.ax.title, self.ax.xaxis.label, self.ax.yaxis.label):
            text.set_picker(True)
        # remember the automatic placement: the drag offsets sit on top of it
        self._text_base = {"title": self.ax.title.get_transform(),
                           "x": self.ax.xaxis.label.get_transform(),
                           "y": self.ax.yaxis.label.get_transform()}

    def _reapply_distances(self):
        """Turn the stored pixel distances into points for the current dpi."""
        for which in ("x", "y"):
            axis = self.ax.xaxis if which == "x" else self.ax.yaxis
            axis.labelpad = self.points(self.axis_cfg[which]["label_pad"])
            self.ax.tick_params(axis=which, which="both",
                                pad=self.points(self.axis_cfg[which]["tick_pad"]))
        self.ax.set_title(self.ax.get_title(), fontsize=self.fonts["title"],
                          color=safe_hex(self.fonts["title_color"], "#000000"),
                          pad=self.points(self.fonts["title_pad"]))
        self.ax.title.set_picker(True)
        self.apply_text_offsets()

    def _on_resize(self, _event=None):
        """The Tk canvas may change the resolution: keep the pixels honest."""
        dpi = self.fig.get_dpi()
        if abs(dpi - self._dpi) > 0.01:
            self._dpi = dpi
            self._reapply_distances()
        # circles keep their shape and the arrow heads their size only if the
        # geometry is rebuilt for the new aspect ratio
        self.refresh_shapes()
        self.refresh_arrows()
        self._refresh_highlight()
        self.draw()

    def _connect_events(self):
        self._dpi = self.fig.get_dpi()
        self.canvas.mpl_connect("resize_event", self._on_resize)
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
        if self.selection is not None and self.selection[0] == "legend":
            if self.selection[1] not in self.legends:
                self.select_object(None, None)
            else:
                self._refresh_highlight()

    # -- drawn objects (rectangle, triangle, circle, ellipse) --------------
    def arm_shape_drawing(self, kind=None, armed=None):
        """Wait for a press-drag in the diagram and draw a shape there."""
        if kind is not None:
            self.shape_kind = kind
            self.settings.set("shape", "kind",
                              name_of(SHAPE_KINDS, kind, "Rectangle"))
            try:                       # remember it for the next start as well
                self.settings.save()
            except OSError:
                pass
            self.shape_button.set_shape(kind)
        wanted = (not self._pending_shape) if armed is None else armed
        self._pending_shape = bool(wanted)
        if self._pending_shape:                  # only one tool at a time
            self.arm_text_placement(False)
            self.arm_arrow_drawing(armed=False)
        widget = self.canvas.get_tk_widget()
        try:
            self.shape_button.set_active(self._pending_shape)
            widget.configure(cursor="tcross" if self._pending_shape else "")
            self.toolbar.set_message(
                "Draw: press and drag in the diagram" if self._pending_shape else "")
        except (tk.TclError, AttributeError):
            pass
        if not self._pending_shape:
            self._cursor = ""
        return self._pending_shape

    def show_shape_menu(self, event=None):
        """The popup list of the drawing objects."""
        menu = tk.Menu(self, tearoff=0)
        for label, code in SHAPE_KINDS:
            menu.add_command(label=label,
                             command=lambda c=code: self.arm_shape_drawing(c, True))
        try:
            x = self.shape_button.winfo_rootx()
            y = self.shape_button.winfo_rooty() + self.shape_button.winfo_height()
            menu.tk_popup(x, y)
        finally:
            menu.grab_release()
        return menu

    def default_shape_state(self, kind, x, y, width=0.0, height=0.0):
        cfg = self.settings.section("shape")
        return {
            "kind": kind, "x": float(x), "y": float(y),
            "w": float(width), "h": float(height), "angle": 0.0,
            "style": code_of(LINE_STYLES, cfg["line_style"], "-"),
            "width": float(cfg["line_width"]),
            "edge": safe_hex(cfg["line_color"], "#000000"),
            "face": ("none" if cfg["no_fill"]
                     else safe_hex(cfg["fill_color"], "#cfe3f7")),
            "alpha": float(cfg["fill_alpha"]),
        }

    def add_shape(self, kind=None, position=(0.4, 0.4), size=(0.2, 0.15),
                  state=None):
        self._shape_counter += 1
        key = f"shape{self._shape_counter}"
        self.shape_state[key] = state or self.default_shape_state(
            kind or self.shape_kind, position[0], position[1], size[0], size[1])
        self.refresh_shape(key)
        self.draw()
        return key

    def remove_shape(self, key):
        patch = self.shapes.pop(key, None)
        if patch is not None:
            patch.remove()
        self.shape_state.pop(key, None)
        if self.selected_shape == key:
            self.select_shape(None)
        dialog = self._dialogs.pop(f"shape-{key}", None)
        if dialog is not None and dialog.winfo_exists():
            dialog.destroy()
        self.draw()

    def _axes_aspect(self):
        box = self.ax.get_window_extent()
        return (box.width / box.height) if box.height else 1.0

    def refresh_shape(self, key):
        """Build the patch of one drawn object from its state."""
        patch = self.shapes.pop(key, None)
        if patch is not None:
            patch.remove()
        state = self.shape_state.get(key)
        if state is None:
            return None
        x, y = state["x"], state["y"]
        w = max(MIN_SHAPE_SIZE, state["w"])
        h = max(MIN_SHAPE_SIZE, state["h"])
        if state["kind"] == "circle":      # keep it round on the screen
            h = w * self._axes_aspect()
            state["h"] = h
        face = state.get("face", "none")
        common = {
            "transform": self._shape_transform(state),
            "clip_on": False, "zorder": 5,
            "edgecolor": state["edge"], "linestyle": state["style"],
            "linewidth": state["width"],
            "facecolor": ("none" if face == "none"
                          else to_rgba(face, state.get("alpha", 0.6))),
        }
        if state["kind"] == "triangle":
            patch = Polygon([[x + w / 2, y + h], [x, y], [x + w, y]],
                            closed=True, **common)
        elif state["kind"] in ("circle", "ellipse"):
            patch = Ellipse((x + w / 2, y + h / 2), w, h, **common)
        else:
            patch = Rectangle((x, y), w, h, **common)
        self.ax.add_patch(patch)
        self.shapes[key] = patch
        if self.selected_shape == key:
            self._refresh_handles()
        return patch

    def refresh_shapes(self):
        for key in list(self.shape_state):
            self.refresh_shape(key)

    # -- rotation ----------------------------------------------------------
    @staticmethod
    def angle_of(state):
        try:
            return float(state.get("angle", 0.0) or 0.0)
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def shape_centre(state):
        return (state["x"] + state["w"] / 2.0, state["y"] + state["h"] / 2.0)

    def _rotation(self, centre, angle):
        """Turn by `angle` degrees around `centre`, measured on the screen."""
        px, py = self.ax.transAxes.transform(centre)
        return Affine2D().rotate_deg_around(float(px), float(py), float(angle))

    def _shape_transform(self, state):
        """Axes coordinates plus the rotation of that object, in pixels.

        Rotating in pixels (and not in axes coordinates) keeps the object
        undistorted whatever the proportions of the plot area.
        """
        angle = self.angle_of(state)
        if not angle:
            return self.ax.transAxes
        return self.ax.transAxes + self._rotation(self.shape_centre(state), angle)

    def _turn_point(self, point, centre, angle):
        """One point of the plot area turned around `centre`."""
        if not angle:
            return (float(point[0]), float(point[1]))
        base = self.ax.transAxes
        turned = self._rotation(centre, angle).transform(base.transform(point))
        back = base.inverted().transform(turned)
        return (float(back[0]), float(back[1]))

    def rotation_centre(self):
        """The point the selected object turns around, in axes coordinates."""
        kind, key = self.selection or (None, None)
        if kind == "shape" and key in self.shape_state:
            return self.shape_centre(self.shape_state[key])
        if kind == "note" and key in self.note_state:
            return tuple(self.note_state[key]["pos"])
        return None

    def rotation_handle_position(self):
        """Where the round rotation control point sits, or None."""
        kind, key = self.selection or (None, None)
        centre = self.rotation_centre()
        if centre is None:
            return None
        base = self.ax.transAxes
        if kind == "shape":
            state = self.shape_state[key]
            top = self.shape_handle_positions(state)[6]     # top, middle
            start = np.array(base.transform(centre), dtype=float)
            end = np.array(base.transform(top), dtype=float)
            vector = end - start
            length = float(np.hypot(*vector))
            if length < 1e-6:
                return None
            point = end + vector / length * ROTATE_GAP
        else:
            artist = self.notes.get(key)
            if artist is None:
                return None
            try:
                box = artist.get_window_extent(self._renderer())
            except (RuntimeError, ValueError, AttributeError, TypeError):
                return None
            point = np.array([(box.x0 + box.x1) / 2.0, box.y1 + ROTATE_GAP])
        back = base.inverted().transform(point)
        return (float(back[0]), float(back[1]))

    def rotate_selection(self, angle, snap=False):
        """Turn the selected drawing or text box to `angle` degrees."""
        kind, key = self.selection or (None, None)
        state = self.selected_state()
        if state is None or kind not in ("shape", "note"):
            return False
        if snap:
            angle = round(angle / ROTATE_SNAP) * ROTATE_SNAP
        state["angle"] = float(angle) % 360.0
        if kind == "shape":
            self.refresh_shape(key)
        else:
            self.refresh_note(key)
        self._refresh_handles()
        self._refresh_highlight()
        self.draw()
        return True

    def _pointer_angle(self, event, centre):
        point = np.array(self.ax.transAxes.transform(centre), dtype=float)
        vector = np.array([event.x, event.y], dtype=float) - point
        if float(np.hypot(*vector)) < 1e-6:
            return None
        return float(np.degrees(np.arctan2(vector[1], vector[0])))

    # -- arrows ------------------------------------------------------------
    def arm_arrow_drawing(self, head=None, armed=None):
        """Wait for a press-drag in the diagram and draw an arrow there."""
        if head is not None:
            self.arrow_head = head
            self.settings.set("arrow", "head",
                              name_of(ARROW_HEADS, head, "Triangle head"))
            try:
                self.settings.save()
            except OSError:
                pass
            self.arrow_button.set_shape(head)
        wanted = (not self._pending_arrow) if armed is None else armed
        self._pending_arrow = bool(wanted)
        if self._pending_arrow:
            self.arm_text_placement(False)
            self.arm_shape_drawing(armed=False)
        widget = self.canvas.get_tk_widget()
        try:
            self.arrow_button.set_active(self._pending_arrow)
            widget.configure(cursor="tcross" if self._pending_arrow else "")
            self.toolbar.set_message(
                "Arrow: press at the tail and drag to the tip"
                if self._pending_arrow else "")
        except (tk.TclError, AttributeError):
            pass
        if not self._pending_arrow:
            self._cursor = ""
        return self._pending_arrow

    def show_arrow_menu(self, event=None):
        menu = tk.Menu(self, tearoff=0)
        for label, code in ARROW_HEADS:
            menu.add_command(label=label,
                             command=lambda c=code: self.arm_arrow_drawing(c, True))
        try:
            x = self.arrow_button.winfo_rootx()
            y = self.arrow_button.winfo_rooty() + self.arrow_button.winfo_height()
            menu.tk_popup(x, y)
        finally:
            menu.grab_release()
        return menu

    def default_arrow_state(self, head, tail, tip):
        cfg = self.settings.section("arrow")
        return {
            "head": head, "tail": (float(tail[0]), float(tail[1])),
            "tip": (float(tip[0]), float(tip[1])),
            "size": float(cfg["head_size"]),
            "style": code_of(LINE_STYLES, cfg["line_style"], "-"),
            "width": float(cfg["line_width"]),
            "color": safe_hex(cfg["color"], "#000000"),
        }

    def add_arrow(self, head=None, tail=(0.3, 0.3), tip=(0.5, 0.5), state=None):
        self._arrow_counter += 1
        key = f"arrow{self._arrow_counter}"
        self.arrow_state[key] = state or self.default_arrow_state(
            head or self.arrow_head, tail, tip)
        self.refresh_arrow(key)
        self.draw()
        return key

    def remove_arrow(self, key):
        for artist in self.arrows.pop(key, ()):
            artist.remove()
        self.arrow_state.pop(key, None)
        if self.selection == ("arrow", key):
            self.select_object(None, None)
        dialog = self._dialogs.pop(f"arrow-{key}", None)
        if dialog is not None and dialog.winfo_exists():
            dialog.destroy()
        self.draw()

    def _head_polygon(self, state):
        """Head corners in axes coordinates, built in pixels so it is true."""
        transform = self.ax.transAxes
        inverse = transform.inverted()
        tail = np.array(transform.transform(state["tail"]), dtype=float)
        tip = np.array(transform.transform(state["tip"]), dtype=float)
        direction = tip - tail
        length = float(np.hypot(*direction))
        if length < 1e-6:
            return None, state["tip"]
        unit = direction / length
        normal = np.array([-unit[1], unit[0]])
        size = min(float(state["size"]), max(4.0, length))
        half = size * 0.42
        base = tip - unit * size
        left, right = base + normal * half, base - normal * half
        kind = state["head"]
        if kind == "chevron":
            points = [left, tip, right]
        elif kind == "concave":
            points = [tip, left, base + unit * size * 0.35, right]
        elif kind == "convex":
            points = [tip, left, base - unit * size * 0.22, right]
        else:
            points = [tip, left, right]
        shaft_end = tip if kind == "chevron" else base + unit * size * 0.15
        return ([inverse.transform(point) for point in points],
                inverse.transform(shaft_end))

    def refresh_arrow(self, key):
        for artist in self.arrows.pop(key, ()):
            artist.remove()
        state = self.arrow_state.get(key)
        if state is None:
            return None
        points, shaft_end = self._head_polygon(state)
        shaft, = self.ax.plot(
            [state["tail"][0], shaft_end[0]], [state["tail"][1], shaft_end[1]],
            transform=self.ax.transAxes, color=state["color"],
            linestyle=state["style"], linewidth=state["width"],
            solid_capstyle="butt", clip_on=False, zorder=5,
            label="_nolegend_")
        artists = [shaft]
        if points is not None:
            if state["head"] == "chevron":
                head, = self.ax.plot(
                    [p[0] for p in points], [p[1] for p in points],
                    transform=self.ax.transAxes, color=state["color"],
                    linestyle="-", linewidth=state["width"],
                    solid_joinstyle="miter", clip_on=False, zorder=5,
                    label="_nolegend_")
            else:
                head = Polygon(points, closed=True, transform=self.ax.transAxes,
                               facecolor=state["color"],
                               edgecolor=state["color"],
                               linewidth=max(0.2, state["width"] * 0.5),
                               clip_on=False, zorder=5)
                self.ax.add_patch(head)
            artists.append(head)
        self.arrows[key] = artists
        if self.selection == ("arrow", key):
            self._refresh_handles()
        return artists

    def refresh_arrows(self):
        for key in list(self.arrow_state):
            self.refresh_arrow(key)

    @staticmethod
    def arrow_handle_positions(state):
        return [tuple(state["tail"]), tuple(state["tip"])]

    def arrow_at(self, x, y, tolerance=6.0):
        """Key of the arrow under the pointer, or None."""
        if x is None or y is None:
            return None
        point = np.array([x, y], dtype=float)
        for key in reversed(list(self.arrow_state)):
            state = self.arrow_state[key]
            tail = np.array(self.ax.transAxes.transform(state["tail"]))
            tip = np.array(self.ax.transAxes.transform(state["tip"]))
            segment = tip - tail
            length = float(np.hypot(*segment))
            if length < 1e-6:
                continue
            position = float(np.clip(np.dot(point - tail, segment) / length ** 2,
                                     0.0, 1.0))
            distance = float(np.hypot(*(point - (tail + position * segment))))
            if distance <= tolerance + state["width"] + state["size"] * 0.25:
                return key
        return None

    def edit_arrow(self, key):
        state = self.arrow_state.get(key)
        if state is None:
            return None

        def apply(values):
            state.update(values)
            self.refresh_arrow(key)
            self.draw()

        return self._show_dialog(f"arrow-{key}", lambda: ArrowDialog(
            self, state, apply, on_delete=lambda: self.remove_arrow(key),
            on_close=lambda _d: self._dialogs.pop(f"arrow-{key}", None)))

    # -- selection and control points --------------------------------------
    @staticmethod
    def handle_positions(state):
        x, y, w, h = state["x"], state["y"], state["w"], state["h"]
        return [(x, y), (x + w, y), (x + w, y + h), (x, y + h),
                (x + w / 2, y), (x + w, y + h / 2),
                (x + w / 2, y + h), (x, y + h / 2)]

    @property
    def selected_shape(self):
        kind, key = self.selection or (None, None)
        return key if kind == "shape" else None

    @property
    def selected_arrow(self):
        kind, key = self.selection or (None, None)
        return key if kind == "arrow" else None

    def select_shape(self, key):
        self.select_object("shape", key)

    def _selection_store(self, kind):
        return {"shape": self.shape_state, "arrow": self.arrow_state,
                "note": self.note_state, "legend": self.legend_state,
                "text": self.text_offset}.get(kind)

    def select_object(self, kind, key):
        """Remember the object the keyboard commands work on."""
        store = self._selection_store(kind)
        if store is not None and key in store:
            if kind == "text":          # only a text that is really there
                artist = self.text_artist(key)
                if artist is None or not artist.get_text():
                    kind = None
        if store is not None and key in store and kind is not None:
            self.selection = (kind, key)
        else:
            self.selection = None
        self._refresh_handles()
        self._refresh_highlight()

    def selected_state(self):
        """The dictionary of the selected object, or None."""
        kind, key = self.selection or (None, None)
        store = self._selection_store(kind)
        return None if store is None else store.get(key)

    def highlighted_artist(self):
        """The text of the selection - drawings show control points instead."""
        kind, key = self.selection or (None, None)
        if kind == "note":
            return self.notes.get(key)
        if kind == "legend":
            return self.legends.get(key)
        if kind == "text":
            artist = self.text_artist(key)
            return artist if artist is not None and artist.get_text() else None
        return None

    def is_marked(self):
        """True while a text, a label or a legend box wears the blue veil."""
        return self._marked is not None

    def _plain_look(self, marked):
        """Give one text its own appearance back."""
        kind, key = marked
        if kind == "text":
            artist = self.text_artist(key)
            if artist is not None:
                artist.set_bbox(None)
        elif kind == "note":
            self.refresh_note(key)             # rebuilt from its own state
        elif kind == "legend":
            legend, state = self.legends.get(key), self.legend_state.get(key)
            if legend is not None and state is not None:
                edge, face = state.get("edge", "none"), state.get("face", "#ffffff")
                frame = legend.get_frame()
                frame.set_alpha(1.0)
                frame.set_edgecolor("none" if edge == "none" else edge)
                frame.set_linewidth(0.0 if edge == "none" else 0.8)
                frame.set_facecolor("none" if face == "none" else face)

    def _refresh_highlight(self):
        """A light blue veil marks the selected text, label or legend box.

        The mark belongs to the artist itself, so it follows the text
        wherever matplotlib puts it - no stale pixel coordinates.
        """
        kind, key = self.selection or (None, None)
        wanted = (kind, key) if kind in ("text", "note", "legend") else None
        if self._marked is not None and self._marked != wanted:
            self._plain_look(self._marked)
            self._marked = None
        if wanted is None:
            return None
        if kind == "text":
            artist = self.text_artist(key)
            if artist is None or not artist.get_text():
                return None
            artist.set_bbox(dict(SELECT_BOX))
        elif kind == "note":
            artist = self.notes.get(key)
            if artist is None:
                return None
            patch = artist.get_bbox_patch()
            if patch is None:
                artist.set_bbox(dict(SELECT_BOX))
            else:
                patch.set_facecolor(SELECT_FACE)
                patch.set_edgecolor(SELECT_EDGE)
                patch.set_linewidth(1.0)
        else:
            legend = self.legends.get(key)
            if legend is None:
                return None
            frame = legend.get_frame()
            frame.set_alpha(None)      # let the translucent veil through
            frame.set_facecolor(SELECT_FACE)
            frame.set_edgecolor(SELECT_EDGE)
            frame.set_linewidth(1.2)
        self._marked = wanted
        return self.highlighted_artist()

    # -- clipboard, keyboard moving and deleting ---------------------------
    def _axes_delta(self, dx_pixels, dy_pixels):
        """A pixel offset as an offset in the coordinates of the plot area."""
        inverse = self.ax.transAxes.inverted()
        origin = inverse.transform((0.0, 0.0))
        moved = inverse.transform((float(dx_pixels), float(dy_pixels)))
        return (float(moved[0] - origin[0]), float(moved[1] - origin[1]))

    @staticmethod
    def _shifted_state(kind, state, dx, dy):
        """A copy of one object state moved by (dx, dy) in axes coordinates."""
        moved = copy.deepcopy(state)
        if kind == "shape":
            moved["x"] = float(moved["x"]) + dx
            moved["y"] = float(moved["y"]) + dy
        elif kind == "arrow":
            for end in ("tail", "tip"):
                moved[end] = (float(moved[end][0]) + dx,
                              float(moved[end][1]) + dy)
        else:                                   # a text box
            moved["pos"] = (float(moved["pos"][0]) + dx,
                            float(moved["pos"][1]) + dy)
        return moved

    def copy_selection(self, _event=None):
        """Ctrl/Cmd+C: keep the selected object with all of its properties."""
        kind, _key = self.selection or (None, None)
        state = self.selected_state()
        if state is None:
            self.flash("Select an object first, then copy it")
            return None
        if kind not in COPYABLE:
            self.flash(f"{OBJECT_NAMES.get(kind, kind)} cannot be copied - "
                       "text boxes, drawings and arrows can")
            return None
        PlotWindow._clipboard = {"kind": kind, "pasted": 0,
                                 "state": copy.deepcopy(state)}
        self.flash(f"{OBJECT_NAMES.get(kind, kind)} copied - "
                   f"paste it with {PASTE_HINT}")
        return kind

    def paste_clipboard(self, _event=None):
        """Ctrl/Cmd+V: another copy of it, a little beside the original."""
        data = PlotWindow._clipboard
        if not data:
            self.flash("Nothing has been copied yet")
            return None
        data["pasted"] += 1                     # repeated pastes cascade
        step = PASTE_STEP * data["pasted"]
        dx, dy = self._axes_delta(step, -step)
        kind = data["kind"]
        state = self._shifted_state(kind, data["state"], dx, dy)
        if kind == "shape":
            key = self.add_shape(state=state)
        elif kind == "arrow":
            key = self.add_arrow(state=state)
        else:
            key = self.add_note(state["pos"], state=state)
        self.select_object(kind, key)
        self.draw()
        self.flash(f"{OBJECT_NAMES.get(kind, kind)} pasted")
        return key

    def nudge_selection(self, dx_pixels, dy_pixels):
        """Move the selected object with the arrow keys."""
        kind, key = self.selection or (None, None)
        state = self.selected_state()
        if state is None:
            return False
        dx, dy = self._axes_delta(dx_pixels, dy_pixels)
        if kind == "text":
            # the title and the axis labels are shifted in pixels already
            offset = self.text_offset[key]
            self.text_offset[key] = (offset[0] + float(dx_pixels),
                                     offset[1] + float(dy_pixels))
            self.apply_text_offset(key)
        elif kind == "legend":
            position = (float(state["pos"][0]) + dx,
                        float(state["pos"][1]) + dy)
            state["pos"] = position
            legend = self.legends.get(key)
            if legend is not None:
                legend.set_bbox_to_anchor(position, transform=self.ax.transAxes)
        else:
            state.update(self._shifted_state(kind, state, dx, dy))
            if kind == "shape":
                self.refresh_shape(key)
            elif kind == "arrow":
                self.refresh_arrow(key)
            else:
                self._move_note(key, state["pos"])
        self._refresh_handles()
        self._refresh_highlight()
        self.draw()
        return True

    def delete_selection(self, _event=None):
        """Delete or Backspace: remove the selected object."""
        kind, key = self.selection or (None, None)
        remover = {"shape": self.remove_shape, "arrow": self.remove_arrow,
                   "note": self.remove_note}.get(kind)
        if remover is None:
            return False
        remover(key)
        return True

    def announce_selection(self):
        """Tell in the toolbar what is selected and what a second click does."""
        kind, _key = self.selection or (None, None)
        if kind is None:
            return
        self.flash(f"{OBJECT_NAMES.get(kind, kind)} selected - "
                   "click it again for its properties")

    def save_figure_clean(self, *_args):
        """The saved image must not contain the selection marks."""
        selection = self.selection
        self.select_object(None, None)
        try:
            self.canvas.draw()
            return self.toolbar.save_figure()
        finally:
            if selection is not None:
                self.select_object(*selection)
            self.canvas.draw_idle()

    def flash(self, message):
        """A short note in the message area of the toolbar."""
        try:
            self.toolbar.set_message(message)
            self.after(2500, lambda: self.toolbar.set_message(""))
        except (tk.TclError, AttributeError):
            pass

    def shape_handle_positions(self, state):
        """The eight control points, turned with the object."""
        points = self.handle_positions(state)
        angle = self.angle_of(state)
        if not angle:
            return points
        centre = self.shape_centre(state)
        return [self._turn_point(point, centre, angle) for point in points]

    def selected_handle_positions(self):
        kind, key = self.selection or (None, None)
        if kind == "shape" and key in self.shape_state:
            return self.shape_handle_positions(self.shape_state[key])
        if kind == "arrow" and key in self.arrow_state:
            return self.arrow_handle_positions(self.arrow_state[key])
        return None

    def _refresh_handles(self):
        points = self.selected_handle_positions()
        if self._handles is None and points is not None:
            self._handles, = self.ax.plot(
                [], [], linestyle="none", marker="s", markersize=7,
                markerfacecolor="#ffffff", markeredgecolor="#1a5fb4",
                markeredgewidth=1.2, transform=self.ax.transAxes,
                clip_on=False, zorder=8, label="_nolegend_")
        if self._handles is not None:
            if points is None:
                self._handles.set_data([], [])
            else:
                self._handles.set_data([p[0] for p in points],
                                       [p[1] for p in points])
        self._refresh_rotation_handle()

    def _refresh_rotation_handle(self):
        """The round control point that turns a drawing or a text box."""
        point = self.rotation_handle_position()
        if self._rotator is None:
            if point is None:
                return
            self._rotator, = self.ax.plot(
                [], [], linestyle="-", linewidth=0.8, color="#1a5fb4",
                marker="o", markersize=8, markerfacecolor="#ffffff",
                markeredgecolor="#1a5fb4", markeredgewidth=1.2,
                markevery=[1], transform=self.ax.transAxes,
                clip_on=False, zorder=8, label="_nolegend_")
        if point is None:
            self._rotator.set_data([], [])
            return
        centre = self.rotation_centre()
        kind, key = self.selection or (None, None)
        if kind == "shape":
            anchor = self.shape_handle_positions(self.shape_state[key])[6]
        else:
            anchor = centre
        self._rotator.set_data([anchor[0], point[0]], [anchor[1], point[1]])

    def handle_at(self, x, y, tolerance=8.0):
        """Index of the control point of the selected object, or None.

        `ROTATE_HANDLE` (8) is the round one that turns the object.
        """
        if x is None or y is None:
            return None
        for index, point in enumerate(self.selected_handle_positions() or ()):
            px, py = self.ax.transAxes.transform(point)
            if abs(px - x) <= tolerance and abs(py - y) <= tolerance:
                return index
        point = self.rotation_handle_position()
        if point is not None:
            px, py = self.ax.transAxes.transform(point)
            if abs(px - x) <= tolerance and abs(py - y) <= tolerance:
                return ROTATE_HANDLE
        return None

    def shape_at(self, x, y):
        """Key of the drawn object under the pointer, or None."""
        if x is None or y is None:
            return None
        for key in reversed(list(self.shapes)):        # topmost first
            patch = self.shapes[key]
            try:
                inside = patch.get_path().contains_point(
                    (x, y), patch.get_transform(),
                    radius=max(3.0, patch.get_linewidth()))
            except (ValueError, AttributeError):
                continue
            if inside:
                return key
        return None

    OPPOSITE_HANDLE = {0: 2, 1: 3, 2: 0, 3: 1, 4: 6, 5: 7, 6: 4, 7: 5}

    def _resize_shape(self, key, index, point):
        state = self.shape_state[key]
        angle = self.angle_of(state)
        anchor_before = None
        if angle:
            # work in the frame of the object and keep the opposite control
            # point where it is on the screen
            anchor = self.OPPOSITE_HANDLE.get(index, index)
            anchor_before = self.ax.transAxes.transform(
                self.shape_handle_positions(state)[anchor])
            point = self._turn_point(point, self.shape_centre(state), -angle)
        x0, y0 = state["x"], state["y"]
        x1, y1 = x0 + state["w"], y0 + state["h"]
        if index in (0, 3, 7):
            x0 = point[0]
        elif index in (1, 2, 5):
            x1 = point[0]
        if index in (0, 1, 4):
            y0 = point[1]
        elif index in (2, 3, 6):
            y1 = point[1]
        state["x"], state["w"] = min(x0, x1), max(MIN_SHAPE_SIZE, abs(x1 - x0))
        state["y"], state["h"] = min(y0, y1), max(MIN_SHAPE_SIZE, abs(y1 - y0))
        if anchor_before is not None:
            anchor = self.OPPOSITE_HANDLE.get(index, index)
            after = self.ax.transAxes.transform(
                self.shape_handle_positions(state)[anchor])
            dx, dy = self._axes_delta(anchor_before[0] - after[0],
                                      anchor_before[1] - after[1])
            state["x"] += dx
            state["y"] += dy
        self.refresh_shape(key)

    def edit_shape(self, key):
        state = self.shape_state.get(key)
        if state is None:
            return None

        def apply(values):
            state.update(values)
            self.refresh_shape(key)
            self.draw()

        return self._show_dialog(f"shape-{key}", lambda: ShapeDialog(
            self, state, apply, on_delete=lambda: self.remove_shape(key),
            on_close=lambda _d: self._dialogs.pop(f"shape-{key}", None)))

    # -- free text boxes ---------------------------------------------------
    def arm_text_placement(self, armed=None):
        """Wait for a click in the diagram and put a new text box there."""
        self._pending_text = (not self._pending_text) if armed is None else armed
        if self._pending_text:                   # only one tool at a time
            self.arm_shape_drawing(armed=False)
            self.arm_arrow_drawing(armed=False)
        widget = self.canvas.get_tk_widget()
        try:
            if self._pending_text:
                self.text_button.configure(relief="sunken")
                widget.configure(cursor="xterm")     # a vertical line
                self.toolbar.set_message("Click in the diagram to place the text")
            else:
                self.text_button.configure(relief="flat")
                widget.configure(cursor="")
                self._cursor = ""
                self.toolbar.set_message("")
        except (tk.TclError, AttributeError):
            pass
        return self._pending_text

    def _shift_active(self, event=None):
        """True while Shift is held down (from Tk or from the mouse event)."""
        if self._shift_down:
            return True
        modifiers = getattr(event, "modifiers", None) or ()
        try:
            if "shift" in modifiers:
                return True
        except TypeError:
            pass
        return "shift" in str(getattr(event, "key", "") or "")

    def _snap_point(self, anchor, point):
        """`point` pulled onto the nearest 45 degree direction from `anchor`.

        The angles are measured on the screen, so a snapped arrow really is
        vertical, horizontal or diagonal whatever the size of the plot area.
        """
        transform = self.ax.transAxes
        start = np.array(transform.transform(anchor), dtype=float)
        end = np.array(transform.transform(point), dtype=float)
        vector = end - start
        if float(np.hypot(*vector)) < 1e-6:
            return (float(point[0]), float(point[1]))
        angle = np.round(np.arctan2(vector[1], vector[0]) / SNAP_ANGLE) * SNAP_ANGLE
        unit = np.array([np.cos(angle), np.sin(angle)])
        length = max(2.0, float(np.dot(vector, unit)))
        snapped = transform.inverted().transform(start + unit * length)
        return (float(snapped[0]), float(snapped[1]))

    def cancel_tools(self):
        """Escape: none of the three toolbar tools stays armed."""
        self.arm_text_placement(False)
        self.arm_shape_drawing(armed=False)
        self.arm_arrow_drawing(armed=False)

    def default_note_state(self, position):
        cfg = self.settings.section("text")
        return {
            "text": "Text", "pos": (float(position[0]), float(position[1])),
            "angle": 0.0,
            "size": int(cfg["size"]), "color": safe_hex(cfg["color"], "#000000"),
            "edge": ("none" if not cfg["frame"]
                     else safe_hex(cfg["edge_color"], "#000000")),
            "face": ("none" if cfg["transparent"]
                     else safe_hex(cfg["background"], "#ffffff")),
        }

    def add_note(self, position, text=None, state=None):
        """Create a text box at `position` (axes coordinates)."""
        self._note_counter += 1
        key = f"note{self._note_counter}"
        self.note_state[key] = state or self.default_note_state(position)
        if text is not None:
            self.note_state[key]["text"] = text
        self.refresh_note(key)
        self.draw()
        return key

    def remove_note(self, key):
        artist = self.notes.pop(key, None)
        if artist is not None:
            artist.remove()
        self.note_state.pop(key, None)
        if self._marked == ("note", key):
            self._marked = None
        if self.selection == ("note", key):
            self.select_object(None, None)
        dialog = self._dialogs.pop(f"note-{key}", None)
        if dialog is not None and dialog.winfo_exists():
            dialog.destroy()
        self.draw()

    def refresh_note(self, key):
        artist = self.notes.pop(key, None)
        if artist is not None:
            artist.remove()
        state = self.note_state.get(key)
        if state is None or not str(state["text"]).strip():
            return None
        edge, face = state.get("edge", "none"), state.get("face", "none")
        box = {"boxstyle": "round,pad=0.35",
               "facecolor": "none" if face == "none" else face,
               "edgecolor": "none" if edge == "none" else edge,
               "linewidth": 0.0 if edge == "none" else 0.8}
        artist = self.ax.text(state["pos"][0], state["pos"][1], state["text"],
                              transform=self.ax.transAxes,
                              fontsize=state["size"], color=state["color"],
                              ha="left", va="center", bbox=box, zorder=6,
                              rotation=self.angle_of(state),
                              rotation_mode="anchor",
                              picker=True, clip_on=False)
        self.notes[key] = artist
        if self.selection == ("note", key) and self._marked != ("note", key):
            self._refresh_highlight()
        return artist

    def refresh_notes(self):
        for key in list(self.note_state):
            self.refresh_note(key)

    def note_at(self, x, y):
        """Key of the text box under the pointer, or None."""
        if x is None or y is None:
            return None
        renderer = self._renderer()
        for key, artist in self.notes.items():
            try:
                box = artist.get_window_extent(renderer)
            except (RuntimeError, ValueError, AttributeError):
                continue
            if box.expanded(1.15, 1.4).contains(x, y):
                return key
        return None

    def edit_note(self, key):
        state = self.note_state.get(key)
        if state is None:
            return None

        def apply(values):
            state.update(values)
            if not str(state["text"]).strip():
                self.remove_note(key)
                return
            self.refresh_note(key)
            self.draw()

        return self._show_dialog(f"note-{key}", lambda: TextBoxDialog(
            self, "Text box", state["text"], state, apply, rotation=True,
            hint="An empty text deletes this box.",
            on_delete=lambda: self.remove_note(key),
            on_close=lambda _d: self._dialogs.pop(f"note-{key}", None)))

    # -- movable title and axis labels -------------------------------------
    def text_artist(self, name):
        return {"title": self.ax.title,
                "x": self.ax.xaxis.label,
                "y": self.ax.yaxis.label}.get(name)

    def _base_transform(self, name):
        """The automatic placement of a text, without any drag offset.

        set_title() builds a fresh offset transform for the title every time
        the distance changes, so that one has to be read again here.
        """
        if name == "title":
            return self.ax.transAxes + self.ax.titleOffsetTrans
        return self._text_base.get(name)

    def apply_text_offset(self, name):
        """Shift one text by its dragged offset, keeping the automatic place."""
        base = self._base_transform(name)
        artist = self.text_artist(name)
        if base is None or artist is None:
            return
        dx, dy = self.text_offset.get(name, (0.0, 0.0))
        if dx or dy:
            artist.set_transform(base + Affine2D().translate(dx, dy))
        else:
            artist.set_transform(base)
        if name == "title":
            # matplotlib keeps lifting the title above the tick labels, which
            # would cancel a vertical drag: freeze that while it is moved
            try:
                self.ax._autotitlepos = not (dx or dy)
            except AttributeError:
                pass

    def apply_text_offsets(self):
        for name in ("title", "x", "y"):
            self.apply_text_offset(name)

    def reset_text_offsets(self):
        for name in ("title", "x", "y"):
            self.text_offset[name] = (0.0, 0.0)
        self.apply_text_offsets()
        self.draw()

    def text_at(self, x, y):
        """Name of the movable text under the pointer, or None."""
        if x is None or y is None:
            return None
        renderer = self._renderer()
        for name in ("title", "x", "y"):
            artist = self.text_artist(name)
            if artist is None or not artist.get_text():
                continue
            try:
                box = artist.get_window_extent(renderer)
            except (RuntimeError, ValueError, AttributeError):
                continue
            if box.expanded(1.2, 1.5).contains(x, y):
                return name
        return None

    def _start_text_drag(self, name, event):
        if name.startswith(NOTE_KEY):
            origin = tuple(self.note_state[name[len(NOTE_KEY):]]["pos"])
        else:
            origin = tuple(self.text_offset[name])
        self._text_drag = {"name": name, "x": event.x, "y": event.y,
                           "offset": origin, "moved": False}

    def _move_note(self, key, position):
        self.note_state[key]["pos"] = (float(position[0]), float(position[1]))
        artist = self.notes.get(key)
        if artist is not None:
            artist.set_position(self.note_state[key]["pos"])

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
        x, y = self.ax.transAxes.inverted().transform((event.x, event.y))
        return (float(x), float(y))

    def _start_legend_drag(self, y_col, event):
        pos = self.legend_state[y_col]["pos"]
        point = self._axes_point(event)
        self._drag = {"column": y_col,
                      "dx": pos[0] - point[0], "dy": pos[1] - point[1]}

    def _on_motion(self, event):
        if self._shape_drag is not None:
            if event.x is None or event.y is None:
                return
            drag = self._shape_drag
            key = drag["key"]
            mode = drag["mode"]
            if mode == "rotate":
                pointer = self._pointer_angle(event, drag["centre"])
                if pointer is None:
                    return
                # the object turns by as much as the pointer did, so grabbing
                # the handle never makes it jump
                self.rotate_selection(drag["angle"] + pointer - drag["pointer"],
                                      snap=self._shift_active(event))
                return
            if mode.startswith("arrow"):
                if key not in self.arrow_state:
                    self._shape_drag = None
                    return
                point = self._axes_point(event)
                state = self.arrow_state[key]
                snap = self._shift_active(event)
                if mode == "arrow-new":
                    state["tip"] = (self._snap_point(state["tail"], point)
                                    if snap else point)
                elif mode == "arrow-end":
                    moving = "tail" if drag["index"] == 0 else "tip"
                    fixed = "tip" if drag["index"] == 0 else "tail"
                    state[moving] = (self._snap_point(state[fixed], point)
                                     if snap else point)
                else:
                    shift = (point[0] - drag["start"][0],
                             point[1] - drag["start"][1])
                    state["tail"] = (drag["tail"][0] + shift[0],
                                     drag["tail"][1] + shift[1])
                    state["tip"] = (drag["tip"][0] + shift[0],
                                    drag["tip"][1] + shift[1])
                    drag["moved"] = True
                self.refresh_arrow(key)
                self._refresh_handles()
                self.draw()
                return
            if key not in self.shape_state:
                self._shape_drag = None
                return
            point = self._axes_point(event)
            if drag["mode"] == "new":          # rubber band from the anchor
                anchor = drag["anchor"]
                state = self.shape_state[key]
                state["x"], state["w"] = min(anchor[0], point[0]), abs(point[0] - anchor[0])
                state["y"], state["h"] = min(anchor[1], point[1]), abs(point[1] - anchor[1])
                self.refresh_shape(key)
            elif drag["mode"] == "resize":
                self._resize_shape(key, drag["index"], point)
            else:
                state = self.shape_state[key]
                state["x"] = drag["origin"][0] + point[0] - drag["start"][0]
                state["y"] = drag["origin"][1] + point[1] - drag["start"][1]
                drag["moved"] = True
                self.refresh_shape(key)
            self.draw()
            return
        if self._text_drag is not None:
            if event.x is None or event.y is None:
                return
            drag = self._text_drag
            dx = event.x - drag["x"]
            dy = event.y - drag["y"]
            if abs(dx) > 2 or abs(dy) > 2:
                drag["moved"] = True
            name = drag["name"]
            if name.startswith(NOTE_KEY):     # text boxes live in axes coords
                inverse = self.ax.transAxes.inverted()
                start = inverse.transform((drag["x"], drag["y"]))
                now = inverse.transform((event.x, event.y))
                self._move_note(name[len(NOTE_KEY):],
                                (drag["offset"][0] + now[0] - start[0],
                                 drag["offset"][1] + now[1] - start[1]))
            else:
                self.text_offset[name] = (drag["offset"][0] + dx,
                                          drag["offset"][1] + dy)
                self.apply_text_offset(name)
            self._refresh_highlight()
            self.draw()
            return
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
        self._refresh_highlight()
        self.draw()

    def _on_release(self, _event):
        self._drag = None
        shape_drag, self._shape_drag = self._shape_drag, None
        if shape_drag is not None and shape_drag["mode"].startswith("arrow"):
            key = shape_drag["key"]
            state = self.arrow_state.get(key)
            if state is not None:
                if shape_drag["mode"] == "arrow-new":
                    tail = np.array(self.ax.transAxes.transform(state["tail"]))
                    tip = np.array(self.ax.transAxes.transform(state["tip"]))
                    if float(np.hypot(*(tip - tail))) < 12.0:   # a plain click
                        state["tip"] = (state["tail"][0] + 0.18,
                                        state["tail"][1])
                        self.refresh_arrow(key)
                        self._refresh_handles()
                self.draw()
            return
        if shape_drag is not None and shape_drag["mode"] == "rotate":
            self.draw()
            return
        if shape_drag is not None:
            key = shape_drag["key"]
            state = self.shape_state.get(key)
            if state is not None:
                if shape_drag["mode"] == "new" and (
                        state["w"] < 0.02 or state["h"] < 0.02):
                    state["w"] = max(state["w"], 0.18)   # a plain click
                    state["h"] = max(state["h"], 0.14)
                    self.refresh_shape(key)
                self.draw()
            return
        drag, self._text_drag = self._text_drag, None
        if drag is None:
            return
        if not drag["moved"]:      # a click that only selected: put it back
            name = drag["name"]
            if name.startswith(NOTE_KEY):
                self._move_note(name[len(NOTE_KEY):], drag["offset"])
            else:
                self.text_offset[name] = drag["offset"]
                self.apply_text_offset(name)
        self._refresh_highlight()
        self.draw()

    def _update_cursor(self, event):
        if self._pending_text or self._pending_shape or self._pending_arrow:
            return                     # the tool cursor stays until the click
        cursor = ""
        _y_col, legend = self.legend_at(event.x, event.y)
        index = self.handle_at(event.x, event.y)
        if index == ROTATE_HANDLE:
            cursor = "exchange"            # a round arrow: turn the object
        elif index is not None:
            cursor = "sizing"
        elif self.arrow_at(event.x, event.y) is not None:
            cursor = "fleur"
        elif self.shape_at(event.x, event.y) is not None:
            cursor = "fleur"
        elif self.note_at(event.x, event.y) is not None:
            cursor = "fleur"
        elif self.text_at(event.x, event.y) is not None:
            cursor = "fleur"
        elif legend is not None:
            cursor = "fleur"           # one click selects it, then it is moved
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

    # -- distances are given in pixels, matplotlib wants points ------------
    def points(self, pixels):
        return float(pixels) * 72.0 / float(self.fig.get_dpi())

    def pixels(self, points):
        return float(points) * float(self.fig.get_dpi()) / 72.0

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
        # the plot area moved: the pixel geometry of the objects is rebuilt
        self.refresh_shapes()
        self.refresh_arrows()
        self._refresh_handles()
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
        label_pad = to_float(cfg.get("label_pad"), self.fonts["axis_label_pad"])
        tick_pad = to_float(cfg.get("tick_pad"), self.fonts["tick_label_pad"])
        axis.label.set_fontsize(label_size)
        axis.label.set_color(label_color)
        axis.label.set_picker(True)
        axis.labelpad = self.points(label_pad)      # distance of the label
        ax.tick_params(axis=which, which="both", labelsize=tick_size,
                       labelcolor=tick_color, pad=self.points(tick_pad))

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
            "label_pad": label_pad, "tick_pad": tick_pad,
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
        if self._pending_text or self._pending_shape or self._pending_arrow:
            return  # waiting for the click that places the new object
        if (self.shape_at(mouse.x, mouse.y) is not None
                or self.arrow_at(mouse.x, mouse.y) is not None
                or self.handle_at(mouse.x, mouse.y) is not None):
            return  # drawn objects are handled by the press handler
        if self.legend_at(mouse.x, mouse.y)[1] is not None:
            return  # the legend boxes are handled by the press handler
        artist = event.artist
        if artist in self.notes.values() or self.note_at(mouse.x, mouse.y):
            return  # free text boxes are handled by the press handler
        # the title and the axis labels are draggable, so the press and
        # release handlers decide between moving them and editing them
        if artist in (self.ax.title, self.ax.xaxis.label, self.ax.yaxis.label):
            return
        if self.text_at(mouse.x, mouse.y) is not None or self._text_drag:
            return

        if artist in self.ax.spines.values() or self.frame_hit(mouse.x, mouse.y):
            return          # the frame is opened by a double click
        # a curve is never "selected": one click opens its properties
        if isinstance(artist, Line2D) and artist in self.lines:
            self.open_series_dialog(artist)

    def object_at(self, x, y):
        """(kind, key) of the object under the pointer, the topmost first."""
        if self.selection is not None and self.handle_at(x, y) is not None:
            return self.selection            # a control point of the selection
        key = self.arrow_at(x, y)
        if key is not None:
            return ("arrow", key)
        key = self.shape_at(x, y)
        if key is not None:
            return ("shape", key)
        key = self.note_at(x, y)
        if key is not None:
            return ("note", key)
        name = self.text_at(x, y)
        if name is not None:
            return ("text", name)
        column, legend = self.legend_at(x, y)
        if legend is not None:
            return ("legend", column)
        if self.frame_hit(x, y):
            return ("frame", "frame")
        return (None, None)

    def open_properties(self, kind, key):
        """The property window of one object, whatever kind it is."""
        if kind == "arrow":
            return self.edit_arrow(key)
        if kind == "shape":
            return self.edit_shape(key)
        if kind == "note":
            return self.edit_note(key)
        if kind == "legend":
            return self.edit_legend_entry(key)
        if kind == "text":
            return (self.edit_title() if key == "title"
                    else self.edit_axis_label(key))
        if kind == "frame":
            return self.open_axes_dialog("frame")
        return None

    def _on_double_click(self, event):
        """The second click opens the properties of the object under it."""
        kind, key = self.object_at(event.x, event.y)
        if kind is not None:
            if kind != "frame":            # the frame itself is not selected
                self.select_object(kind, key)
                self.draw()
            self.open_properties(kind, key)
            return True
        which = self._axis_hit(event)      # the numbers or the label of an axis
        if which:
            self.open_axes_dialog(which)
            return True
        return False

    def _on_button_press(self, event):
        # the keyboard focus is taken by the native <Button-1> binding of the
        # canvas widget (see take_focus), not from inside this handler
        if event.dblclick:                 # every object needs two clicks
            self._on_double_click(event)
            return
        if event.button != 1:
            return
        if self._pending_text:            # place a new text box here
            if event.x is not None and event.y is not None:
                key = self.add_note(self._axes_point(event))
                self.arm_text_placement(False)
                self.after(1, lambda k=key: self.edit_note(k))
            return
        if self._pending_shape:           # start drawing a new object
            if event.x is not None and event.y is not None:
                point = self._axes_point(event)
                key = self.add_shape(self.shape_kind, point, (0.0, 0.0))
                self._shape_drag = {"key": key, "mode": "new", "anchor": point}
                self.arm_shape_drawing(armed=False)
                self.select_shape(key)
            return
        if self._pending_arrow:           # start drawing a new arrow
            if event.x is not None and event.y is not None:
                point = self._axes_point(event)
                key = self.add_arrow(self.arrow_head, point, point)
                self._shape_drag = {"key": key, "mode": "arrow-new"}
                self.arm_arrow_drawing(armed=False)
                self.select_object("arrow", key)
            return

        index = self.handle_at(event.x, event.y)
        if index == ROTATE_HANDLE:        # turn the selected object
            kind, key = self.selection
            centre = self.rotation_centre()
            start = self._pointer_angle(event, centre)
            if centre is not None and start is not None:
                self._shape_drag = {"key": key, "mode": "rotate", "kind": kind,
                                    "centre": centre, "pointer": start,
                                    "angle": self.angle_of(self.selected_state())}
            return
        if index is not None:             # resize the selected object
            kind, key = self.selection
            self._shape_drag = {"key": key, "index": index,
                                "mode": ("arrow-end" if kind == "arrow"
                                         else "resize")}
            return
        key = self.arrow_at(event.x, event.y)
        if key is not None:               # select an arrow and drag it
            self.select_object("arrow", key)
            self.announce_selection()
            self.draw()
            state = self.arrow_state[key]
            self._shape_drag = {"key": key, "mode": "arrow-move", "moved": False,
                                "start": self._axes_point(event),
                                "tail": tuple(state["tail"]),
                                "tip": tuple(state["tip"])}
            return
        key = self.shape_at(event.x, event.y)
        if key is not None:               # select a drawing and drag it
            self.select_shape(key)
            self.announce_selection()
            self.draw()
            state = self.shape_state[key]
            self._shape_drag = {"key": key, "mode": "move", "moved": False,
                                "start": self._axes_point(event),
                                "origin": (state["x"], state["y"])}
            return
        key = self.note_at(event.x, event.y)
        if key is not None:               # select a text box and drag it
            self.select_object("note", key)
            self.announce_selection()
            self.draw()
            self._start_text_drag(f"{NOTE_KEY}{key}", event)
            return
        name = self.text_at(event.x, event.y)
        if name is not None:              # the title or an axis label
            self.select_object("text", name)
            self.announce_selection()
            self.draw()
            self._start_text_drag(name, event)
            return
        y_col, legend = self.legend_at(event.x, event.y)
        if legend is not None:            # select a legend box and drag it
            self.select_object("legend", y_col)
            self.announce_selection()
            self.draw()
            self._start_legend_drag(y_col, event)
            return
        if self.selection is not None:    # clicking elsewhere deselects
            self.select_object(None, None)
            self.draw()
        if self.frame_hit(event.x, event.y):
            self.flash("Frame - click it again for frame and origin")

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
        def apply(text, size, color, distance):
            self.fonts["title"] = size
            self.fonts["title_color"] = color
            if distance is not None:
                self.fonts["title_pad"] = distance
            self.ax.set_title(text, fontsize=size, color=color,
                              pad=self.points(self.fonts["title_pad"]))
            self.ax.title.set_picker(True)
            self.apply_text_offset("title")   # set_title resets the placement
            self.draw()

        return self._show_dialog("title-text", lambda: TextStyleDialog(
            self, "Plot title", self.ax.get_title(), self.fonts["title"], apply,
            color=safe_hex(self.fonts["title_color"], "#000000"),
            distance=self.fonts["title_pad"],
            distance_label="Distance from the axes [px]:",
            hint="The distance is measured from the top of the plot area.",
            on_close=lambda _d: self._dialogs.pop("title-text", None)))

    def edit_axis_label(self, which):
        def apply(text, size, color, distance):
            cfg = dict(self.axis_cfg[which])
            cfg.update({"label": text, "label_size": size, "label_color": color})
            if distance is not None:
                cfg["label_pad"] = distance
            self.apply_axis(which, cfg)

        return self._show_dialog(f"label-{which}", lambda: TextStyleDialog(
            self, f"{which.upper()} axis label", self.axis_label(which),
            self.axis_cfg[which]["label_size"], apply,
            color=self.axis_cfg[which]["label_color"],
            distance=self.axis_cfg[which]["label_pad"],
            distance_label="Distance from the axis [px]:",
            hint="The colour and the distance of the numbers are on the\n"
                 "axis tab of the axes properties dialog.",
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

        return self._show_dialog(f"legend-{column}", lambda: TextBoxDialog(
            self, f"Legend of '{column}'", line.get_label(), state, apply,
            hint="An empty text hides this legend box.",
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

Every text, label, axis and object reacts to the mouse, and all of them
follow the same rule:

> **One click selects, a second click opens the properties.**

A selected object can be moved with the pointer or with the arrow keys,
copied, pasted and deleted, so a whole diagram can be arranged without
opening a single dialog.  What is selected is always visible:

* a **text** - the title, an axis label, a legend box or a text box - is
  covered with a light **blue veil** in a blue frame,
* a **drawing** or an **arrow** shows its **control points** instead,
* clicking an empty part of the diagram deselects everything.

The single exception is a **curve**: it is never selected, because there is
nothing to move or copy on it, so one click on a curve opens its
properties at once.

| Action | Result |
| --- | --- |
| Click a curve | Curve properties at once: line and marker settings separately. |
| Click the title, an axis label, a legend box, a text box, a drawing or an arrow | Selects it (a text turns blue, a drawing shows control points). |
| Click the selected object again | Its property window: text, font, colours, distances - whatever belongs to that object. |
| Drag any selected-able object | Moves it (the title, the axis labels, the legend boxes, text boxes, drawings and arrows all move freely). |
| Drag a control point | Resizes a drawing, or moves the tip or the tail of an arrow. |
| Drag the round control point above a drawing or a text box | Turns it around its centre (a text box around its own anchor); `Shift` keeps 15 degree steps. |
| Arrow keys | Move the selected object by one pixel, with `Shift` by ten. |
| `Ctrl/Cmd+C`, `Ctrl/Cmd+V` | Copies the selected text box, drawing or arrow with all of its properties and pastes another copy of it. |
| `Delete` / `Backspace` | Removes the selected text box, drawing or arrow. |
| Click the frame (any axis line) twice | Frame and origin settings. |
| Click twice beside an axis (on the numbers or the label) | Axes properties, opened on the tab of that axis. |
| Hold Shift while drawing or resizing an arrow | Keeps the arrow horizontal, vertical or at 45, 135, 225, 315 degrees. |
| Plot menu | The axes dialog (axes, frame and origin), the title/fonts dialog, copy, paste and delete of the selected object, plus closing this diagram. |
| Toolbar | The standard Matplotlib toolbar (pan, zoom, saving the figure as an image), the **T** button that adds a text box, the drawing tool and the arrow tool. |

The blue veil and the control points are only on the screen: they are left
out of the image that the save button of the toolbar writes.

### Drawing rectangles, triangles, circles and ellipses

The button next to **T** is the drawing tool.  Its icon shows the shape
that will be drawn, with a small arrow in its lower right corner:

* clicking the **icon** starts drawing with the shape that is shown (a
  rectangle at the first start, later whatever was used last),
* clicking the **arrow** opens the list `Rectangle`, `Triangle`, `Circle`,
  `Ellipse`; after choosing one the tool is armed with it and the icon
  changes to that shape.

While the tool is armed the button stays pressed and the pointer becomes a
cross.  Press in the diagram and drag: the object is drawn between the
press and the release point with the default line and fill.  A plain click
without dragging gives an object of a comfortable default size.  `Esc` or
clicking the icon again cancels.

An object that was drawn behaves like the other decorations:

* it is **selected** by one click, and eight small square **control
  points** appear on its corners and on the middle of its sides; dragging
  one of them **resizes** the object (the pointer becomes a resize cross),
* dragging the object itself **moves** it, and so do the arrow keys,
* a **second click** opens its **properties**: line style (solid, dashed,
  dash-dot, dotted, none), line thickness, line colour, fill colour with an
  opacity, or `No fill (outline only)`, and a `Delete` button,
* clicking an empty part of the diagram deselects it,
* a circle keeps its round shape: its height follows its width and the
  proportions of the plot area,
* it can be **turned** to any angle: see below.

The positions and sizes are kept in the coordinates of the plot area, so
the objects follow the diagram when the window is resized, and they are
stored in `.aplt` files.  The starting line and fill of new objects come
from the `Drawings` tab of the settings.

### Turning the drawings and the text boxes

A selected drawing shows one more control point: a **round** one on a short
line above it.  Dragging that point turns the object around its centre, and
holding **Shift** while dragging keeps the angle in 15 degree steps.  A
selected text box has the same round point above it and turns around its
own anchor, so it stays where it was put.

The exact angle is in the property window of the object as
`Rotation > Angle [deg]`, with an `Upright` button that puts it back to
zero.  Angles are counted counter-clockwise and any value is accepted;
negative angles and angles above 360 are wrapped.

The rotation is measured on the **screen**, so an object keeps its shape
and its size whatever the proportions of the plot area: a rectangle stays a
rectangle with square corners, a circle stays round, and a text stays
readable.  Everything else keeps working on a turned object:

* the eight square control points turn with it, and dragging one of them
  keeps the opposite corner exactly where it is,
* the pointer finds the object where it is really drawn, so a turned
  rectangle is not clicked by the empty corner beside it,
* moving with the pointer or with the arrow keys, copying, pasting and
  deleting leave the angle alone - a copy is turned like its original,
* the angle is stored in `.aplt` files (older files simply open upright).

### Arrows

The third button of the group is the arrow tool.  Its icon is an arrow head
pointing to the right - the head that will be drawn - with the same small
arrow in its lower right corner:

* clicking the **icon** arms the tool with the head that is shown (a
  triangle head at the first start, later whatever was used last),
* clicking the **arrow** in the corner opens the list `Triangle head`,
  `Chevron head`, `Concave head`, `Convex head`; the icon changes to the
  chosen one.

Press in the diagram at the **tail** of the arrow and drag: the arrow
follows the pointer, so its length and its direction are drawn immediately,
and it is finished by releasing the button at the **tip**.  A plain click
without dragging gives a short horizontal arrow.  `Esc` or clicking the
icon again cancels.

Holding **Shift** while the arrow is drawn - or later while its tip or tail
is dragged - snaps it to the nearest 45 degrees, so it becomes exactly
horizontal, exactly vertical or an exact diagonal (45, 135, 225, 315
degrees).  The angle is measured on the screen, so the arrow really looks
that way whatever the proportions of the plot area.  The end that is not
dragged stays where it is.

An arrow behaves like the drawn objects:

* it is **selected** by one click, and two **control points** appear, one on
  the tip and one on the tail; dragging either of them changes the length,
  the direction and the position of that end,
* dragging the shaft or the head **moves** the whole arrow (the arrow keys
  move it by one pixel, with `Shift` by ten),
* a **second click** opens its **properties**: the arrow head
  (`Triangle`, `Chevron`, `Concave`, `Convex`), the head size in pixels,
  the line style, the line thickness, the colour and a `Delete` button,
* clicking an empty part of the diagram deselects it.

The tip and the tail are kept in the coordinates of the plot area, so the
arrows follow the diagram when the window is resized, while the head keeps
its size in pixels.  They are stored in `.aplt` files, and the head, size,
line and colour of new arrows come from the `Arrows` tab of the settings.

### Selecting, copying, moving and deleting the objects

One click selects; what is selected is shown by the **blue veil** on a text
(the title, an axis label, a legend box, a text box) or by the **control
points** of a drawing or an arrow.  Everything that is selected can then be
worked on from the keyboard:

| Keys | What happens |
| --- | --- |
| `Ctrl+C` / `Cmd+C` | The selected object goes to the clipboard with every one of its properties. |
| `Ctrl+V` / `Cmd+V` | Another copy appears a little to the lower right of the original and is selected; each further paste steps further, so a series of copies does not pile up. |
| Left / Right / Up / Down | Moves the selected object by one pixel. |
| `Shift` + an arrow key | Moves it by ten pixels. |
| `Delete` or `Backspace` | Removes it. |

The same commands are in the `Plot` menu as `Copy object`, `Paste object`
and `Delete object`.

The keys always belong to the window that was clicked last, so after a
property window has been used, **one click anywhere in the diagram** brings
them back - the click also keeps or changes the selection, so nothing is
lost.  The property window stays open while this happens.

Copying, pasting and deleting work on **text boxes, drawings and arrows**.
The title, the axis labels and the legend boxes belong to the diagram and
are not copied or deleted - but they are selected and moved with the arrow
keys just like everything else.

So a circle that has its final line style, thickness, line colour, fill and
opacity does not have to be built again: select it, `Ctrl/Cmd+C`, then
`Ctrl/Cmd+V` as many times as needed and move the copies where they belong
- with the pointer or with the arrow keys.  The same holds for arrows (head
type, head size, thickness, colour) and for text boxes (text, font, frame,
background).

The clipboard belongs to the program, not to one window, so an object can
be copied in one diagram and pasted into another one.  It is not the
clipboard of the operating system: `Ctrl/Cmd+C` in the diagram does not
disturb text that was copied elsewhere.

### Text boxes on the diagram

The **T** button on the right end of the toolbar, a little apart from the
save button, adds free text to the diagram:

1. press **T** - the button stays pressed and the pointer becomes a
   vertical line,
2. click in the diagram where the text should be - a text box appears there
   and its dialog opens,
3. type the text and press `OK`.

`Esc` or pressing **T** again cancels the placement without adding
anything.

A text box behaves like a legend box:

* **click** it to select it - it turns blue - and **drag** it with the
  pointer to move it (the pointer becomes a move cross over it), or move it
  with the arrow keys,
* **click it again** to open its dialog: text, font size, font colour, the
  frame around it (its colour, or no frame) and the background (a colour,
  or fully transparent),
* `Delete` in that dialog - or an empty text - removes the box,
* **turn** it with the round handle above it or with `Angle [deg]` in its
  dialog; it turns around its own anchor point, so it stays in place,
* the position is kept in the coordinates of the plot area, so the box
  follows the diagram when the window is resized,
* any number of text boxes can be added, and they are all stored in
  `.aplt` files.

The starting font, frame and background of new boxes come from the
`Text boxes` tab of the settings.

### Moving the title and the axis labels

The title and both axis labels can be dragged with the pointer, just like
the legend boxes: press on the text, move it, release it.  The pointer
becomes a move cross over them.  Pressing and releasing without moving is a
click, so it only selects the text (it turns blue); the second click opens
its dialog.  A selected label also moves with the arrow keys, one pixel at
a time, or ten with `Shift` - handy for the last bit of fine tuning.

The drag is stored as a shift in pixels **on top of** the automatic
placement, which has two useful consequences:

* the text keeps following the diagram - it stays in place when the window
  is resized, when the axes are moved in `Frame and origin`, or when longer
  numbers appear next to the axis,
* the **distance** setting still works: it moves the text with respect to
  the axis, and the drag is added to that.

`Plot > Title and fonts... > Reset dragged texts` puts the title and both
labels back to their automatic places.

### Legend boxes

Every curve has its **own** legend box, so they can be placed
independently.

* Click a box anywhere - on its frame or on its text - to select it: it is
  covered with the blue veil.  Then drag it to a new place with the
  pointer, or move it with the arrow keys (`Shift`: ten pixels).
* Click the selected box again to open its own dialog: the text, the font
  size and the font colour, the **frame** around the box (its colour, or no
  frame at all) and the **background** (its colour, or fully transparent).
  An empty text hides the box.
* The boxes keep their position when the data is updated, when the curve
  style changes and when a column is renamed, and they are stored in
  `.aplt` files.
* `Plot > Title and fonts...` sets one font size for every box, the corner
  where new boxes start, and can stack all boxes again with
  `Reset positions`.

### The property windows

The dialogs (curve properties, axes properties, title and fonts, legend)
are ordinary windows:

* they open **next to** the diagram window, not on top of it (to the right
  if there is room on the screen, otherwise to the left),
* the diagram can be **clicked in front of them** while they stay open, so
  a change can be looked at without a dialog covering the curves,
* clicking the same curve, axis or legend twice again brings its window
  back to the front,
* they stay open until they are closed, and several of them can be open at
  the same time.

If the old behaviour is preferred, `Property windows always on top` in the
`Windows` tab of the settings keeps them above the diagram again.

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

* **Axis label and fonts**: the label text, the font size, font colour and
  **distance** of the label, and the font size, font colour and
  **distance** of the numbers (ticks).  Both distances are given in pixels
  and are measured from the axis (from the end of the tick marks in the
  case of the numbers); larger values push the text away from the diagram,
  negative values pull it inwards.  The colour of the tick *marks* is not
  set here - it belongs to the frame, so a black frame can carry grey
  numbers.
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

Every text around the diagram has a **distance** in pixels next to its font
size and colour: the title from the top of the plot area, the axis labels
from their axis, and the axis numbers from the end of the tick marks.  The
values are converted to the units matplotlib works in with the resolution
of the figure, so a distance of 10 px really is ten pixels on the screen.

Font **size**, font **colour** and **distance** can be set in three places,
always together:

* the **title**: click it on the diagram, or use
  `Plot > Title and fonts...`,
* the **axis labels** and the **axis numbers**: click the label (label text,
  size and colour), or use the matching tab of the axes dialog (label and
  numbers, size and colour),
* the **legend boxes**: click the text of a box for that box alone, the
  curve properties dialog for the same box, or
  `Plot > Title and fonts...` for all of them at once (legend boxes have no
  distance: they are placed by dragging them).

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
* the title with its font size, colour and distance, the dragged positions
  of the title and of both axis labels, and the visibility, starting
  corner, default font size and colour of the legend boxes,
* both axes: label, the size, colour and distance of the label and of the
  numbers, automatic or fixed range, step, number of minor ticks, and the
  grid settings of the axis,
* the frame: style, thickness, colour, major and minor tick length, the
  background of the plot area and of the window, and the size and origin of
  the axes inside the window,
* every text box with its text, position, angle, font, frame and background,
* every drawn object with its shape, position, size, angle, line and fill,
* every arrow with its head type and size, tip, tail, line and colour,
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
| Windows | Start size of the main window and of the diagram windows, and whether the property windows stay above the diagram. |
| Spreadsheet | Number of rows and column names at start, column width, font size, automatic row adding. |
| Plot | Figure size and resolution, the title pattern (`{x}` is the name of the X column), default Y label, default line style and width, default marker, size and edge width, hollow markers, legend visibility, starting corner, frame and background of the legend boxes, and the default fill under the curves (colour, opacity, pattern, baseline). |
| Fonts | Size and colour of the title, the axis labels, the axis numbers and the legend boxes, and the starting distance (in pixels) of the title, the axis labels and the axis numbers. |
| Grid | Default grid: major and minor lines, colour, style, width, number of minor ticks. |
| Frame | Default frame style, thickness, colour, tick lengths, background colours, and the default size and origin of the axes (as fractions of the window). |
| Text boxes | Font size and colour, frame and background of the text boxes added with the **T** button. |
| Drawings | The shape the drawing tool starts with, and the line style, thickness, colour, fill colour and opacity of new objects. |
| Arrows | The head type the arrow tool starts with, the head size in pixels, and the line style, thickness and colour of new arrows. |
| Data files | Field separator and decimal sign of text data files (`auto` recognises them). |

Window sizes and plot defaults are used by windows opened after saving;
diagrams that are already open keep their settings.


## 5. Typical workflow

1. `Random data`, `Open data file` or type the numbers by hand.
2. Rename the columns by clicking their headings - these names become the
   legend texts and the X axis label.
3. `Plot`.
4. Click the curves, and click the labels and the axes twice, until the
   diagram looks right,
   and drag the legend boxes where they do not cover the data.  Add text
   boxes, drawings and arrows to point out what matters - style one of them
   and copy it (`Ctrl/Cmd+C`, `Ctrl/Cmd+V`) instead of building the next
   one from the beginning.
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
* The keyboard follows the click: the diagram takes it on every click in
  the plot area (this is done by Tk itself, not through matplotlib's event
  loop, so it is not lost when a property window has been used), and a
  property window gives it back to the diagram when it is closed.
* A curve whose properties are needed is clicked once; everything else
  needs two clicks, because the first one selects it.  This is what makes
  moving, copying and the arrow keys possible on all of those objects.
* The three tools of the toolbar (**T**, the shape and the arrow button)
  are exclusive: arming one cancels the others, and `Esc` cancels all of
  them.
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
            plot_menu.add_command(label="Copy object",
                                  accelerator=f"{ACCEL_NAME}+C",
                                  command=plot.copy_selection)
            plot_menu.add_command(label="Paste object",
                                  accelerator=f"{ACCEL_NAME}+V",
                                  command=plot.paste_clipboard)
            plot_menu.add_command(label="Delete object", accelerator="Del",
                                  command=plot.delete_selection)
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
