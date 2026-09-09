#!/usr/bin/env python3
"""
APlot - Data Visualizer
=======================

A Tkinter application to edit tabular data and plot it interactively with
Matplotlib.

Spreadsheet window
------------------
* toolbar: Plot / Update plot / four coloured row and column icons (blue
  adds, red deletes; the two adding ones are split buttons that insert
  above/below and before/after the selected cell) / Settings
* a check button above every column: only the ticked columns are plotted
  (a newly opened file starts with all of them ticked)
* a highlighted block of cells: click and drag, Shift+click, Shift+arrows,
  Shift+Space (rows), Ctrl/Cmd+Space (columns), Ctrl/Cmd+A (everything)
* a click on a column letter (A, B, C, ...) takes the whole column, a click
  on a row number (1, 2, 3, ...) the whole row, the corner the whole table
* the block is copied (Ctrl/Cmd+C), pasted (Ctrl/Cmd+V), cut (Ctrl/Cmd+X),
  emptied (Delete) and its rows deleted with one button
* the black square of the selection pulls a value down as a copy, and two
  or more selected numbers down as a series (1, 3 -> 5, 7, 9, ...)
* empty cells break the curves instead of connecting over them, so a range
  of data can be plotted in separate pieces
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
* nine plot styles, each with its own settings: line + symbol, line,
  scatter, bar chart, error bar, histogram, stairs, 2D histogram and pie
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
  drawing tool next to it adds rectangles, triangles, circles, ellipses
  and lines
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
* click an axis line        -> a control point on each of its two ends:
                              drag one to make that axis longer or shorter
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

import ast
import copy
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import tkinter as tk
from pathlib import Path
from tkinter import ttk, filedialog, colorchooser, messagebox, simpledialog
from tkinter import font as tkfont

import numpy as np
import pandas as pd

import matplotlib
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.colors import to_hex, to_rgba
from matplotlib.figure import Figure
from matplotlib.legend import Legend
from matplotlib.legend_handler import HandlerTuple
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

PLOT_STYLES = [
    ("Line + Symbol", "line_symbol", "Curves with markers (points and line)"),
    ("Line", "line", "Continuous curve without markers"),
    ("Scatter", "scatter", "Discrete symbols/markers only"),
    ("Bar Chart", "bar", "Vertical bar chart"),
    ("Error Bar", "errorbar", "Points with vertical error bars and caps"),
    ("Histogram", "histogram", "Counts the values of a column into bins"),
    ("Stairs", "stairs", "A stepped outline of the values (ax.stairs)"),
    ("2D Histogram", "hist2d", "Counts the X/Y pairs in a grid (ax.hist2d)"),
    ("Pie Chart", "pie", "The values of one column as slices (ax.pie)"),
]

ERROR_SOURCES = [
    ("Next column (x, mean, std)", "pair"),
    ("Percentage (%)", "percent"),
    ("Fixed value", "fixed"),
    ("Standard deviation", "std"),
    ("From column...", "column"),
]

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

# where a stairs plot puts the step between two X values
STAIRS_EDGES = [("Midway between the X values", "mid"),
                ("At the X value (step after it)", "post"),
                ("At the X value (step before it)", "pre")]

# the colour scales of a 2D histogram and of the slices of a pie
COLOR_MAPS = [
    ("Viridis", "viridis"), ("Plasma", "plasma"), ("Inferno", "inferno"),
    ("Magma", "magma"), ("Cividis", "cividis"), ("Turbo", "turbo"),
    ("Blues", "Blues"), ("Reds", "Reds"), ("Greens", "Greens"),
    ("Oranges", "Oranges"), ("Purples", "Purples"), ("Greys", "Greys"),
    ("Hot", "hot"), ("Cool", "cool"), ("Jet", "jet"),
    ("Coolwarm", "coolwarm"), ("Spectral", "Spectral"),
    ("Rainbow", "rainbow"), ("Tab10 (distinct colours)", "tab10"),
    ("Tab20 (distinct colours)", "tab20"), ("Pastel", "Pastel1"),
]

# what is written beside the slices of a pie
PIE_LABELS = [("The text of the first column", "column"),
              ("The row number", "row"), ("Nothing", "none")]

HIST2D_BINS = 20           # the grid of a 2D histogram, per axis
MAX_HIST2D_BINS = 500
PIE_START_ANGLE = 90.0     # the first slice starts at the top

FRAME_STYLES = [
    ("No frame (X and Y only) (default)", "none"),
    ("Full frame", "box"),
    ("Frame with ticks (inward)", "box_in"),
    ("Frame with ticks (outward)", "box_out"),
]

# matplotlib's own subplot position: left, bottom, width, height
DEFAULT_POSITION = (0.13, 0.125, 0.775, 0.77)
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
               ("Circle", "circle"), ("Ellipse", "ellipse"), ("Line", "line")]
OPEN_SHAPES = ("line",)     # drawings that are a stroke, not an area

ARROW_HEADS = [("Triangle head", "triangle"), ("Chevron head", "chevron"),
               ("Concave head", "concave"), ("Convex head", "convex")]
# corners first, then the middle of the sides
HANDLE_COUNT = 8
ROTATE_HANDLE = 8           # the round control point above the object
ROTATE_GAP = 26.0           # pixels between the object and that point
ROTATE_SNAP = 15.0          # degrees, while Shift is held
MIN_SHAPE_SIZE = 0.01       # in axes coordinates
MIN_AXIS_SIZE = 0.08        # smallest plot area, as a fraction of the figure

# copy / paste and the keyboard
OBJECT_NAMES = {"shape": "Drawing", "arrow": "Arrow", "note": "Text box",
                "legend": "Legend box", "text": "Text", "frame": "Frame",
                "axis": "Axis"}
COPYABLE = ("shape", "arrow", "note")   # a legend or an axis label is not copied
PASTE_STEP = 14.0           # pixels: how far a pasted copy sits from the original
NUDGE_STEP = 1.0            # pixels: one press of an arrow key
NUDGE_BIG_STEP = 10.0       # pixels: with Shift
SNAP_ANGLE = np.pi / 4      # arrows snap to 45 degrees while Shift is held

# texts that can be rewritten in place, the way a file is renamed in the
# Finder: one click selects, a second - slower than a double click - opens a
# little editor with the cursor where the pointer was
EDITABLE_KINDS = ("text", "note", "legend")
RENAME_DELAY = 1500         # milliseconds allowed between the two clicks
INLINE_PAD = 3              # pixels of air around the text in the editor
INLINE_MIN_WIDTH = 48       # pixels: an empty editor is still usable
INLINE_FAMILY = "DejaVu Sans"
CARET_COLOR = "#1a5fb4"     # the blinking cursor of the in-place editor
CARET_ON_MS = 600           # how long it is shown ...
CARET_OFF_MS = 350          # ... and how long it is away: it blinks
SELECT_COLOR = "#1a5fb4"    # the blue of the selection
BLOCK_TINT = "#d7e6f8"      # background of the selected spreadsheet cells
BLOCK_LINE = 2              # thickness of the outline around the block
AUTO_SCROLL_EDGE = 14       # pixels: how close to the border scrolling starts
AUTO_SCROLL_MS = 55         # how often the table scrolls on during a drag
CHECK_BAR_HEIGHT = 46       # the strip of "plot this column" check buttons and column letters
ROW_HEADER_WIDTH = 48       # width of the line numbers column on the left side of the table
# the two check buttons above every column of the table: they say which axis
# that column belongs to.  The first column feeds one of the two X axes, all
# the others one of the two Y axes - or none of them at all.
AXIS_TAGS = {
    "x": (("B", "x_B", "Bottom x-axis"), ("T", "x_T", "Top x-axis")),
    "y": (("L", "y_L", "Left y-axis"), ("R", "y_R", "Right y-axis")),
}
X_SIDES = {"B": "bottom", "T": "top"}
Y_SIDES = {"L": "left", "R": "right"}
AXIS_NAMES = {"x": "X axis", "y": "Left Y axis", "y2": "Right Y axis"}
# the four sides of the plot area, as the pointer sees them
FRAME_ENDS = {"bottom": ((0.0, 0.0), (1.0, 0.0)),
              "top": ((0.0, 1.0), (1.0, 1.0)),
              "left": ((0.0, 0.0), (0.0, 1.0)),
              "right": ((1.0, 0.0), (1.0, 1.0))}
SIDE_ALIASES = {"x": "bottom", "y": "left", "y2": "right"}
SIDE_NAMES = {"bottom": "Bottom X axis", "top": "Top X axis",
              "left": "Left Y axis", "right": "Right Y axis"}
HORIZONTAL_SIDES = ("bottom", "top")
TOOLTIP_DELAY = 250        # milliseconds before a hint pops up
TOOLTIP_BACKGROUND = "#ffffe0"
AXIS_CHECK_FONT = 10       # the x_B / x_T / y_L / y_R labels
# the column letters (A, B, C, ...) and the row numbers share it
HEADER_COLOR = "#1a5fb4"
# the letter of a column, and the number of a row, the block touches
HEADER_ACTIVE = "#d0e2fb"
LETTER_WIDTH = 56          # the clickable strip under the check buttons
# a table column is never narrower than its two check buttons
MIN_COLUMN_WIDTH = 104
FILL_HANDLE_SIZE = 6       # the black square that pulls a selection down
MAX_AUTO_COLUMNS = 64      # a blank sheet never grows past this
HISTOGRAM_BINS = 20        # a histogram counts into this many bins by default
MAX_HISTOGRAM_BINS = 1000  # ... and never into more than this
ROW_AXIS_LABEL = "Row"     # the X axis when the row number is the X value
CLIPBOARD_DPI = 200        # the picture put on the clipboard is a good one
SCRIPT_SUFFIX = ".py"      # the diagram exported as a matplotlib program
SPIN_WIDTH = 4             # characters in the little number boxes
ENTRY_WIDTH = 12           # characters in the range and style boxes
COMBO_WIDTH = 14           # characters in the style lists
SELECT_FACE = to_rgba(SELECT_COLOR, 0.18)     # veil over a selected text
SELECT_EDGE = to_rgba(SELECT_COLOR, 0.90)
SELECT_BOX = {"boxstyle": "round,pad=0.28", "facecolor": SELECT_FACE,
              "edgecolor": SELECT_EDGE, "linewidth": 1.0}
MODIFIER = "Command" if sys.platform == "darwin" else "Control"
PASTE_HINT = "Cmd+V" if sys.platform == "darwin" else "Ctrl+V"
ACCEL_NAME = "Cmd" if sys.platform == "darwin" else "Ctrl"

PALETTE_FALLBACK = "#1f77b4"


def names(table):
    """Human readable names of a (name, code, ...) table."""
    return [row[0] for row in table]


def code_of(table, name, default):
    """Matplotlib code belonging to a human readable name."""
    for row in table:
        if row[0] == name:
            return row[1]
    return default


def drawn_names(table):
    """Option names of a table without its "none" entry.

    The curve dialog switches the line, the marker, the legend and the fill on
    and off with a check button, so "None" is not offered in the lists.
    """
    return [row[0] for row in table if str(row[1]).lower() != "none"]


def name_of(table, code, default):
    """Human readable name belonging to a matplotlib code."""
    if code is None:
        code = "None"
    for row in table:
        if row[1] == code:
            return row[0]
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


def copy_png_to_clipboard(path):
    """Put a PNG file on the clipboard of the system.

    Every desktop does this its own way and none of them through Tk, so the
    small command line tool of the platform is used.  Returns True when one
    of them was there and did the work.
    """
    path = str(path)
    if sys.platform == "darwin":
        script = ('set the clipboard to '
                  f'(read (POSIX file "{path}") as \u00abclass PNGf\u00bb)')
        commands = [["osascript", "-e", script]]
    elif sys.platform.startswith("win"):
        powershell = (
            "Add-Type -AssemblyName System.Windows.Forms,System.Drawing; "
            "[System.Windows.Forms.Clipboard]::SetImage("
            f"[System.Drawing.Image]::FromFile('{path}'))")
        commands = [["powershell", "-NoProfile", "-Command", powershell]]
    else:
        commands = [["xclip", "-selection", "clipboard", "-t", "image/png",
                     "-i", path],
                    ["wl-copy", "--type", "image/png"],
                    ["xsel", "--clipboard", "--input"]]
    for command in commands:
        if shutil.which(command[0]) is None:
            continue
        try:
            if command[0] in ("wl-copy", "xsel"):
                with open(path, "rb") as handle:
                    subprocess.run(command, stdin=handle, check=True,
                                   timeout=20)
            else:
                subprocess.run(command, check=True, timeout=20,
                               stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL)
            return True
        except (OSError, subprocess.SubprocessError):
            continue
    return False


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
        "marker_edge_width": 1.0, "hollow_markers": False,
        "legend_visible": True, "legend_location": "best",
        "legend_frame": False, "legend_edge_color": "#000000",
        "legend_background": "#ffffff", "legend_transparent": True,
        "fill_under": False, "fill_color": "#1f77b4", "fill_alpha": 0.35,
        "fill_pattern": "None (plain colour)",
        "fill_base": "Bottom of the axes",
        "fill_follows_line": True,
    },
    "fonts": {
        "title": 18, "axis_label": 18, "tick_label": 16, "legend": 14,
        "title_color": "#000000", "axis_label_color": "#000000",
        "tick_label_color": "#000000", "legend_color": "#000000",
        "title_pad": 12.0, "axis_label_pad": 7.0, "tick_label_pad": 10.0,
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
        ("color", "Axis colour (starting value)", "color"),
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

class PairedFields:
    """Sections whose lines may carry two settings, aligned across sections.

    Every section is a grid of four columns: label, widget, label, widget.
    `align_columns` gives a group of sections the same column widths, so the
    second setting of every shared line starts at the same place - the
    labels and the boxes behind them alike.
    """

    @staticmethod
    def _padding(info):
        """The horizontal padding of one grid cell, whatever Tk reports."""
        value = info.get("padx", 0)
        if isinstance(value, (list, tuple)):
            parts = [str(one) for one in value]
        else:
            parts = str(value).split()
        total = 0
        for part in parts:
            try:
                total += int(float(part))
            except (TypeError, ValueError):
                pass
        return total

    @staticmethod
    def _pair(box, row, first_text, first_widget, second_text, second_widget,
              pady=3):
        """Two settings on one line: label, widget, label, widget."""
        ttk.Label(box, text=first_text).grid(row=row, column=0, sticky="w",
                                             padx=(0, 8), pady=pady)
        first_widget.grid(row=row, column=1, sticky="w", pady=pady)
        ttk.Label(box, text=second_text).grid(row=row, column=2, sticky="w",
                                              padx=(16, 8), pady=pady)
        second_widget.grid(row=row, column=3, sticky="w", pady=pady)
        return first_widget, second_widget

    @staticmethod
    def _wide(widget, row, pady=(6, 0), columnspan=4):
        """One widget across the whole width of a section."""
        widget.grid(row=row, column=0, columnspan=columnspan, sticky="ew",
                    pady=pady)
        return widget

    def _align_columns(self, boxes):
        """Give a group of sections the same first three column widths."""
        try:      # the colour boxes only know their size once they are laid out
            self.update_idletasks()
        except tk.TclError:
            pass
        # column 2 carries the second label of a shared line ("Colour:",
        # "To:", "Minor ticks:"); it has to be as wide everywhere, or the
        # widget behind it would start at a different place in every section
        widest = {0: 0, 1: 0, 2: 0}
        for box in boxes:
            for child in box.winfo_children():
                info = child.grid_info()
                if not info or int(info.get("columnspan", 1)) != 1:
                    continue
                column = int(info.get("column", 0))
                if column in widest:
                    # the free space around the widget belongs to the cell
                    needed = child.winfo_reqwidth() + self._padding(info)
                    widest[column] = max(widest[column], needed)
        for box in boxes:
            for column, width in widest.items():
                box.grid_columnconfigure(column, minsize=width + 4)


class Tooltip:
    """A small yellow hint that appears while the pointer rests on a widget."""

    def __init__(self, widget, text, delay=TOOLTIP_DELAY):
        self.widget = widget
        self.text = str(text)
        self.delay = int(delay)
        self._timer = None
        self._window = None
        widget.bind("<Enter>", self._entered, add="+")
        widget.bind("<Leave>", self._left, add="+")
        widget.bind("<ButtonPress>", self._left, add="+")
        widget.bind("<Destroy>", self._left, add="+")

    # -- the pointer comes and goes ----------------------------------------
    def _entered(self, _event=None):
        self._cancel()
        try:
            self._timer = self.widget.after(self.delay, self.show)
        except tk.TclError:
            self._timer = None

    def _left(self, _event=None):
        self._cancel()
        self.hide()

    def _cancel(self):
        if self._timer is not None:
            try:
                self.widget.after_cancel(self._timer)
            except tk.TclError:
                pass
            self._timer = None

    # -- the hint itself ---------------------------------------------------
    def visible(self):
        return bool(self._window is not None and self._window.winfo_exists())

    def show(self):
        """Show the hint right below the widget; returns the little window."""
        self._timer = None
        if self.visible() or not self.text:
            return self._window
        try:
            if not self.widget.winfo_exists():
                return None
            x = self.widget.winfo_rootx()
            y = self.widget.winfo_rooty() + self.widget.winfo_height() + 3
            window = tk.Toplevel(self.widget)
            window.wm_overrideredirect(True)
            window.wm_geometry(f"+{x}+{y}")
            label = tk.Label(window, text=self.text, justify="left",
                             background=TOOLTIP_BACKGROUND, foreground="#000000",
                             relief="solid", borderwidth=1, padx=5, pady=2)
            label.pack()
            self._window = window
            self.label = label
        except tk.TclError:
            self._window = None
        return self._window

    def hide(self):
        window, self._window = self._window, None
        if window is not None:
            try:
                if window.winfo_exists():
                    window.destroy()
            except tk.TclError:
                pass
        return None

    def set_text(self, text):
        self.text = str(text)
        if self.visible():
            self.hide()
            self.show()


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
        elif kind == "line":
            self.create_line(x0, y1, x1, y0, fill="#000000", width=2,
                             tags="icon")
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


class PlotSplitButton(tk.Canvas):
    """Split button for the toolbar: icon of active plot style + 'Plot' label + dropdown arrow.

    Clicking the left side triggers plotting with the current plot style.
    Clicking the right side opens a menu with all available plot styles.
    """

    ARROW_ZONE = 18

    def __init__(self, master, style="line_symbol", width=84, height=26,
                 background=None, on_plot=None, on_menu=None):
        self._background = background or "#f0f0f0"
        super().__init__(master, width=width, height=height,
                         highlightthickness=1, highlightbackground="#b8b8b8",
                         borderwidth=0, background=self._background, cursor="hand2")
        self._width = width
        self._height = height
        self.style = style
        self._on_plot = on_plot
        self._on_menu = on_menu
        self._hover_part = None
        self.tooltip = Tooltip(self, "")
        self.bind("<Button-1>", self._clicked)
        self.bind("<Motion>", self._on_motion)
        self.bind("<Leave>", self._on_leave)
        self.set_style(style)

    def set_style(self, style):
        self.style = style
        style_desc = dict((code, label) for label, code, *_ in PLOT_STYLES).get(style, "Plot")
        self.tooltip.set_text(f"Plot: {style_desc} (click to plot, click arrow to select style)")
        self._redraw()

    def _on_motion(self, event):
        part = "right" if event.x >= self._width - self.ARROW_ZONE else "left"
        if part != self._hover_part:
            self._hover_part = part
            self._redraw()

    def _on_leave(self, _event=None):
        if self._hover_part is not None:
            self._hover_part = None
            self._redraw()

    def _clicked(self, event):
        if event.x >= self._width - self.ARROW_ZONE:
            if self._on_menu:
                self._on_menu(event)
        elif self._on_plot:
            self._on_plot()
        return "break"

    def _redraw(self):
        self.delete("all")
        w, h = self._width, self._height
        split_x = w - self.ARROW_ZONE

        # Hover backgrounds
        if self._hover_part == "left":
            self.create_rectangle(1, 1, split_x - 1, h - 1, fill="#e5effa", outline="")
        elif self._hover_part == "right":
            self.create_rectangle(split_x + 1, 1, w - 1, h - 1, fill="#e5effa", outline="")

        # Separator line
        self.create_line(split_x, 3, split_x, h - 3, fill="#c0c0c0", width=1)

        # Plot Icon box: x in [4, 24], y in [3, 23]
        ix0, iy0, ix1, iy1 = 4, 3, 24, 23
        self.create_rectangle(ix0, iy0, ix1, iy1, fill="#ffffff", outline="#b0b0b0", width=1)
        mx = (ix0 + ix1) / 2
        my = (iy0 + iy1) / 2
        self.create_line(ix0, my, ix1, my, fill="#ebebeb")
        self.create_line(mx, iy0, mx, iy1, fill="#ebebeb")

        style = self.style
        blue = "#1a5fb4"
        if style == "line":
            pts = [ix0 + 2, my + 4, ix0 + 7, iy0 + 3, ix0 + 13, iy1 - 3, ix1 - 2, my - 3]
            self.create_line(pts, fill=blue, width=2, smooth=True)
        elif style == "scatter":
            pts = [(ix0 + 3, iy1 - 5), (ix0 + 7, iy0 + 5), (ix0 + 11, my),
                   (ix0 + 15, iy0 + 6), (ix1 - 3, iy1 - 4)]
            for px, py in pts:
                self.create_line(px - 2, py - 2, px + 2, py + 2, fill=blue, width=1.5)
                self.create_line(px - 2, py + 2, px + 2, py - 2, fill=blue, width=1.5)
        elif style == "bar":
            bars = [(ix0 + 2, 5), (ix0 + 6, 12), (ix0 + 11, 16), (ix0 + 15, 8)]
            for bx, bh in bars:
                self.create_rectangle(bx, iy1 - bh, bx + 3.5, iy1, fill="#1f77b4", outline=blue, width=1)
        elif style == "errorbar":
            pts = [(ix0 + 5, iy1 - 6, 4), (ix0 + 10, iy0 + 7, 5), (ix1 - 5, my, 4)]
            for px, py, err in pts:
                self.create_line(px, py - err, px, py + err, fill=blue, width=1.5)
                self.create_line(px - 2.5, py - err, px + 2.5, py - err, fill=blue, width=1.5)
                self.create_line(px - 2.5, py + err, px + 2.5, py + err, fill=blue, width=1.5)
                self.create_oval(px - 1.8, py - 1.8, px + 1.8, py + 1.8, fill=blue, outline=blue)
        elif style == "histogram":
            heights = [3, 8, 15, 9, 4]
            bw = 3.2
            for i, bh in enumerate(heights):
                self.create_rectangle(ix0 + 1.5 + i * bw, iy1 - bh, ix0 + 1.5 + (i + 1) * bw, iy1,
                                      fill="#1f77b4", outline="#ffffff", width=0.8)
        elif style == "stairs":
            # a stepped outline: four treads going up
            steps = [5, 9, 13, 17]
            points = [ix0 + 2, iy1 - steps[0]]
            for index, height in enumerate(steps):
                x_left = ix0 + 2 + index * 4.5
                points += [x_left, iy1 - height, x_left + 4.5, iy1 - height]
            self.create_line(points, fill=blue, width=1.8)
        elif style == "hist2d":
            # a grid of squares, darker towards the middle
            shades = [["#dce7f5", "#9ec3e8", "#dce7f5"],
                      ["#9ec3e8", "#1f77b4", "#6aa8dc"],
                      ["#eef4fb", "#6aa8dc", "#c3d9f1"]]
            cell = (ix1 - ix0 - 4) / 3.0
            for row in range(3):
                for column in range(3):
                    self.create_rectangle(
                        ix0 + 2 + column * cell, iy0 + 2 + row * cell,
                        ix0 + 2 + (column + 1) * cell, iy0 + 2 + (row + 1) * cell,
                        fill=shades[row][column], outline="")
        elif style == "pie":
            # a circle with one slice taken out of it
            pad = 2
            self.create_arc(ix0 + pad, iy0 + pad, ix1 - pad, iy1 - pad,
                            start=60, extent=300, fill="#1f77b4",
                            outline=blue, width=1, style="pieslice")
            self.create_arc(ix0 + pad + 1.5, iy0 + pad - 1.5,
                            ix1 - pad + 1.5, iy1 - pad - 1.5,
                            start=0, extent=60, fill="#f5a623",
                            outline=blue, width=1, style="pieslice")
        else:  # line_symbol (default)
            pts = [ix0 + 2, my + 4, ix0 + 7, iy0 + 3, ix0 + 13, iy1 - 3, ix1 - 2, my - 3]
            self.create_line(pts, fill=blue, width=1.5, smooth=True)
            for px, py in [(ix0 + 3, my + 3), (ix0 + 10, my - 1), (ix1 - 3, my - 3)]:
                self.create_oval(px - 2, py - 2, px + 2, py + 2, fill=blue, outline=blue)

        # "Plot" text
        self.create_text(ix1 + 18, h / 2, text="Plot", font=("TkDefaultFont", 10, "bold"), fill="#000000")

        # Menu arrow ▼
        ax = split_x + self.ARROW_ZONE / 2
        ay = h / 2
        self.create_polygon([ax - 4, ay - 2, ax + 4, ay - 2, ax, ay + 3], fill="#000000", outline="#000000")


class TableToolButton(tk.Canvas):
    """Toolbar button of the spreadsheet, drawn as a small coloured icon.

    `kind` is `"row"` or `"column"` and `action` is `"add"` or `"delete"`:
    a **blue** icon adds, a **red** one deletes, and the band that is
    painted shows *where* it happens.  When `on_menu` is given the button
    is a **split button**: the icon does the thing its picture shows and
    the little arrow opens the list of the places (before or after the
    selected cell, or at the end of the sheet).

    A tooltip under the pointer always spells the operation out in words.
    """

    ARROW_ZONE = 14
    ICON_WIDTH = 38
    HEIGHT = 26
    ADD_COLOR = "#1a5fb4"           # blue: something is added
    DELETE_COLOR = "#c01c28"        # red: something is removed
    CELL_OUTLINE = "#8a8a8a"
    CELL_FILL = "#ffffff"
    HOVER = "#e5effa"

    # which of the three bands of the icon is painted
    TARGET_BAND = {"above": 0, "before": 0, "below": 2, "after": 2, "end": 2}

    def __init__(self, master, kind="row", action="add", where=None,
                 background=None, command=None, on_menu=None):
        self.kind = kind
        self.action = action
        self.split = on_menu is not None
        self._background = background or "#f0f0f0"
        width = self.ICON_WIDTH + (self.ARROW_ZONE if self.split else 0)
        super().__init__(master, width=width, height=self.HEIGHT,
                         highlightthickness=1, highlightbackground="#b8b8b8",
                         borderwidth=0, background=self._background,
                         cursor="hand2")
        self._width = width
        self._command = command
        self._on_menu = on_menu
        self._hover_part = None
        self.tooltip = Tooltip(self, "")
        self.bind("<Button-1>", self._clicked)
        self.bind("<Motion>", self._on_motion)
        self.bind("<Leave>", self._on_leave)
        default = "below" if kind == "row" else "after"
        self.set_where(where or default)

    # -- what the icon shows -----------------------------------------------
    def set_where(self, where):
        """Remember the place the icon shows and say it in the tooltip."""
        self.where = where
        self.tooltip.set_text(self.describe())
        self._redraw()

    def describe(self):
        """The words of the tooltip: what this button does."""
        thing = "row" if self.kind == "row" else "column"
        if self.action == "delete":
            if self.kind == "row":
                return ("Delete row: removes every row the selected cells "
                        "touch, with their data")
            return ("Delete column: removes the column of the selected "
                    "cell, with its data")
        places = {"above": "above the selected cell",
                  "below": "below the selected cell",
                  "before": "before (left of) the selected cell",
                  "after": "after (right of) the selected cell",
                  "end": ("at the end of the sheet" if self.kind == "row"
                          else "at the right end of the sheet")}
        return (f"Add {thing}: inserts an empty {thing} "
                f"{places.get(self.where, '')} "
                f"(the arrow chooses the place)")

    # -- drawing ------------------------------------------------------------
    def _redraw(self):
        self.delete("all")
        height = self.HEIGHT
        split_x = self._width - self.ARROW_ZONE if self.split else self._width
        if self._hover_part == "left":
            self.create_rectangle(1, 1, split_x - 1, height - 1,
                                  fill=self.HOVER, outline="")
        elif self._hover_part == "right":
            self.create_rectangle(split_x + 1, 1, self._width - 1, height - 1,
                                  fill=self.HOVER, outline="")
        if self.split:
            self.create_line(split_x, 4, split_x, height - 4, fill="#c0c0c0")
            ax, ay = split_x + self.ARROW_ZONE / 2, height / 2
            self.create_polygon([ax - 4, ay - 2, ax + 4, ay - 2, ax, ay + 3],
                                fill="#000000", outline="#000000")

        colour = self.ADD_COLOR if self.action == "add" else self.DELETE_COLOR
        low, high = 3, height - 5                 # the little table: 3 bands
        target = 1 if self.action == "delete" else \
            self.TARGET_BAND.get(self.where, 2)
        gap = 1.5
        span = (high - low - 2 * gap) / 3.0
        starts = [low + index * (span + gap) for index in range(3)]
        if self.action == "add" and self.where == "end":
            # the coloured band stands apart: the far end of the whole sheet
            span = (high - low - 4 * gap) / 3.0
            starts = [low, low + span + gap, high - span]
        for index in range(3):
            start, stop = starts[index], starts[index] + span
            fill = colour if index == target else self.CELL_FILL
            box = ((low, start, high, stop) if self.kind == "row"
                   else (start, low, stop, high))
            self.create_rectangle(*box, fill=fill, outline=self.CELL_OUTLINE,
                                  width=1, tags="icon")

        glyph = "+" if self.action == "add" else "×"
        gx, gy = self.ICON_WIDTH - 9, height / 2
        self.create_oval(gx - 6, gy - 6, gx + 6, gy + 6, fill=self.CELL_FILL,
                         outline=colour, width=1, tags="icon")
        self.create_text(gx, gy, text=glyph, fill=colour,
                         font=("TkDefaultFont", 12, "bold"), tags="icon")

    # -- behaviour ----------------------------------------------------------
    def _on_motion(self, event):
        part = ("right" if self.split and event.x >= self._width - self.ARROW_ZONE
                else "left")
        if part != self._hover_part:
            self._hover_part = part
            self._redraw()

    def _on_leave(self, _event=None):
        if self._hover_part is not None:
            self._hover_part = None
            self._redraw()

    def _clicked(self, event):
        if self.split and event.x >= self._width - self.ARROW_ZONE:
            if self._on_menu:
                self._on_menu(event)
        elif self._command:
            self._command()
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

        self.kind = state["kind"]
        self.line_on_var = tk.BooleanVar(
            value=not SeriesStyleDialog.is_off(state["style"]))
        self.style_var = tk.StringVar(
            value=SeriesStyleDialog.first_choice(LINE_STYLES, state["style"],
                                                 "Solid"))
        self.width_var = tk.StringVar(value=f"{state['width']:g}")
        self.alpha_var = tk.StringVar(value=f"{state.get('alpha', 0.6):g}")
        self.fill_on_var = tk.BooleanVar(value=state["face"] != "none")
        self.angle_var = tk.StringVar(value=f"{float(state.get('angle', 0.0)):g}")

        line = self._section("Line", self.line_on_var)
        combo = ttk.Combobox(line, textvariable=self.style_var, state="readonly",
                             values=drawn_names(LINE_STYLES), width=14)
        self.field(line, 0, "Style:", combo)
        combo.bind("<<ComboboxSelected>>", lambda _e: self.apply())
        self.field(line, 1, "Thickness:",
                   ttk.Spinbox(line, from_=0, to=20, increment=0.5, width=8,
                               textvariable=self.width_var, command=self.apply))
        self.edge_color = ColorSwatch(line, state["edge"],
                                      command=lambda _c: self.apply())
        self.field(line, 2, "Colour:", self.edge_color)

        # a line is a stroke: there is nothing to fill in it
        self.fill_box = None
        if self.kind not in OPEN_SHAPES:
            fill = self._section("Fill", self.fill_on_var, pady=(10, 0))
            self.fill_box = fill
            self.face_color = ColorSwatch(
                fill, "#cfe3f7" if state["face"] == "none" else state["face"],
                command=lambda _c: self.apply())
            self.field(fill, 0, "Colour:", self.face_color)
            self.field(fill, 1, "Opacity (0-1):",
                       ttk.Spinbox(fill, from_=0, to=1, increment=0.05, width=8,
                                   textvariable=self.alpha_var,
                                   command=self.apply))
        else:
            self.face_color = ColorSwatch(self.body, "#cfe3f7")
            self.face_color.pack_forget()
            self.fill_on_var.set(False)

        # a line has no rotation of its own: its two ends give the direction
        if self.kind not in OPEN_SHAPES:
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
            hint = ("Switch \"Line\" or \"Fill\" off to leave that part out.\n"
                    "Drag the object to move it, drag a square handle to\n"
                    "resize it and the round one above it to turn it\n"
                    "(Shift: 15 degree steps).")
        else:
            hint = ("Switch \"Line\" off to hide it.\n"
                    "Drag the line to move it, drag one of its two ends to\n"
                    "change its length and direction\n"
                    "(Shift: 45 degree steps).")
        ttk.Label(self.body, foreground="#666", justify="left",
                  text=hint).pack(anchor="w", pady=(8, 0))

        bar = ttk.Frame(self.body)
        bar.pack(fill="x", pady=(12, 0))
        ttk.Button(bar, text="Apply", command=self.apply).pack(side="left")
        if on_delete is not None:
            ttk.Button(bar, text="Delete", command=self._delete).pack(
                side="left", padx=(6, 0))
        ttk.Button(bar, text="Close", command=self.close).pack(side="right")

    def _section(self, title, variable, **pack):
        """A section whose title is its own check button."""
        box = ttk.LabelFrame(self.body, padding=8)
        check = ttk.Checkbutton(box, text=title, variable=variable,
                                command=self.apply)
        box.configure(labelwidget=check)
        box.pack(fill="x", **pack)
        return box

    def values(self):
        return {
            "style": (code_of(LINE_STYLES, self.style_var.get(), "-")
                      if self.line_on_var.get() else "none"),
            "width": max(0.0, to_float(self.width_var.get(), 1.5)),
            "edge": self.edge_color.color,
            "face": (self.face_color.color if self.fill_on_var.get() else "none"),
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

class SeriesStyleDialog(PairedFields, ToolDialog):
    """Line, marker, bar, and error properties of one curve; changes are applied live."""

    def __init__(self, master, line: Line2D, on_change, on_close=None,
                 legend_size=None, legend_color="#000000", on_legend_style=None,
                 fill=None, on_fill=None,
                 plot_style="line_symbol", on_plot_style=None,
                 bar_cfg=None, on_bar_cfg=None,
                 error_cfg=None, on_error_cfg=None,
                 histogram_cfg=None, on_histogram_cfg=None,
                 stairs_cfg=None, on_stairs_cfg=None,
                 hist2d_cfg=None, on_hist2d_cfg=None,
                 pie_cfg=None, on_pie_cfg=None,
                 available_columns=None):
        super().__init__(master, "Curve properties", on_close=on_close)
        self.line = line
        self.on_change = on_change
        self.on_legend_style = on_legend_style
        self.on_fill = on_fill
        self._fill = dict(fill or {})
        self.plot_style_var = tk.StringVar(
            value=name_of(PLOT_STYLES, plot_style, "Line + Symbol"))
        self.on_plot_style = on_plot_style
        self.bar_cfg = dict(bar_cfg or {})
        self.on_bar_cfg = on_bar_cfg
        self.hist_cfg = dict(histogram_cfg or {})
        self.on_histogram_cfg = on_histogram_cfg
        self.stairs_cfg = dict(stairs_cfg or {})
        self.on_stairs_cfg = on_stairs_cfg
        self.hist2d_cfg = dict(hist2d_cfg or {})
        self.on_hist2d_cfg = on_hist2d_cfg
        self.pie_cfg = dict(pie_cfg or {})
        self.on_pie_cfg = on_pie_cfg
        self.error_cfg = dict(error_cfg or {})
        self.on_error_cfg = on_error_cfg
        self.available_columns = list(available_columns or [])
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
        # a check button instead of a list: on means the zero line, off (the
        # default) means the bottom of the axes
        self.fill_zero_var = tk.BooleanVar(
            value=str(self._fill.get("base", "bottom")) == "zero")

        line_color = safe_hex(line.get_color())
        self._build_style_box()
        self._build_legend_box()
        self._build_line_box(line_color)
        self._build_marker_box(line_color, face)
        self._build_bar_box(line_color)
        self._build_error_box(line_color)
        self._build_stairs_box(line_color)
        self._build_hist2d_box()
        self._build_pie_box(line_color)
        self._build_fill_box(line_color)
        self._align_columns((self.legend_box, self.line_box,
                             self.marker_box, self.bar_box,
                             self.error_box, self.stairs_box,
                             self.hist2d_box, self.pie_box, self.fill_box))
        self._update_section_visibility()
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
    def _build_style_box(self):
        box = ttk.LabelFrame(self.body, text="Plot Style", padding=8)
        self.style_box = box
        box.pack(fill="x", pady=(0, 10))
        combo = ttk.Combobox(box, textvariable=self.plot_style_var, state="readonly",
                             values=[label for label, *_ in PLOT_STYLES], width=24)
        combo.pack(fill="x")
        combo.bind("<<ComboboxSelected>>", self._on_style_changed)

    def _build_legend_box(self):
        box = self._section("Legend", self.legend_on_var)
        self.legend_box = box
        ttk.Label(box, text="Text:").grid(row=0, column=0, sticky="w",
                                          padx=(0, 8), pady=3)
        ttk.Entry(box, textvariable=self.label_var, width=30).grid(
            row=0, column=1, columnspan=3, sticky="ew", pady=3)
        self.label_var.trace_add("write", self._apply)
        # the size of the text and its colour stand side by side
        self.legend_color = ColorSwatch(box, self._legend_color,
                                        command=lambda _c: self._apply())
        self._pair(box, 1,
                   "Font size:",
                   ttk.Spinbox(box, from_=4, to=72, increment=1, width=SPIN_WIDTH,
                               textvariable=self.legend_size_var,
                               command=self._apply),
                   "Colour:", self.legend_color)
        self.legend_size_var.trace_add("write", self._apply)
        self._wide(ttk.Label(
            box, text="Switch \"Legend\" off to hide this curve's box.",
            foreground="#666"), 2, pady=(4, 0))

    def _build_line_box(self, line_color):
        box = self._section("Line", self.line_on_var, pady=(10, 0))
        self.line_box = box

        combo = ttk.Combobox(box, textvariable=self.lstyle_var, state="readonly",
                             values=drawn_names(LINE_STYLES), width=COMBO_WIDTH)
        self.field(box, 0, "Style:", combo)
        combo.bind("<<ComboboxSelected>>", self._apply)

        # the thickness of the line and its colour stand side by side
        self.line_color = ColorSwatch(box, line_color,
                                      command=lambda _c: self._apply())
        self._pair(box, 1,
                   "Width:",
                   ttk.Spinbox(box, from_=0, to=20, increment=0.5,
                               width=SPIN_WIDTH, textvariable=self.lwidth_var,
                               command=self._apply),
                   "Colour:", self.line_color)
        self.lwidth_var.trace_add("write", self._apply)

    def _build_marker_box(self, line_color, face):
        box = self._section("Marker", self.marker_on_var, pady=(10, 0))
        self.marker_box = box

        # an outlined marker has no fill at all: the switch belongs on top
        self._wide(ttk.Checkbutton(box, text="Hollow (no fill)",
                                   variable=self.hollow_var,
                                   command=self._apply), 0, pady=(0, 4))

        combo = ttk.Combobox(box, textvariable=self.mstyle_var, state="readonly",
                             values=drawn_names(MARKERS), width=COMBO_WIDTH)
        self.field(box, 1, "Style:", combo)
        combo.bind("<<ComboboxSelected>>", self._apply)

        self.face_color = ColorSwatch(box, safe_hex(face, line_color),
                                      command=lambda _c: self._apply())
        self._pair(box, 2,
                   "Size:",
                   ttk.Spinbox(box, from_=0, to=40, increment=1,
                               width=SPIN_WIDTH, textvariable=self.msize_var,
                               command=self._apply),
                   "Fill colour:", self.face_color)
        self.msize_var.trace_add("write", self._apply)

        self.edge_color = ColorSwatch(
            box, safe_hex(self.line.get_markeredgecolor(), line_color),
            command=lambda _c: self._apply())
        self._pair(box, 3,
                   "Edge width:",
                   ttk.Spinbox(box, from_=0, to=10, increment=0.5,
                               width=SPIN_WIDTH, textvariable=self.mwidth_var,
                               command=self._apply),
                   "Edge colour:", self.edge_color)
        self.mwidth_var.trace_add("write", self._apply)

    def _build_bar_box(self, line_color):
        """Bars: shared by the bar chart and the histogram.

        The two differ in one field only: a bar chart has a width, while
        the bars of a histogram touch and it is the **number of bins** that
        can be set instead.  So the first line of the section carries
        whichever of the two belongs to the style of this curve.
        """
        box = ttk.LabelFrame(self.body, text="Bar properties", padding=8)
        self.bar_box = box
        histogram = self.style_code() == "histogram"
        # a histogram curve reads its colours from its own settings
        source = self.hist_cfg if histogram else self.bar_cfg
        self.bar_width_var = tk.StringVar(value=str(self.bar_cfg.get("width", 0.8)))
        self.hist_bins_var = tk.StringVar(
            value=str(int(self.hist_cfg.get("bins", HISTOGRAM_BINS))))
        self.bar_alpha_var = tk.StringVar(value=str(source.get("alpha", 0.85)))
        self.bar_edge_width_var = tk.StringVar(value=str(source.get("edgewidth", 1.0)))
        self.bar_color = ColorSwatch(box, source.get("color", line_color),
                                     command=lambda _c: self._apply())
        self.bar_edge_color = ColorSwatch(
            box, source.get("edgecolor", "#ffffff" if histogram else line_color),
            command=lambda _c: self._apply())

        self.bar_width_spin = ttk.Spinbox(
            box, from_=0.05, to=10, increment=0.05, width=SPIN_WIDTH,
            textvariable=self.bar_width_var, command=self._apply)
        self._pair(box, 0, "Width:", self.bar_width_spin,
                   "Bar colour:", self.bar_color)
        self.bar_width_label = box.grid_slaves(row=0, column=0)[0]
        self.bar_width_var.trace_add("write", self._apply)

        # the number of bins takes the same place when this is a histogram
        self.hist_bins_label = ttk.Label(box, text="Bins:")
        self.hist_bins_spin = ttk.Spinbox(
            box, from_=1, to=MAX_HISTOGRAM_BINS, increment=1, width=SPIN_WIDTH,
            textvariable=self.hist_bins_var, command=self._apply)
        self.hist_bins_var.trace_add("write", self._apply)

        self._pair(box, 1,
                   "Opacity (0-1):",
                   ttk.Spinbox(box, from_=0, to=1, increment=0.05,
                               width=SPIN_WIDTH, textvariable=self.bar_alpha_var,
                               command=self._apply),
                   "Edge colour:", self.bar_edge_color)
        self.bar_alpha_var.trace_add("write", self._apply)

        self._pair(box, 2,
                   "Edge width:",
                   ttk.Spinbox(box, from_=0, to=10, increment=0.5,
                               width=SPIN_WIDTH, textvariable=self.bar_edge_width_var,
                               command=self._apply),
                   "", ttk.Label(box, text=""))
        self.bar_edge_width_var.trace_add("write", self._apply)

        # a pattern over the colour, the same choice a filled area has
        self.bar_hatch_var = tk.StringVar(
            value=name_of(HATCH_PATTERNS, source.get("hatch", ""),
                          names(HATCH_PATTERNS)[0]))
        pattern = ttk.Combobox(box, textvariable=self.bar_hatch_var,
                               state="readonly", values=names(HATCH_PATTERNS),
                               width=22)
        self.field(box, 3, "Pattern:", pattern)
        pattern.bind("<<ComboboxSelected>>", self._apply)

    def _build_error_box(self, line_color):
        box = ttk.LabelFrame(self.body, text="Error bar properties", padding=8)
        self.error_box = box
        err_type = self.error_cfg.get("type", "pair")
        self.err_type_var = tk.StringVar(
            value=name_of(ERROR_SOURCES, err_type, names(ERROR_SOURCES)[0]))
        self.err_val_var = tk.StringVar(value=str(self.error_cfg.get("value", 5.0)))
        self.err_col_var = tk.StringVar(value=str(self.error_cfg.get("column", "")))
        self.err_capsize_var = tk.StringVar(value=str(self.error_cfg.get("capsize", 4.0)))
        self.err_capthick_var = tk.StringVar(value=str(self.error_cfg.get("capthick", 1.5)))
        self.err_elinewidth_var = tk.StringVar(value=str(self.error_cfg.get("elinewidth", 1.5)))
        self.err_color = ColorSwatch(box, self.error_cfg.get("color", line_color),
                                     command=lambda _c: self._apply())

        combo = ttk.Combobox(box, textvariable=self.err_type_var, state="readonly",
                             values=names(ERROR_SOURCES), width=COMBO_WIDTH)
        self.field(box, 0, "Source:", combo)
        combo.bind("<<ComboboxSelected>>", self._on_err_type_changed)

        self._err_val_spin = ttk.Spinbox(box, from_=0.01, to=1000, increment=0.5,
                                         width=SPIN_WIDTH, textvariable=self.err_val_var,
                                         command=self._apply)
        self._pair(box, 1, "Value / %:", self._err_val_spin,
                   "Colour:", self.err_color)
        self.err_val_var.trace_add("write", self._apply)

        cols = [c for c in self.available_columns if str(c) != str(self.column)]
        if not cols:
            cols = list(self.available_columns)
        self._err_col_combo = ttk.Combobox(box, textvariable=self.err_col_var, state="readonly",
                                           values=cols, width=COMBO_WIDTH)
        self.field(box, 2, "Column:", self._err_col_combo)
        self._err_col_combo.bind("<<ComboboxSelected>>", self._apply)

        self._pair(box, 3,
                   "Cap width:",
                   ttk.Spinbox(box, from_=0, to=20, increment=1,
                               width=SPIN_WIDTH, textvariable=self.err_capsize_var,
                               command=self._apply),
                   "Line width:",
                   ttk.Spinbox(box, from_=0.5, to=10, increment=0.5,
                               width=SPIN_WIDTH, textvariable=self.err_elinewidth_var,
                               command=self._apply))
        self.err_capsize_var.trace_add("write", self._apply)
        self.err_elinewidth_var.trace_add("write", self._apply)

        # the thickness of the caps themselves: it was in the settings all
        # along, but there was no field for it
        self._pair(box, 4,
                   "Cap thickness:",
                   ttk.Spinbox(box, from_=0, to=10, increment=0.5,
                               width=SPIN_WIDTH,
                               textvariable=self.err_capthick_var,
                               command=self._apply),
                   "", ttk.Label(box, text=""))
        self.err_capthick_var.trace_add("write", self._apply)

    def _build_stairs_box(self, line_color):
        """Stairs: where the steps stand, and how the staircase is drawn."""
        box = ttk.LabelFrame(self.body, text="Stairs properties", padding=8)
        self.stairs_box = box
        cfg = self.stairs_cfg
        self.stairs_edges_var = tk.StringVar(
            value=name_of(STAIRS_EDGES, cfg.get("edges", "mid"),
                          names(STAIRS_EDGES)[0]))
        self.stairs_width_var = tk.StringVar(value=str(cfg.get("width", 1.8)))
        self.stairs_alpha_var = tk.StringVar(value=str(cfg.get("alpha", 0.35)))
        self.stairs_fill_var = tk.BooleanVar(value=bool(cfg.get("fill", False)))
        self.stairs_base_var = tk.BooleanVar(
            value=bool(cfg.get("baseline", False)))
        self.stairs_hatch_var = tk.StringVar(
            value=name_of(HATCH_PATTERNS, cfg.get("hatch", ""),
                          names(HATCH_PATTERNS)[0]))
        self.stairs_color = ColorSwatch(box, cfg.get("color", line_color),
                                        command=lambda _c: self._apply())

        combo = ttk.Combobox(box, textvariable=self.stairs_edges_var,
                             state="readonly", values=names(STAIRS_EDGES),
                             width=28)
        self._wide(combo, 0, pady=(0, 4))
        combo.bind("<<ComboboxSelected>>", self._apply)

        self._pair(box, 1,
                   "Line width:",
                   ttk.Spinbox(box, from_=0, to=10, increment=0.2,
                               width=SPIN_WIDTH,
                               textvariable=self.stairs_width_var,
                               command=self._apply),
                   "Colour:", self.stairs_color)
        self.stairs_width_var.trace_add("write", self._apply)

        self._pair(box, 2,
                   "Fill it:", ttk.Checkbutton(box, variable=self.stairs_fill_var,
                                               command=self._apply),
                   "Opacity (0-1):",
                   ttk.Spinbox(box, from_=0, to=1, increment=0.05,
                               width=SPIN_WIDTH,
                               textvariable=self.stairs_alpha_var,
                               command=self._apply))
        self.stairs_alpha_var.trace_add("write", self._apply)

        pattern = ttk.Combobox(box, textvariable=self.stairs_hatch_var,
                               state="readonly", values=names(HATCH_PATTERNS),
                               width=22)
        self.field(box, 3, "Pattern:", pattern)
        pattern.bind("<<ComboboxSelected>>", self._apply)

        self._wide(ttk.Checkbutton(box, text="Close it down to the zero line",
                                   variable=self.stairs_base_var,
                                   command=self._apply), 4, pady=(4, 0))

    def _build_hist2d_box(self):
        """2D histogram: the grid, the colour scale and the colour bar."""
        box = ttk.LabelFrame(self.body, text="2D histogram properties",
                             padding=8)
        self.hist2d_box = box
        cfg = self.hist2d_cfg
        self.h2_xbins_var = tk.StringVar(
            value=str(int(cfg.get("xbins", HIST2D_BINS))))
        self.h2_ybins_var = tk.StringVar(
            value=str(int(cfg.get("ybins", HIST2D_BINS))))
        self.h2_alpha_var = tk.StringVar(value=str(cfg.get("alpha", 1.0)))
        self.h2_cmap_var = tk.StringVar(
            value=name_of(COLOR_MAPS, cfg.get("cmap", "viridis"),
                          names(COLOR_MAPS)[0]))
        self.h2_bar_var = tk.BooleanVar(value=bool(cfg.get("colorbar", False)))
        self.h2_empty_var = tk.BooleanVar(
            value=bool(cfg.get("hide_empty", True)))

        self._pair(box, 0,
                   "Bins across X:",
                   ttk.Spinbox(box, from_=1, to=MAX_HIST2D_BINS, increment=1,
                               width=SPIN_WIDTH, textvariable=self.h2_xbins_var,
                               command=self._apply),
                   "Bins up Y:",
                   ttk.Spinbox(box, from_=1, to=MAX_HIST2D_BINS, increment=1,
                               width=SPIN_WIDTH, textvariable=self.h2_ybins_var,
                               command=self._apply))
        self.h2_xbins_var.trace_add("write", self._apply)
        self.h2_ybins_var.trace_add("write", self._apply)

        combo = ttk.Combobox(box, textvariable=self.h2_cmap_var,
                             state="readonly", values=names(COLOR_MAPS),
                             width=22)
        self.field(box, 1, "Colour scale:", combo)
        combo.bind("<<ComboboxSelected>>", self._apply)

        self._pair(box, 2,
                   "Opacity (0-1):",
                   ttk.Spinbox(box, from_=0, to=1, increment=0.05,
                               width=SPIN_WIDTH, textvariable=self.h2_alpha_var,
                               command=self._apply),
                   "Colour bar:",
                   ttk.Checkbutton(box, variable=self.h2_bar_var,
                                   command=self._apply))
        self.h2_alpha_var.trace_add("write", self._apply)

        self._wide(ttk.Checkbutton(box, text="Leave the empty cells white",
                                   variable=self.h2_empty_var,
                                   command=self._apply), 3, pady=(4, 0))

    def _build_pie_box(self, line_color):
        """Pie: the slices, their names and the numbers written on them."""
        box = ttk.LabelFrame(self.body, text="Pie properties", padding=8)
        self.pie_box = box
        cfg = self.pie_cfg
        self.pie_cmap_var = tk.StringVar(
            value=name_of(COLOR_MAPS, cfg.get("cmap", "tab10"),
                          names(COLOR_MAPS)[0]))
        self.pie_labels_var = tk.StringVar(
            value=name_of(PIE_LABELS, cfg.get("labels", "column"),
                          names(PIE_LABELS)[0]))
        self.pie_start_var = tk.StringVar(
            value=f"{float(cfg.get('start', PIE_START_ANGLE)):g}")
        self.pie_hole_var = tk.StringVar(value=str(cfg.get("hole", 0.0)))
        self.pie_explode_var = tk.StringVar(value=str(cfg.get("explode", 0.0)))
        self.pie_percent_var = tk.BooleanVar(
            value=bool(cfg.get("percent", True)))
        self.pie_decimals_var = tk.StringVar(
            value=str(int(cfg.get("decimals", 1))))
        self.pie_size_var = tk.StringVar(
            value=str(int(cfg.get("label_size", 11))))
        self.pie_clock_var = tk.BooleanVar(
            value=bool(cfg.get("clockwise", True)))
        self.pie_edge_width_var = tk.StringVar(
            value=str(cfg.get("edgewidth", 1.0)))
        self.pie_edge_color = ColorSwatch(
            box, cfg.get("edgecolor", "#ffffff"),
            command=lambda _c: self._apply())

        combo = ttk.Combobox(box, textvariable=self.pie_cmap_var,
                             state="readonly", values=names(COLOR_MAPS),
                             width=22)
        self.field(box, 0, "Slice colours:", combo)
        combo.bind("<<ComboboxSelected>>", self._apply)

        names_combo = ttk.Combobox(box, textvariable=self.pie_labels_var,
                                   state="readonly", values=names(PIE_LABELS),
                                   width=26)
        self._wide(names_combo, 1, pady=(4, 4))
        names_combo.bind("<<ComboboxSelected>>", self._apply)

        self._pair(box, 2,
                   "Start angle:",
                   ttk.Spinbox(box, from_=-360, to=360, increment=15,
                               width=SPIN_WIDTH, textvariable=self.pie_start_var,
                               command=self._apply),
                   "Edge colour:", self.pie_edge_color)
        self.pie_start_var.trace_add("write", self._apply)

        self._pair(box, 3,
                   "Per cent:",
                   ttk.Checkbutton(box, variable=self.pie_percent_var,
                                   command=self._apply),
                   "Decimals:",
                   ttk.Spinbox(box, from_=0, to=4, increment=1,
                               width=SPIN_WIDTH,
                               textvariable=self.pie_decimals_var,
                               command=self._apply))
        self.pie_decimals_var.trace_add("write", self._apply)

        self._pair(box, 4,
                   "Hole (0-0.9):",
                   ttk.Spinbox(box, from_=0, to=0.9, increment=0.05,
                               width=SPIN_WIDTH, textvariable=self.pie_hole_var,
                               command=self._apply),
                   "Text size:",
                   ttk.Spinbox(box, from_=4, to=48, increment=1,
                               width=SPIN_WIDTH, textvariable=self.pie_size_var,
                               command=self._apply))
        self.pie_hole_var.trace_add("write", self._apply)
        self.pie_size_var.trace_add("write", self._apply)

        self._pair(box, 5,
                   "Pull out the first:",
                   ttk.Spinbox(box, from_=0, to=0.5, increment=0.05,
                               width=SPIN_WIDTH,
                               textvariable=self.pie_explode_var,
                               command=self._apply),
                   "Edge width:",
                   ttk.Spinbox(box, from_=0, to=10, increment=0.5,
                               width=SPIN_WIDTH,
                               textvariable=self.pie_edge_width_var,
                               command=self._apply))
        self.pie_explode_var.trace_add("write", self._apply)
        self.pie_edge_width_var.trace_add("write", self._apply)

        self._wide(ttk.Checkbutton(box, text="Go round anticlockwise",
                                   variable=self.pie_clock_var,
                                   command=self._apply), 6, pady=(4, 0))

    def _on_err_type_changed(self, _event=None):
        src = code_of(ERROR_SOURCES, self.err_type_var.get(), "pair")
        if src == "column":
            self._err_col_combo.configure(state="readonly")
            self._err_val_spin.configure(state="disabled")
        elif src in ("std", "pair"):
            self._err_col_combo.configure(state="disabled")
            self._err_val_spin.configure(state="disabled")
        else:
            self._err_col_combo.configure(state="disabled")
            self._err_val_spin.configure(state="normal")
        self._apply()

    def style_code(self):
        """The plot style this curve is drawn with, as a code."""
        return code_of(PLOT_STYLES, self.plot_style_var.get(), "line_symbol")

    def _show_bar_fields(self, histogram):
        """A histogram has a number of bins where a bar chart has a width."""
        self.bar_box.configure(text="Histogram properties" if histogram
                               else "Bar properties")
        if histogram:
            self.bar_width_label.grid_remove()
            self.bar_width_spin.grid_remove()
            self.hist_bins_label.grid(row=0, column=0, sticky="w",
                                      padx=(0, 8), pady=3)
            self.hist_bins_spin.grid(row=0, column=1, sticky="w", pady=3)
        else:
            self.hist_bins_label.grid_remove()
            self.hist_bins_spin.grid_remove()
            self.bar_width_label.grid()
            self.bar_width_spin.grid()

    # which sections belong to which plot style, in the order they appear
    SECTIONS = {
        "line_symbol": ("line_box", "marker_box", "fill_box"),
        "line": ("line_box", "fill_box"),
        "scatter": ("marker_box", "fill_box"),
        "bar": ("bar_box",),
        "histogram": ("bar_box",),
        "errorbar": ("marker_box", "line_box", "error_box"),
        "stairs": ("stairs_box",),
        "hist2d": ("hist2d_box",),
        "pie": ("pie_box",),
    }

    def _update_section_visibility(self):
        """Show exactly the sections the plot style of this curve can use."""
        st = self.style_code()
        for name in ("line_box", "marker_box", "bar_box", "error_box",
                     "stairs_box", "hist2d_box", "pie_box", "fill_box"):
            getattr(self, name).pack_forget()
        if st in ("bar", "histogram"):
            self._show_bar_fields(st == "histogram")
        for name in self.SECTIONS.get(st, self.SECTIONS["line_symbol"]):
            getattr(self, name).pack(fill="x", pady=(10, 0))

    def _on_style_changed(self, _event=None):
        st = self.style_code()
        if st == "line":
            self.line_on_var.set(True)
            self.marker_on_var.set(False)
        elif st == "scatter":
            self.line_on_var.set(False)
            self.marker_on_var.set(True)
        elif st == "line_symbol":
            self.line_on_var.set(True)
            self.marker_on_var.set(True)
        elif st in ("bar", "histogram", "stairs", "hist2d", "pie"):
            # these draw an artist of their own instead of the curve
            self.line_on_var.set(False)
            self.marker_on_var.set(False)
        elif st == "errorbar":
            self.marker_on_var.set(True)
        self._update_section_visibility()
        self._apply()

    def _build_fill_box(self, line_color):
        box = self._section("Fill under the curve", self.fill_on_var,
                            pady=(10, 0))
        self.fill_box = box

        self._wide(ttk.Checkbutton(box, text="Same colour as the curve",
                                   variable=self.fill_follow_var,
                                   command=self._apply), 0, pady=(0, 4))
        # the colour of the area and how transparent it is belong together
        self.fill_color = ColorSwatch(box, self._fill.get("color", line_color),
                                      command=lambda _c: self._apply())
        self._pair(box, 1,
                   "Fill colour:", self.fill_color,
                   "Opacity (0-1):",
                   ttk.Spinbox(box, from_=0, to=1, increment=0.05,
                               width=SPIN_WIDTH,
                               textvariable=self.fill_alpha_var,
                               command=self._apply))
        self.fill_alpha_var.trace_add("write", self._apply)

        pattern = ttk.Combobox(box, textvariable=self.fill_hatch_var,
                               state="readonly", values=names(HATCH_PATTERNS),
                               width=22)
        ttk.Label(box, text="Pattern:").grid(row=2, column=0, sticky="w",
                                             padx=(0, 8), pady=3)
        pattern.grid(row=2, column=1, columnspan=3, sticky="w", pady=3)
        pattern.bind("<<ComboboxSelected>>", self._apply)

        self.fill_zero_check = self._wide(
            ttk.Checkbutton(box, text="Fill down to zero line",
                            variable=self.fill_zero_var, command=self._apply),
            3, pady=(4, 0))
        self._wide(ttk.Label(
            box, foreground="#666", justify="left",
            text="Switched off, the area is filled down to the axis."), 4)

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
        self.bar_color.set_color(color)
        self.bar_edge_color.set_color(color)
        self.err_color.set_color(color)
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
                "base": "zero" if self.fill_zero_var.get() else "bottom",
            })
        st_code = code_of(PLOT_STYLES, self.plot_style_var.get(), "line_symbol")
        if self.on_plot_style:
            self.on_plot_style(st_code)
        if self.on_bar_cfg:
            self.on_bar_cfg({
                "width": to_float(self.bar_width_var.get(), 0.8),
                "alpha": to_float(self.bar_alpha_var.get(), 0.85),
                "edgewidth": to_float(self.bar_edge_width_var.get(), 1.0),
                "color": self.bar_color.color,
                "edgecolor": self.bar_edge_color.color,
                "hatch": code_of(HATCH_PATTERNS, self.bar_hatch_var.get(), ""),
            })
        if self.on_histogram_cfg:
            # the same fields serve the histogram; only the number of bins
            # is its own
            self.on_histogram_cfg({
                "bins": max(1, min(to_int(self.hist_bins_var.get(),
                                          HISTOGRAM_BINS),
                                   MAX_HISTOGRAM_BINS)),
                "alpha": to_float(self.bar_alpha_var.get(), 0.85),
                "edgewidth": to_float(self.bar_edge_width_var.get(), 1.0),
                "color": self.bar_color.color,
                "edgecolor": self.bar_edge_color.color,
                "hatch": code_of(HATCH_PATTERNS, self.bar_hatch_var.get(), ""),
            })
        if self.on_stairs_cfg:
            self.on_stairs_cfg({
                "edges": code_of(STAIRS_EDGES, self.stairs_edges_var.get(), "mid"),
                "width": to_float(self.stairs_width_var.get(), 1.8),
                "fill": bool(self.stairs_fill_var.get()),
                "alpha": to_float(self.stairs_alpha_var.get(), 0.35),
                "hatch": code_of(HATCH_PATTERNS, self.stairs_hatch_var.get(), ""),
                "baseline": bool(self.stairs_base_var.get()),
                "color": self.stairs_color.color,
            })
        if self.on_hist2d_cfg:
            self.on_hist2d_cfg({
                "xbins": max(1, min(to_int(self.h2_xbins_var.get(),
                                           HIST2D_BINS), MAX_HIST2D_BINS)),
                "ybins": max(1, min(to_int(self.h2_ybins_var.get(),
                                           HIST2D_BINS), MAX_HIST2D_BINS)),
                "cmap": code_of(COLOR_MAPS, self.h2_cmap_var.get(), "viridis"),
                "alpha": to_float(self.h2_alpha_var.get(), 1.0),
                "colorbar": bool(self.h2_bar_var.get()),
                "hide_empty": bool(self.h2_empty_var.get()),
            })
        if self.on_pie_cfg:
            self.on_pie_cfg({
                "cmap": code_of(COLOR_MAPS, self.pie_cmap_var.get(), "tab10"),
                "labels": code_of(PIE_LABELS, self.pie_labels_var.get(), "column"),
                "start": to_float(self.pie_start_var.get(), PIE_START_ANGLE),
                "percent": bool(self.pie_percent_var.get()),
                "decimals": max(0, to_int(self.pie_decimals_var.get(), 1)),
                "hole": to_float(self.pie_hole_var.get(), 0.0),
                "explode": to_float(self.pie_explode_var.get(), 0.0),
                "label_size": max(4, to_int(self.pie_size_var.get(), 11)),
                "clockwise": bool(self.pie_clock_var.get()),
                "edgecolor": self.pie_edge_color.color,
                "edgewidth": to_float(self.pie_edge_width_var.get(), 1.0),
            })
        if self.on_error_cfg:
            self.on_error_cfg({
                "type": code_of(ERROR_SOURCES, self.err_type_var.get(), "pair"),
                "value": to_float(self.err_val_var.get(), 5.0),
                "column": self.err_col_var.get(),
                "capsize": to_float(self.err_capsize_var.get(), 4.0),
                "capthick": to_float(self.err_capthick_var.get(), 1.5),
                "elinewidth": to_float(self.err_elinewidth_var.get(), 1.5),
                "color": self.err_color.color,
            })
        self.on_change()


# --------------------------------------------------------------------------
# axes properties: one window, one tab per axis
# --------------------------------------------------------------------------

class AxisTab(PairedFields, ttk.Frame):
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
        self._axis_color = safe_hex(cfg.get("axis_color", "#000000"), "#000000")
        self.label_on_var = tk.BooleanVar(value=cfg.get("label_on", True))
        self.ticks_on_var = tk.BooleanVar(value=cfg.get("ticks_on", True))
        self.gmajor_var = tk.BooleanVar(value=grid["major"])
        self.gminor_var = tk.BooleanVar(value=grid["minor"])
        self.gstyle_var = tk.StringVar(value=name_of(GRID_STYLES, grid["style"], "Dotted"))
        self.gwidth_var = tk.StringVar(value=f"{grid['width']:g}")

        self._build_label_box()
        self._build_range_box()
        self._build_grid_box(grid["color"])
        self._align_columns((self.label_box, self.range_box,
                             self.grid_box))
        self._toggle_auto()

    # -- construction ------------------------------------------------------
    def _section(self, title, variable, **pack):
        """A section whose title is its own check button."""
        box = ttk.LabelFrame(self, padding=8)
        check = ttk.Checkbutton(box, text=title, variable=variable)
        box.configure(labelwidget=check)
        box.pack(fill="x", **pack)
        return box, check

    def _build_label_box(self):
        """The axis label: its text, its font and how far it sits."""
        box, check = self._section("Axis label and fonts", self.label_on_var)
        self.label_box, self.label_check = box, check
        ttk.Label(box, text="Label text:").grid(row=0, column=0, sticky="w",
                                                padx=(0, 8), pady=3)
        # the text field reaches across the whole section, so the colour of
        # the row below it does not get pushed to the far right
        ttk.Entry(box, textvariable=self.label_var, width=30).grid(
            row=0, column=1, columnspan=3, sticky="ew", pady=3)
        # the size and the colour of the label stand side by side
        self.label_color = ColorSwatch(box, self._label_color)
        self._pair(box, 1,
                   "Label font size:",
                   ttk.Spinbox(box, from_=4, to=48, increment=1, width=SPIN_WIDTH,
                               textvariable=self.label_size_var),
                   "Colour:", self.label_color)
        ToolDialog.field(box, 2, "Label offset [px]:",
                         ttk.Spinbox(box, from_=-200, to=400, increment=1,
                                     width=SPIN_WIDTH,
                                     textvariable=self.label_pad_var))
        self._wide(ttk.Label(box, foreground="#666", justify="left",
                             text="Switch the section off to leave the label "
                                  "away."), 3)

    def _build_range_box(self):
        """The numbers on the axis: their font, the range and the ticks."""
        box, check = self._section("Tick range, labels and fonts",
                                   self.ticks_on_var, pady=(10, 0))
        self.range_box, self.ticks_check = box, check
        # the size and the colour of the numbers stand side by side
        self.tick_color = ColorSwatch(box, self._tick_color)
        self._pair(box, 0,
                   "Numbers (ticks) font size:",
                   ttk.Spinbox(box, from_=4, to=48, increment=1, width=SPIN_WIDTH,
                               textvariable=self.tick_size_var),
                   "Colour:", self.tick_color)
        ToolDialog.field(box, 1, "Number offset [px]:",
                         ttk.Spinbox(box, from_=-200, to=400, increment=1,
                                     width=SPIN_WIDTH,
                                     textvariable=self.tick_pad_var))
        self._wide(ttk.Separator(box, orient="horizontal"), 2, pady=(8, 6))
        self._wide(ttk.Checkbutton(box, text="Automatic range and ticks",
                                   variable=self.auto_var,
                                   command=self._toggle_auto), 3, pady=(0, 4))
        # the two ends of the range share one line
        self.min_entry, self.max_entry = self._pair(
            box, 4,
            "From:", ttk.Entry(box, textvariable=self.min_var, width=ENTRY_WIDTH),
            "To:", ttk.Entry(box, textvariable=self.max_var, width=ENTRY_WIDTH))
        # the step of the major ticks and the number of minor ones between
        # them belong together: one line
        self.step_entry, _minor = self._pair(
            box, 5,
            "Step (major ticks):",
            ttk.Entry(box, textvariable=self.step_var, width=ENTRY_WIDTH),
            "Minor ticks:",
            ttk.Spinbox(box, from_=0, to=20, increment=1, width=SPIN_WIDTH,
                        textvariable=self.minor_var))
        self._wide(ttk.Separator(box, orient="horizontal"), 6, pady=(8, 6))
        self.axis_color = ColorSwatch(box, self._axis_color)
        ToolDialog.field(box, 7, "Axis colour:", self.axis_color)
        self._wide(ttk.Label(
            box, foreground="#666", justify="left",
            text="The colour of this axis line and of its tick marks.\n"
                 "Switch the section off to leave the numbers and both\n"
                 "kinds of tick marks away."), 8)

    def _build_grid_box(self, color):
        """The grid: the section title switches the major lines on."""
        box, check = self._section("Grid of this axis", self.gmajor_var,
                                   pady=(10, 0))
        self.grid_box, self.grid_check = box, check
        ttk.Checkbutton(box, text="Minor grid lines", variable=self.gminor_var
                        ).grid(row=0, column=0, columnspan=4, sticky="w")
        # the style of the lines and their colour stand side by side
        self.grid_color = ColorSwatch(box, color)
        self._pair(box, 1,
                   "Style:",
                   ttk.Combobox(box, textvariable=self.gstyle_var,
                                state="readonly", values=names(GRID_STYLES),
                                width=ENTRY_WIDTH),
                   "Colour:", self.grid_color)
        ToolDialog.field(box, 2, "Width:",
                         ttk.Spinbox(box, from_=0.2, to=5, increment=0.2,
                                     width=SPIN_WIDTH,
                                     textvariable=self.gwidth_var))
        self._wide(ttk.Label(
            box, foreground="#666", justify="left",
            text="The section title draws the major grid lines."), 3)

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
            "axis_color": self.axis_color.color,
            "label_on": bool(self.label_on_var.get()),
            "ticks_on": bool(self.ticks_on_var.get()),
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

        self._build_frame_box()
        self._build_background_box(cfg)
        self._build_size_box()
        self._show_values()

    # -- construction ------------------------------------------------------
    def _build_frame_box(self):
        box = ttk.LabelFrame(self, text="Frame", padding=8)
        box.pack(fill="x")
        ToolDialog.field(box, 0, "Style:",
                         ttk.Combobox(box, textvariable=self.style_var,
                                      state="readonly", values=names(FRAME_STYLES),
                                      width=26))
        ToolDialog.field(box, 1, "Thickness:",
                         ttk.Spinbox(box, from_=0, to=10, increment=0.2, width=8,
                                     textvariable=self.width_var))
        ToolDialog.field(box, 2, "Major tick length:",
                         ttk.Spinbox(box, from_=0, to=30, increment=0.5, width=8,
                                     textvariable=self.major_len_var))
        ToolDialog.field(box, 3, "Minor tick length:",
                         ttk.Spinbox(box, from_=0, to=30, increment=0.5, width=8,
                                     textvariable=self.minor_len_var))
        ttk.Label(box, foreground="#666", justify="left",
                  text="\"No frame\" draws only the axes that are in use; the\n"
                       "two \"with ticks\" styles put ticks on all four sides.\n"
                       "The colour of each axis line is on its own page,\n"
                       "as \"Axis colour\".").grid(
            row=4, column=0, columnspan=2, sticky="w", pady=(6, 0))

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
            # the colour lives on the three axis pages now
            "color": self.plot.frame_cfg.get("color", "#000000"),
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
        if plot.right_axis_active():   # only when a curve is drawn there
            tab = AxisTab(notebook, plot, "y2")
            notebook.add(tab, text="Right Y axis")
            self.tabs["y2"] = tab
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
        """which: 'x', 'y', 'y2' or 'frame'."""
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
                    f"{AXIS_NAMES.get(which, which.upper())}.", parent=self)
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

        # the name of the section is its own check button: no frame when off
        frame_box = ttk.LabelFrame(self.body, padding=8)
        frame_check = ttk.Checkbutton(frame_box, text="Surrounding box",
                                      variable=self.frame_var,
                                      command=self.apply)
        frame_box.configure(labelwidget=frame_check)
        frame_box.pack(fill="x", pady=(10, 0))
        self.frame_check = frame_check
        self.edge_color = ColorSwatch(frame_box, "#000000" if edge == "none" else edge,
                                      command=lambda _c: self.apply())
        self.field(frame_box, 0, "Frame colour:", self.edge_color)
        self.face_color = ColorSwatch(frame_box,
                                      "#ffffff" if face == "none" else face,
                                      command=lambda _c: self.apply())
        self.field(frame_box, 1, "Background colour:", self.face_color)
        self.field(frame_box, 2, "",
                   ttk.Checkbutton(frame_box, text="Transparent background",
                                   variable=self.transparent_var,
                                   command=self.apply))
        ttk.Label(frame_box, text="Drag the box with the pointer to move it.",
                  foreground="#666").grid(row=3, column=0, columnspan=2,
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
# excel formula engine & column operations
# --------------------------------------------------------------------------

def col_to_letter(col_idx: int) -> str:
    """Convert 0-based column index to Excel column letter (0->A, 25->Z, 26->AA)."""
    result = []
    col_idx += 1
    while col_idx > 0:
        col_idx, remainder = divmod(col_idx - 1, 26)
        result.append(chr(65 + remainder))
    return "".join(reversed(result))


def letter_to_col(letters: str) -> int:
    """Convert Excel column letter to 0-based index (A->0, Z->25, AA->26)."""
    result = 0
    for ch in str(letters).upper().strip():
        if 'A' <= ch <= 'Z':
            result = result * 26 + (ord(ch) - ord('A') + 1)
    return max(0, result - 1)


REF_PATTERN = re.compile(r'(\$?)([A-Za-z]+)(\$?)(\d+)')
# a cell reference *inside a formula*: not a piece of a longer word, and not
# the name of a function that happens to end in digits (log10, log2)
CELL_IN_FORMULA = re.compile(
    r'(?<![A-Za-z0-9_"\'])(\$?)([A-Za-z]+)(\$?)(\d+)'
    r'(?![A-Za-z0-9_"\'])(?!\s*\()')
# an error left in a formula by a deleted row or column
BROKEN_REF = re.compile(r'#[A-Za-z]+[!?]')


def renumber_formula_rows(formula: str, at_row: int, delta: int) -> str:
    """Move the row references of a formula when rows come or go.

    `at_row` is the **1-based** row where the change happens and `delta`
    how many rows appear (positive) or disappear (negative).  A reference
    to that row, or to one below it, moves with its data - the fixed ones
    (`$A$14`) as well, because it is the values themselves that moved.  A
    reference to a row that was deleted becomes `#REF!`.
    """
    def repl(match):
        col_fixed, letters, row_fixed, digits = match.groups()
        row = int(digits)
        if row < at_row:
            return match.group(0)
        if delta < 0 and row < at_row - delta:
            return "#REF!"
        return f"{col_fixed}{letters}{row_fixed}{row + delta}"

    return CELL_IN_FORMULA.sub(repl, formula)


def renumber_formula_columns(formula: str, at_col: int, delta: int) -> str:
    """The same for the columns; `at_col` is 0-based, as in the table."""
    def repl(match):
        col_fixed, letters, row_fixed, digits = match.groups()
        index = letter_to_col(letters.upper())
        if index < at_col:
            return match.group(0)
        if delta < 0 and index < at_col - delta:
            return "#REF!"
        return (f"{col_fixed}{col_to_letter(index + delta)}"
                f"{row_fixed}{digits}")

    return CELL_IN_FORMULA.sub(repl, formula)


def adjust_formula_references(formula: str, delta_row: int, delta_col: int = 0) -> str:
    """Adjust unanchored cell references in an Excel formula when filling or copying."""
    def repl(match):
        col_fixed = bool(match.group(1))
        col_letters = match.group(2).upper()
        row_fixed = bool(match.group(3))
        row_num = int(match.group(4))

        new_col = col_letters
        if not col_fixed and delta_col != 0:
            c_idx = max(0, letter_to_col(col_letters) + delta_col)
            new_col = col_to_letter(c_idx)

        new_row = row_num
        if not row_fixed and delta_row != 0:
            new_row = max(1, row_num + delta_row)

        c_prefix = "$" if col_fixed else ""
        r_prefix = "$" if row_fixed else ""
        return f"{c_prefix}{new_col}{r_prefix}{new_row}"

    return CELL_IN_FORMULA.sub(repl, formula)


class FormulaEvaluator:
    """Safe AST-based Excel formula evaluator with full mathematical and range support."""

    SAFE_FUNCS = {
        'sin': math.sin, 'cos': math.cos, 'tan': math.tan,
        'asin': math.asin, 'acos': math.acos, 'atan': math.atan,
        'sinh': math.sinh, 'cosh': math.cosh, 'tanh': math.tanh,
        'sqrt': math.sqrt, 'exp': math.exp,
        'log': math.log, 'ln': math.log, 'log10': math.log10, 'log2': math.log2,
        'abs': abs, 'round': round, 'floor': math.floor, 'ceil': math.ceil,
        'mod': lambda a, b: a % b, 'power': pow,
        'pi': lambda: math.pi, 'e': lambda: math.e,
        'radians': math.radians, 'degrees': math.degrees,
        'if': lambda cond, a, b: a if cond else b,
        'sum': lambda vals: float(sum(v for v in vals if not math.isnan(v))) if len(vals) else 0.0,
        'average': lambda vals: (float(sum(v for v in vals if not math.isnan(v))) / len([v for v in vals if not math.isnan(v)])) if any(not math.isnan(v) for v in vals) else 0.0,
        'mean': lambda vals: (float(sum(v for v in vals if not math.isnan(v))) / len([v for v in vals if not math.isnan(v)])) if any(not math.isnan(v) for v in vals) else 0.0,
        'min': lambda vals: float(min(v for v in vals if not math.isnan(v))) if any(not math.isnan(v) for v in vals) else 0.0,
        'max': lambda vals: float(max(v for v in vals if not math.isnan(v))) if any(not math.isnan(v) for v in vals) else 0.0,
        'count': lambda vals: float(len([v for v in vals if not math.isnan(v)])),
        'std': lambda vals: float(math.sqrt(sum((x - sum(vals)/len(vals))**2 for x in vals)/(len(vals)-1))) if len(vals) > 1 else 0.0,
        'stdev': lambda vals: float(math.sqrt(sum((x - sum(vals)/len(vals))**2 for x in vals)/(len(vals)-1))) if len(vals) > 1 else 0.0,
        'median': lambda vals: float(sorted(vals)[len(vals)//2]) if len(vals) else 0.0,
    }

    # names that stand for a number on their own, so that a formula such as
    # =sin((B1+C1)+pi/6) means what it says
    CONSTANTS = {'pi': math.pi, 'tau': math.tau, 'e': math.e}
    # ... but a bare column letter always wins over a constant: in a sheet
    # with five columns "e" is column E of the current row
    LETTER_CONSTANTS = ('e',)

    def __init__(self, df: pd.DataFrame, cell_formulas: dict):
        self.df = df
        self.cell_formulas = cell_formulas
        self._eval_stack = set()

    def get_cell_value(self, row: int, col: int):
        if (row, col) in self._eval_stack:
            raise ValueError("#CYCLE!")
        if not (0 <= row < len(self.df) and 0 <= col < len(self.df.columns)):
            raise ValueError("#REF!")

        if (row, col) in self.cell_formulas:
            formula = self.cell_formulas[(row, col)]
            self._eval_stack.add((row, col))
            try:
                val = self.evaluate(formula, row, col)
            finally:
                self._eval_stack.discard((row, col))
            return val
        else:
            raw = self.df.iat[row, col]
            if raw == "" or raw is None or pd.isna(raw):
                return 0.0
            try:
                return float(raw)
            except (ValueError, TypeError):
                return str(raw)

    def get_range_values(self, start_ref: str, end_ref: str):
        m1 = REF_PATTERN.match(start_ref)
        m2 = REF_PATTERN.match(end_ref)
        if not m1 or not m2:
            raise ValueError("#REF!")
        c0 = letter_to_col(m1.group(2))
        r0 = int(m1.group(4)) - 1
        c1 = letter_to_col(m2.group(2))
        r1 = int(m2.group(4)) - 1

        c_start, c_end = sorted((c0, c1))
        r_start, r_end = sorted((r0, r1))

        values = []
        for r in range(r_start, r_end + 1):
            for c in range(c_start, c_end + 1):
                try:
                    val = self.get_cell_value(r, c)
                    if isinstance(val, (int, float)):
                        v = float(val)
                        if not math.isnan(v) and not math.isinf(v):
                            values.append(v)
                except Exception:
                    pass
        return values

    def evaluate(self, expr_str: str, current_row: int = 0, current_col: int = 0):
        s = str(expr_str).strip()
        if s.startswith("="):
            s = s[1:].strip()
        if not s:
            return ""

        # a reference that a deleted row or column has broken says so
        broken = BROKEN_REF.search(s)
        if broken:
            return broken.group(0).upper()

        # Replace ^ with ** for power, and <> with !=
        s = s.replace("^", "**")
        s = s.replace("<>", "!=")

        # Replace range arguments: e.g. SUM(A1:A5) -> SUM(__range__("A1", "A5"))
        range_re = re.compile(r'([A-Za-z_][A-Za-z0-9_]*)\s*\(\s*(\$?[A-Za-z]+\$?\d+)\s*:\s*(\$?[A-Za-z]+\$?\d+)\s*\)', re.IGNORECASE)
        s = range_re.sub(r'\1(__range__("\2", "\3"))', s)

        # Replace column name references in brackets e.g. [X], [Y1] with cell in current row
        cols = [str(c) for c in self.df.columns]
        for c_idx, c_name in enumerate(cols):
            c_letter = col_to_letter(c_idx)
            s = s.replace(f"[{c_name}]", f"{c_letter}{current_row + 1}")

        # Replace single cell references with __cell__("A1").  A function
        # whose name ends in digits (log10, log2) is not a cell reference,
        # so a name followed by "(" is left alone.
        s = CELL_IN_FORMULA.sub(r'__cell__("\1\2\3\4")', s)

        # Parse AST
        try:
            tree = ast.parse(s, mode='eval')
        except SyntaxError:
            return "#ERROR!"

        was_in_stack = (current_row, current_col) in self._eval_stack
        if not was_in_stack:
            self._eval_stack.add((current_row, current_col))
        try:
            res = self._eval_ast(tree.body, current_row, current_col)
            if isinstance(res, str) and res.startswith("#"):
                return res
            if isinstance(res, (int, float)):
                res = float(res)
                if math.isnan(res):
                    return "#NUM!"
                if math.isinf(res):
                    return "#DIV/0!"
                if res.is_integer():
                    return int(res)
                return round(res, 8)
            return res
        except ZeroDivisionError:
            return "#DIV/0!"
        except ValueError as err:
            err_msg = str(err)
            return err_msg if err_msg.startswith("#") else "#VALUE!"
        except Exception:
            return "#VALUE!"
        finally:
            if not was_in_stack:
                self._eval_stack.discard((current_row, current_col))

    def _eval_ast(self, node, current_row, current_col):
        if isinstance(node, ast.Constant):
            return node.value
        elif isinstance(node, ast.Name):
            name = node.id.lower()
            cols_lower = [str(c).lower() for c in self.df.columns]
            # a constant used as a value (pi, e, tau) comes first, so that
            # "pi/6" is a number and not the function pi() divided by six -
            # unless the sheet really has a column of that name, or the
            # letter is a column letter (E is column 5)
            if name in self.CONSTANTS:
                if name in cols_lower:
                    return self.get_cell_value(current_row,
                                               cols_lower.index(name))
                if name in self.LETTER_CONSTANTS:
                    c_idx = letter_to_col(name)
                    if 0 <= c_idx < len(self.df.columns):
                        return self.get_cell_value(current_row, c_idx)
                return self.CONSTANTS[name]
            if name in self.SAFE_FUNCS:
                return self.SAFE_FUNCS[name]
            elif name in ('true', 'false'):
                return name == 'true'
            # If name is a column name or column letter, resolve for current row
            if name in cols_lower:
                c_idx = cols_lower.index(name)
                return self.get_cell_value(current_row, c_idx)
            # Check single letter column (A, B, C...)
            if len(name) <= 2 and name.isalpha():
                c_idx = letter_to_col(name)
                if 0 <= c_idx < len(self.df.columns):
                    return self.get_cell_value(current_row, c_idx)
            raise ValueError(f"#NAME? ({node.id})")
        elif isinstance(node, ast.UnaryOp):
            val = self._eval_ast(node.operand, current_row, current_col)
            if isinstance(val, str) and val.startswith("#"):
                return val
            if isinstance(node.op, ast.UAdd):
                return +val
            elif isinstance(node.op, ast.USub):
                return -val
            elif isinstance(node.op, ast.Not):
                return not val
        elif isinstance(node, ast.BinOp):
            left = self._eval_ast(node.left, current_row, current_col)
            if isinstance(left, str) and left.startswith("#"):
                return left
            right = self._eval_ast(node.right, current_row, current_col)
            if isinstance(right, str) and right.startswith("#"):
                return right
            if isinstance(node.op, ast.Add):
                return left + right
            elif isinstance(node.op, ast.Sub):
                return left - right
            elif isinstance(node.op, ast.Mult):
                return left * right
            elif isinstance(node.op, ast.Div):
                if right == 0:
                    raise ZeroDivisionError("#DIV/0!")
                return left / right
            elif isinstance(node.op, ast.FloorDiv):
                if right == 0:
                    raise ZeroDivisionError("#DIV/0!")
                return left // right
            elif isinstance(node.op, ast.Mod):
                if right == 0:
                    raise ZeroDivisionError("#DIV/0!")
                return left % right
            elif isinstance(node.op, ast.Pow):
                return left ** right
        elif isinstance(node, ast.Compare):
            left = self._eval_ast(node.left, current_row, current_col)
            if isinstance(left, str) and left.startswith("#"):
                return left
            for op, comparator in zip(node.ops, node.comparators):
                right = self._eval_ast(comparator, current_row, current_col)
                if isinstance(right, str) and right.startswith("#"):
                    return right
                if isinstance(op, ast.Eq):
                    if not (left == right): return False
                elif isinstance(op, ast.NotEq):
                    if not (left != right): return False
                elif isinstance(op, ast.Lt):
                    if not (left < right): return False
                elif isinstance(op, ast.LtE):
                    if not (left <= right): return False
                elif isinstance(op, ast.Gt):
                    if not (left > right): return False
                elif isinstance(op, ast.GtE):
                    if not (left >= right): return False
                left = right
            return True
        elif isinstance(node, ast.Call):
            func = None
            if isinstance(node.func, ast.Name):
                fname = node.func.id.lower()
                if fname == '__cell__':
                    ref = self._eval_ast(node.args[0], current_row, current_col)
                    m = REF_PATTERN.match(ref)
                    if not m: raise ValueError("#REF!")
                    col = letter_to_col(m.group(2))
                    row = int(m.group(4)) - 1
                    return self.get_cell_value(row, col)
                elif fname == '__range__':
                    r1 = self._eval_ast(node.args[0], current_row, current_col)
                    r2 = self._eval_ast(node.args[1], current_row, current_col)
                    return self.get_range_values(r1, r2)
                elif fname in self.SAFE_FUNCS:
                    func = self.SAFE_FUNCS[fname]
                else:
                    raise ValueError(f"#NAME? ({fname})")
            else:
                func = self._eval_ast(node.func, current_row, current_col)

            args = [self._eval_ast(a, current_row, current_col) for a in node.args]
            for a in args:
                if isinstance(a, str) and a.startswith("#"):
                    return a
            return func(*args)
        elif isinstance(node, ast.IfExp):
            cond = self._eval_ast(node.test, current_row, current_col)
            if isinstance(cond, str) and cond.startswith("#"):
                return cond
            return self._eval_ast(node.body, current_row, current_col) if cond else self._eval_ast(node.orelse, current_row, current_col)

        raise ValueError("#EXPR!")


def eval_column_math(df: pd.DataFrame, expr_str: str):
    """Evaluate a mathematical expression across columns, supporting numpy/vector functions."""
    s = str(expr_str).strip()
    if s.startswith("="):
        s = s[1:].strip()
    if not s:
        return np.zeros(len(df))

    s = s.replace("^", "**")
    s = s.replace("<>", "!=")

    context = {
        'np': np, 'math': math,
        'sin': np.sin, 'cos': np.cos, 'tan': np.tan,
        'asin': np.arcsin, 'acos': np.arccos, 'atan': np.arctan,
        'sinh': np.sinh, 'cosh': np.cosh, 'tanh': np.tanh,
        'sqrt': np.sqrt, 'exp': np.exp,
        'log': np.log, 'ln': np.log, 'log10': np.log10, 'log2': np.log2,
        'abs': np.abs, 'round': np.round, 'floor': np.floor, 'ceil': np.ceil,
        'pi': np.pi, 'e': np.e,
        'mean': lambda x: np.nanmean(x),
        'std': lambda x: np.nanstd(x),
        'sum': lambda x: np.nansum(x),
        'min': lambda x: np.nanmin(x),
        'max': lambda x: np.nanmax(x),
        'normalize': lambda x: (x - np.nanmin(x)) / (np.nanmax(x) - np.nanmin(x)) if (np.nanmax(x) != np.nanmin(x)) else np.zeros_like(x),
        'standardize': lambda x: (x - np.nanmean(x)) / np.nanstd(x) if np.nanstd(x) != 0 else np.zeros_like(x),
        'cumsum': lambda x: np.nancumsum(x),
        'diff': lambda x: np.gradient(x) if len(x) > 1 else np.zeros_like(x),
        'smooth': lambda x, w=5: pd.Series(x).rolling(max(1, int(w)), center=True, min_periods=1).mean().to_numpy(),
        'linspace': lambda a, b: np.linspace(a, b, len(df)),
    }

    # Bind column names and letters as numpy arrays
    for col_idx, col_name in enumerate(df.columns):
        arr = pd.to_numeric(df[col_name], errors='coerce').to_numpy(float)
        # replace NaN with 0 for computation
        arr = np.nan_to_num(arr, nan=0.0)
        context[str(col_name)] = arr
        c_letter = col_to_letter(col_idx)
        context[c_letter] = arr
        context[c_letter.lower()] = arr

    # Evaluate safely
    result = eval(s, {"__builtins__": {}}, context)
    if isinstance(result, (int, float)):
        result = np.full(len(df), float(result))
    return np.asarray(result, dtype=float)


class FormulaBar(ttk.Frame):
    """Excel-style formula bar with Cell Address Box, fx indicator, and formula entry."""

    def __init__(self, master, on_commit=None, on_cancel=None, on_fill_down=None, on_math=None):
        super().__init__(master, padding=(4, 2))
        self.master_table = master
        self.on_commit = on_commit
        self.on_cancel = on_cancel
        self.on_fill_down = on_fill_down
        self.on_math = on_math

        # Cell name / address box
        self.name_var = tk.StringVar(value="A1")
        self.name_box = ttk.Entry(self, textvariable=self.name_var, width=13, justify="center")
        self.name_box.pack(side="left", padx=(0, 4))
        self.name_box.bind("<Return>", self._jump_to_cell)
        Tooltip(self.name_box, "Active cell (type address like B5 and press Enter to jump)")

        # fx indicator
        fx_label = tk.Label(self, text="fx", font=("TkDefaultFont", 11, "bold", "italic"),
                            foreground="#1a5fb4")
        fx_label.pack(side="left", padx=(2, 6))

        # Formula / value entry
        self.formula_var = tk.StringVar()
        self.entry = ttk.Entry(self, textvariable=self.formula_var)
        self.entry.pack(side="left", fill="x", expand=True, padx=(0, 4))
        self.entry.bind("<Return>", self._commit)
        self.entry.bind("<KP_Enter>", self._commit)
        self.entry.bind("<Escape>", self._cancel)

        # Buttons: Commit (✓) and Cancel (✕).  Filling down and the column
        # operations live on the keyboard (Ctrl/Cmd+D) and in the right
        # click menus of the cells and the headings, where they belong.
        btn_commit = ttk.Button(self, text="✓", width=3, command=self._commit)
        btn_commit.pack(side="left", padx=(0, 2))
        Tooltip(btn_commit, "Accept formula (Enter)")

        btn_cancel = ttk.Button(self, text="✕", width=3, command=self._cancel)
        btn_cancel.pack(side="left", padx=(0, 4))
        Tooltip(btn_cancel, "Cancel formula (Esc)")

    def set_cell(self, address_str, formula_or_val):
        self.name_var.set(address_str)
        self.formula_var.set(formula_or_val)

    def get_text(self):
        return self.formula_var.get()

    def _commit(self, _event=None):
        if self.on_commit:
            self.on_commit(self.formula_var.get())
        return "break"

    def _cancel(self, _event=None):
        if self.on_cancel:
            self.on_cancel()
        return "break"

    def _fill_down(self):
        if self.on_fill_down:
            self.on_fill_down()

    def _math(self):
        if self.on_math:
            self.on_math()

    def _jump_to_cell(self, _event=None):
        addr = self.name_var.get().strip().upper()
        m = REF_PATTERN.match(addr)
        if m and hasattr(self.master_table, "select_cell_by_address"):
            self.master_table.select_cell_by_address(m.group(2), int(m.group(4)))
        return "break"


class ColumnMathDialog(ToolDialog):
    """Excel-style column operations / formula calculator."""

    def __init__(self, master, table, on_applied=None, on_close=None):
        super().__init__(master, "Column Operations (Math & Formulas)", on_close=on_close)
        self.table = table
        self.on_applied = on_applied
        self.df = table.df

        columns = [str(c) for c in self.df.columns]
        current_col = table.current_column or (columns[1] if len(columns) > 1 else (columns[0] if columns else "Y1"))
        if current_col not in columns and columns:
            current_col = columns[0]

        self.target_var = tk.StringVar(value=str(current_col))
        self.expr_var = tk.StringVar(value="")
        self.dynamic_var = tk.BooleanVar(value=True)

        # Top frame: Target Column
        top_frame = ttk.LabelFrame(self.body, text="Target Column", padding=8)
        top_frame.pack(fill="x")

        ttk.Label(top_frame, text="Calculate column:").grid(row=0, column=0, sticky="w", padx=(0, 6))
        self.target_combo = ttk.Combobox(top_frame, textvariable=self.target_var, state="readonly",
                                         values=columns, width=16)
        self.target_combo.grid(row=0, column=1, sticky="w")
        ttk.Button(top_frame, text="+ New Column", command=self._add_new_column).grid(row=0, column=2, padx=(8, 0))

        # Formula input frame
        formula_frame = ttk.LabelFrame(self.body, text="Formula / Expression", padding=8)
        formula_frame.pack(fill="x", pady=(8, 0))

        ttk.Label(formula_frame, text="Formula (Excel or Python):").pack(anchor="w")
        self.expr_entry = ttk.Entry(formula_frame, textvariable=self.expr_var, width=46)
        self.expr_entry.pack(fill="x", pady=(3, 6))
        self.expr_entry.focus_set()

        # Preset Operations Combobox
        preset_frame = ttk.Frame(formula_frame)
        preset_frame.pack(fill="x", pady=(0, 6))
        ttk.Label(preset_frame, text="Presets:").pack(side="left", padx=(0, 6))
        self.preset_combo = ttk.Combobox(preset_frame, state="readonly", width=36, values=[
            "Choose a preset operation...",
            "Scale by factor: Col * k",
            "Offset by constant: Col + k",
            "Add two columns: Col1 + Col2",
            "Subtract two columns: Col1 - Col2",
            "Multiply two columns: Col1 * Col2",
            "Divide two columns: Col1 / Col2",
            "Normalize to [0, 1]: (Col - min)/(max - min)",
            "Standardize (Z-score): (Col - mean)/std",
            "Subtract mean / baseline: Col - mean",
            "Cumulative sum: cumsum(Col)",
            "Derivative / Difference: diff(Col)",
            "Moving average smooth: smooth(Col, 5)",
            "Linear sequence: linspace(start, stop)",
        ])
        self.preset_combo.current(0)
        self.preset_combo.pack(side="left", fill="x", expand=True)
        self.preset_combo.bind("<<ComboboxSelected>>", self._apply_preset)

        # Quick Insert Column buttons
        col_btn_frame = ttk.Frame(formula_frame)
        col_btn_frame.pack(fill="x", pady=(2, 4))
        ttk.Label(col_btn_frame, text="Columns:").pack(side="left", padx=(0, 6))
        for col_name in columns[:6]:
            letter = col_to_letter(columns.index(col_name))
            btn = ttk.Button(col_btn_frame, text=f"{col_name} ({letter})", width=len(col_name) + 5,
                             command=lambda c=col_name: self._insert_text(f"{c} "))
            btn.pack(side="left", padx=2)

        # Quick Math buttons
        math_btn_frame = ttk.Frame(formula_frame)
        math_btn_frame.pack(fill="x", pady=(2, 4))
        ttk.Label(math_btn_frame, text="Math:").pack(side="left", padx=(0, 6))
        for op in ["+", "-", "*", "/", "^", "(", ")", "sin", "cos", "exp", "log10", "sqrt", "abs", "mean", "std"]:
            ttk.Button(math_btn_frame, text=op, width=max(2, len(op) + 1),
                       command=lambda o=op: self._insert_text(f"{o}(" if len(o) > 1 and o not in ("+", "-", "*", "/", "^", "(", ")") else f" {o} ")).pack(side="left", padx=1)

        # Dynamic formula checkbox
        ttk.Checkbutton(formula_frame, text="Apply as dynamic Excel formulas (recalculated when data changes)",
                        variable=self.dynamic_var).pack(anchor="w", pady=(6, 0))

        # Preview frame
        self.preview_frame = ttk.LabelFrame(self.body, text="Preview (first rows)", padding=6)
        self.preview_frame.pack(fill="x", pady=(8, 0))
        self.preview_label = ttk.Label(self.preview_frame, text="Enter a formula to see preview...", justify="left", foreground="#444")
        self.preview_label.pack(anchor="w")
        self.expr_var.trace_add("write", lambda *_: self._update_preview())
        self.target_var.trace_add("write", lambda *_: self._update_preview())

        # Buttons: Calculate, Close
        bar = ttk.Frame(self.body)
        bar.pack(fill="x", pady=(10, 0))
        ttk.Button(bar, text="Calculate & Apply", command=self.apply).pack(side="left")
        ttk.Button(bar, text="Close", command=self.close).pack(side="right")
        self.bind("<Return>", lambda _e: self.apply())

    def _insert_text(self, text):
        self.expr_entry.insert("insert", text)
        self.expr_entry.focus_set()

    def _add_new_column(self):
        new_name = f"Y{len(self.df.columns)}"
        name = simpledialog.askstring("New Column", "Column name:", initialvalue=new_name, parent=self)
        if name and self.table.add_column(name):
            cols = [str(c) for c in self.table.df.columns]
            self.target_combo.configure(values=cols)
            self.target_var.set(name)

    def _apply_preset(self, _event=None):
        idx = self.preset_combo.current()
        target = self.target_var.get()
        cols = [str(c) for c in self.df.columns]
        other_col = cols[1] if len(cols) > 1 and cols[0] == target else (cols[0] if cols else "X")

        presets = {
            1: f"{target} * 2",
            2: f"{target} + 10",
            3: f"{target} + {other_col}",
            4: f"{target} - {other_col}",
            5: f"{target} * {other_col}",
            6: f"{target} / {other_col}",
            7: f"normalize({target})",
            8: f"standardize({target})",
            9: f"{target} - mean({target})",
            10: f"cumsum({target})",
            11: f"diff({target})",
            12: f"smooth({target}, 5)",
            13: "linspace(0, 10)",
        }
        if idx in presets:
            self.expr_var.set(presets[idx])

    def _update_preview(self):
        expr = self.expr_var.get().strip()
        if not expr:
            self.preview_label.configure(text="Enter a formula to see preview...")
            return
        try:
            arr = eval_column_math(self.table.df, expr)
            preview_vals = [f"{arr[i]:.4g}" if np.isfinite(arr[i]) else "NaN" for i in range(min(5, len(arr)))]
            self.preview_label.configure(text=f"First rows: [ {', '.join(preview_vals)} ... ]")
        except Exception as err:
            self.preview_label.configure(text=f"Error: {err}")

    def apply(self):
        expr = self.expr_var.get().strip()
        if not expr:
            return
        target = self.target_var.get()
        if target not in self.table.df.columns:
            if not self.table.add_column(target):
                messagebox.showerror("Error", f"Could not create column '{target}'", parent=self)
                return

        target_idx = list(self.table.df.columns).index(target)
        target_letter = col_to_letter(target_idx)
        is_array_func = any(fn in expr.lower() for fn in ("smooth", "cumsum", "diff", "linspace", "normalize", "standardize"))

        if self.dynamic_var.get() and not is_array_func:
            # Build row-specific Excel formulas
            expr_clean = expr[1:].strip() if expr.startswith("=") else expr
            # Convert column names and letters into row placeholders
            # E.g. [Y1] -> Col letter
            cols = [str(c) for c in self.table.df.columns]
            for c_idx, c_name in enumerate(cols):
                c_letter = col_to_letter(c_idx)
                # replace column name surrounded by word boundary
                expr_clean = re.sub(rf'\b{re.escape(c_name)}\b', f"__{c_letter}__", expr_clean)

            # Apply row by row
            for r in range(len(self.table.df)):
                row_expr = expr_clean
                for c_idx in range(len(cols)):
                    c_letter = col_to_letter(c_idx)
                    row_expr = row_expr.replace(f"__{c_letter}__", f"{c_letter}{r + 1}")
                    # Also replace standalone column letters
                    row_expr = re.sub(rf'\b{c_letter}\b', f"{c_letter}{r + 1}", row_expr)
                    row_expr = re.sub(rf'\b{c_letter.lower()}\b', f"{c_letter}{r + 1}", row_expr)

                formula_str = f"={row_expr}"
                self.table.cell_formulas[(r, target_idx)] = formula_str

            self.table.recalculate_all()
        else:
            # Apply as static values
            try:
                arr = eval_column_math(self.table.df, expr)
                for r in range(min(len(self.table.df), len(arr))):
                    self.table.cell_formulas.pop((r, target_idx), None)
                    v = arr[r]
                    val = int(v) if (isinstance(v, float) and v.is_integer()) else round(float(v), 8)
                    self.table.df.iat[r, target_idx] = val
                    if self.table.tree.exists(str(r)):
                        self.table.tree.set(str(r), target, str(val))
            except Exception as err:
                messagebox.showerror("Math Error", f"Could not calculate expression:\n{err}", parent=self)
                return

        self.table._changed()
        if self.on_applied:
            self.on_applied()
        self.close()


# --------------------------------------------------------------------------
# data table
# --------------------------------------------------------------------------

class DataTable(ttk.Frame):
    """Treeview based table with in-place cell editing."""

    def __init__(self, master, config: Config, on_change=None, on_rename=None,
                 on_add_column=None, on_delete_column=None):
        super().__init__(master)
        self.config_obj = config
        self.on_change = on_change
        self.on_rename = on_rename
        # the program adds and deletes columns (it asks for the name)
        self.on_add_column = on_add_column
        self.on_delete_column = on_delete_column
        self.df = pd.DataFrame()
        self.current_column = None      # column of the last clicked cell/heading
        self._editor = None
        self._heading_editor = None
        self.cell_formulas: dict = {}   # (row, col) -> formula string (e.g. "=A1+B1")
        # the highlighted block of cells: (row0, col0, row1, col1)
        self.block = None
        self.anchor = (0, 0)            # where Shift+arrows measure from
        self.cursor = (0, 0)            # the cell the keyboard works on
        self._outline = []              # the four frames around the block
        self._fill_handle = None        # black square at bottom-right corner of selection
        # the blank starting sheet grows columns to fill the window
        self.auto_columns = False
        self._grow_timer = None
        self._fill_feedback = []        # 4 thin frames indicating fill extent
        self._fill_dragging = False
        self._fill_start_bounds = None
        self._fill_target_row = None
        self._fill_auto_scroll_timer = None
        self._row_selecting = False
        self._row_press = None
        self._letter_selecting = False  # a range of columns is being dragged
        self._letter_press = None       # the column the drag started on
        self._col_labels: dict = {}     # column name -> the label of its letter
        self._selecting = False         # a block is being dragged out
        self._press = None              # (x, cell) of the press that started it
        self._text_dragging = False     # the pointer is selecting cell text
        self._drag_point = None         # last pointer position of the drag
        self._auto_scroll = None        # the running auto-scroll timer

        self.style = ttk.Style(self)
        self.tree = ttk.Treeview(self, show="headings", selectmode="none",
                                 style="APlot.Treeview", takefocus=True)
        self.tree.tag_configure("block", background=BLOCK_TINT)

        # Row line numbers (1, 2, 3...) at the left side of the spreadsheet panel
        self.corner_box = tk.Frame(self, width=ROW_HEADER_WIDTH,
                                   height=CHECK_BAR_HEIGHT,
                                   relief="groove", borderwidth=1,
                                   cursor="hand2")
        self.corner_box.grid_propagate(False)
        self.corner_box_label = ttk.Label(self.corner_box, text="◢", foreground="#888888",
                                          font=("TkDefaultFont", 8))
        self.corner_box_label.place(relx=0.5, rely=0.5, anchor="center")
        self.corner_box.bind("<Button-1>", lambda _e: self.select_all_cells())
        self.corner_box_label.bind("<Button-1>", lambda _e: self.select_all_cells())

        self.row_tree = ttk.Treeview(self, show="headings", selectmode="none",
                                     style="APlot.RowHeader.Treeview", takefocus=False)
        self.row_tree["columns"] = ("#",)
        self.row_tree.heading("#", text="#", anchor="center", command=self.select_all_cells)
        self.row_tree.column("#", width=ROW_HEADER_WIDTH, minwidth=ROW_HEADER_WIDTH,
                             stretch=False, anchor="center")
        self.row_tree.tag_configure("active_row", background=HEADER_ACTIVE,
                                    foreground="#000000")

        self.row_tree.bind("<Button-1>", self._on_row_tree_click)
        self.row_tree.bind("<B1-Motion>", self._on_row_tree_drag)
        self.row_tree.bind("<ButtonRelease-1>", self._on_row_tree_release)
        self.row_tree.bind("<MouseWheel>", self._on_row_tree_wheel)
        self.row_tree.bind("<Button-4>", self._on_row_tree_wheel)
        self.row_tree.bind("<Button-5>", self._on_row_tree_wheel)

        v_scroll = ttk.Scrollbar(self, orient="vertical", command=self._yview)
        h_scroll = ttk.Scrollbar(self, orient="horizontal", command=self._xview)
        self.tree.configure(yscrollcommand=self._y_scrolled,
                            xscrollcommand=self._x_scrolled)
        self._v_scroll, self._h_scroll = v_scroll, h_scroll

        # Formula bar above the check bar and headings
        self.formula_bar = FormulaBar(self, on_commit=self._formula_bar_commit,
                                      on_cancel=self._formula_bar_cancel,
                                      on_fill_down=self.fill_down,
                                      on_math=self.open_column_math)
        self.formula_bar.grid(row=0, column=0, columnspan=3, sticky="ew", pady=(0, 2))

        # Corner box above row numbers, and check bar above column data
        self.corner_box.grid(row=1, column=0, sticky="nsew")
        self.check_bar = tk.Frame(self, height=CHECK_BAR_HEIGHT)
        self.check_bar.grid(row=1, column=1, sticky="ew")
        self.check_bar.grid_propagate(False)

        # column name -> {"B"/"T" or "L"/"R": BooleanVar} and the two widgets
        self.axis_vars: dict = {}
        self._checks: dict = {}

        self.row_tree.grid(row=2, column=0, sticky="ns")
        self.tree.grid(row=2, column=1, sticky="nsew")
        v_scroll.grid(row=2, column=2, sticky="ns")
        h_scroll.grid(row=3, column=1, sticky="ew")

        # Summary status bar at the bottom (Sum, Average, Count, Min, Max)
        self.status_bar = ttk.Frame(self)
        self.status_bar.grid(row=4, column=0, columnspan=3, sticky="ew", pady=(2, 0))
        self.status_label = ttk.Label(self.status_bar, text="", foreground="#444",
                                      font=("TkDefaultFont", 9))
        self.status_label.pack(side="left", padx=4)

        self.rowconfigure(2, weight=1)
        self.columnconfigure(0, weight=0)
        self.columnconfigure(1, weight=1)
        self.columnconfigure(2, weight=0)

        self.tree.bind("<Button-1>", self._on_click)
        self.tree.bind("<Shift-Button-1>", self._on_shift_click)
        self.tree.bind("<B1-Motion>", self._on_drag)
        self.tree.bind("<ButtonRelease-1>", self._on_drag_end)
        for seq in ("<Button-2>", "<Button-3>", "<Control-Button-1>"):
            self.tree.bind(seq, self._show_context_menu)
        self.tree.bind("<Configure>", lambda _e: self._layout_changed())
        self.tree.bind("<MouseWheel>", lambda _e: self.after(1, self._refresh_outline),
                       add="+")
        self._bind_grid_keys()
        self.apply_config()

    # -- which columns are plotted, and against which axis ------------------
    def _is_x_column(self, name):
        columns = [str(one) for one in self.df.columns]
        return bool(columns) and str(name) == columns[0]

    def _axis_family(self, index):
        """The first column belongs to the X axes, every other one to the Y."""
        return "x" if index == 0 else "y"

    def _build_checks(self, check_all=False):
        """Two check buttons and column letters per column, in the strip above the headings."""
        wanted = [str(name) for name in self.df.columns]
        previous = {name: self.column_axis(name) for name in self.axis_vars}
        for widgets in self._checks.values():
            for widget in widgets.values():
                widget.destroy()
        self._checks.clear()
        for lbl in getattr(self, "_col_labels", {}).values():
            lbl.destroy()
        self._col_labels = {}
        self.axis_vars = {}
        for index, name in enumerate(wanted):
            family = self._axis_family(index)
            first_code = AXIS_TAGS[family][0][0]
            if check_all or name not in previous:
                chosen = first_code            # a new column: the first axis
            else:
                chosen = previous[name]        # keep the choice, "none" too
            if family == "x" and chosen not in X_SIDES:
                chosen = "B"                   # the X column always feeds one
            variables, widgets = {}, {}
            for code, text, hint in AXIS_TAGS[family]:
                variable = tk.BooleanVar(value=(code == chosen))
                check = ttk.Checkbutton(
                    self.check_bar, variable=variable, text=text,
                    takefocus=False, style="APlot.Axis.TCheckbutton",
                    command=lambda n=name, c=code: self._axis_clicked(n, c))
                check.tooltip = Tooltip(check, hint)
                variables[code] = variable
                widgets[code] = check
            self.axis_vars[name] = variables
            self._checks[name] = widgets

            # the letter of the column: clicking it selects the whole column,
            # exactly as the number beside a row selects the whole row
            c_letter = col_to_letter(index)
            lbl = tk.Label(self.check_bar, text=c_letter,
                           font=("TkDefaultFont", 10, "bold"),
                           foreground=HEADER_COLOR,
                           background=self.header_background(),
                           cursor="hand2")
            lbl.bind("<Button-1>", lambda e, i=index: self._on_letter_click(i, e))
            lbl.bind("<Shift-Button-1>",
                     lambda e, i=index: self._on_letter_shift_click(i, e))
            lbl.bind("<B1-Motion>", self._on_letter_drag)
            lbl.bind("<ButtonRelease-1>", self._on_letter_release)
            lbl.bind("<Button-3>",
                     lambda e, i=index: self._show_header_context_menu(i, e))
            lbl.bind("<Button-2>",
                     lambda e, i=index: self._show_header_context_menu(i, e))
            lbl.tooltip = Tooltip(
                lbl, f"Column {c_letter}: click to select the whole column")
            self._col_labels[name] = lbl
        self._place_checks()

    def header_background(self):
        """The colour of the strip the check buttons and letters sit on."""
        try:
            return str(self.check_bar.cget("background"))
        except (tk.TclError, AttributeError):
            return "#f0f0f0"

    def _axis_clicked(self, name, code):
        """One axis per column: ticking one check button clears the other."""
        variables = self.axis_vars.get(str(name)) or {}
        variable = variables.get(code)
        if variable is None:
            return
        if variable.get():                      # it was just switched on
            for other, one in variables.items():
                if other != code:
                    one.set(False)
        elif self._is_x_column(name):
            variable.set(True)         # the data has to have an X axis
            return                     # nothing changed: no replot needed
        self._changed()

    def _place_checks(self):
        """Put the two check buttons of every column over its middle, and column letter below."""
        if not self._checks:
            return
        rows = self.tree.get_children()
        offset = 0
        try:
            offset = int(self.tree.winfo_rootx() - self.check_bar.winfo_rootx())
        except tk.TclError:
            offset = 0
        width = self.check_bar.winfo_width() or self.winfo_width()
        for index, (name, widgets) in enumerate(self._checks.items()):
            box = None
            for row in rows:            # a visible row gives the exact place
                box = self.tree.bbox(row, f"#{index + 1}")
                if box:
                    break
            if not box:
                box = self._column_span(index)
            pair = list(widgets.values())
            lbl = getattr(self, "_col_labels", {}).get(name)
            if box is None:
                for check in pair:
                    check.place_forget()
                if lbl:
                    lbl.place_forget()
                continue
            x = offset + box[0] + box[2] / 2
            if x < 0 or (width and x > width):
                for check in pair:
                    check.place_forget()
                if lbl:
                    lbl.place_forget()
                continue
            pair[0].place(x=int(x) - 2, y=12, anchor="e")
            pair[1].place(x=int(x) + 2, y=12, anchor="w")
            if lbl:
                # a strip as wide as the letter needs to be easy to hit
                strip = max(24, min(int(box[2]) - 8, LETTER_WIDTH))
                lbl.place(x=int(x), y=32, anchor="center",
                          width=strip, height=17)

    def _column_span(self, index):
        """(x, y, width, height) of one column when no row is visible."""
        columns = self.tree["columns"]
        if index >= len(columns):
            return None
        start = 0
        for other in columns[:index]:
            start += int(self.tree.column(other, "width"))
        try:
            first = float(self.tree.xview()[0])
        except (tk.TclError, ValueError, IndexError):
            first = 0.0
        total = sum(int(self.tree.column(one, "width")) for one in columns) or 1
        return (int(start - first * total), 0,
                int(self.tree.column(columns[index], "width")), 0)

    def column_axis(self, name):
        """"B"/"T" for the X column, "L"/"R" for a Y column, None if unused."""
        for code, variable in (self.axis_vars.get(str(name)) or {}).items():
            try:
                if bool(variable.get()):
                    return code
            except tk.TclError:
                return None
        return None

    def set_column_axis(self, name, code):
        """Tick one of the two check buttons of a column (None: neither)."""
        variables = self.axis_vars.get(str(name))
        if variables is None:
            return False
        if code is not None and code not in variables:
            return False
        for one, variable in variables.items():
            variable.set(one == code)
        if code is None and self._is_x_column(name):
            variables["B"].set(True)       # the X column keeps an axis
        self._changed()
        return True

    def axis_check(self, name, code):
        """The check button widget itself - used by the hints and the tests."""
        return (self._checks.get(str(name)) or {}).get(code)

    def plot_columns(self):
        """The X column plus every Y column that has an axis ticked."""
        names = [str(name) for name in self.df.columns]
        if not names:
            return []
        chosen = [names[0]]
        for name in names[1:]:
            if self.column_axis(name) in Y_SIDES:
                chosen.append(name)
        return chosen

    def plot_layout(self):
        """Which axis every plotted column belongs to."""
        names = [str(name) for name in self.df.columns]
        if not names:
            return {"x": None, "x_side": "bottom", "y": {}}
        x_name = names[0]
        x_side = X_SIDES.get(self.column_axis(x_name) or "B", "bottom")
        sides = {}
        for name in names[1:]:
            code = self.column_axis(name)
            if code in Y_SIDES:
                sides[name] = Y_SIDES[code]
        return {"x": x_name, "x_side": x_side, "y": sides}

    def plot_dataframe(self, least=1):
        """The data of the ticked columns only.

        `least` is how many columns the diagram needs.  One is enough for
        every style now: a histogram counts a single column of raw values,
        and every other diagram draws it against the row numbers.
        """
        columns = self.plot_columns()
        if len(columns) < max(1, int(least)):
            return self.df.iloc[:, :0]
        return self.df[columns].copy()

    def set_plot_column(self, name, plotted=True):
        """Plot this column on its first axis, or not at all."""
        if not plotted and self._is_x_column(name):
            return False
        if plotted:
            index = [str(one) for one in self.df.columns].index(str(name)) \
                if str(name) in [str(one) for one in self.df.columns] else 1
            return self.set_column_axis(name,
                                        AXIS_TAGS[self._axis_family(index)][0][0])
        return self.set_column_axis(name, None)

    def check_all_columns(self):
        """Every column on its first axis: the bottom X and the left Y."""
        for index, name in enumerate(self._checks):
            variables = self.axis_vars[name]
            first = AXIS_TAGS[self._axis_family(index)][0][0]
            for code, variable in variables.items():
                variable.set(code == first)
        self._changed()

    # -- the highlighted block of cells ------------------------------------
    def _bind_grid_keys(self):
        """Keys of the table itself, when no cell editor is open."""
        tree = self.tree

        def wrap(function, *args):
            def handler(_event=None):
                function(*args)
                return "break"
            return handler

        steps = {"Left": (0, -1), "Right": (0, 1), "Up": (-1, 0), "Down": (1, 0)}
        for name, (d_row, d_col) in steps.items():
            tree.bind(f"<{name}>", wrap(self.move_cursor, d_row, d_col))
            tree.bind(f"<Shift-{name}>", wrap(self.extend_block, d_row, d_col))
        tree.bind("<Return>", wrap(self.edit_cursor))
        tree.bind("<KP_Enter>", wrap(self.edit_cursor))
        tree.bind("<F2>", wrap(self.edit_cursor))
        for modifier in ("Control", "Command"):
            tree.bind(f"<{modifier}-a>", wrap(self.select_all_cells))
            tree.bind(f"<{modifier}-A>", wrap(self.select_all_cells))
            tree.bind(f"<{modifier}-c>", wrap(self.copy_block))
            tree.bind(f"<{modifier}-C>", wrap(self.copy_block))
            tree.bind(f"<{modifier}-v>", wrap(self.paste_block))
            tree.bind(f"<{modifier}-V>", wrap(self.paste_block))
            tree.bind(f"<{modifier}-x>", wrap(self.cut_block))
            tree.bind(f"<{modifier}-X>", wrap(self.cut_block))
            tree.bind(f"<{modifier}-d>", wrap(self.fill_down))
            tree.bind(f"<{modifier}-D>", wrap(self.fill_down))
            tree.bind(f"<{modifier}-space>", wrap(self.select_columns_of_block))
        tree.bind("<Shift-space>", wrap(self.select_rows_of_block))
        for sequence in ("<Delete>", "<BackSpace>"):
            tree.bind(sequence, wrap(self.clear_block))

    def _shape(self):
        return len(self.df), len(self.df.columns)

    def block_bounds(self):
        """The block as (row0, col0, row1, col1), clamped to the table."""
        rows, columns = self._shape()
        if not rows or not columns:
            return None
        if self.block is None:
            row, col = self.cursor
            self.block = (row, col, row, col)
        r0, c0, r1, c1 = self.block
        r0, r1 = sorted((max(0, min(rows - 1, r0)), max(0, min(rows - 1, r1))))
        c0, c1 = sorted((max(0, min(columns - 1, c0)),
                         max(0, min(columns - 1, c1))))
        self.block = (r0, c0, r1, c1)
        return self.block

    def block_cells(self):
        """Number of cells, rows and columns in the block."""
        bounds = self.block_bounds()
        if bounds is None:
            return (0, 0, 0)
        r0, c0, r1, c1 = bounds
        return ((r1 - r0 + 1) * (c1 - c0 + 1), r1 - r0 + 1, c1 - c0 + 1)

    def select_block(self, r0, c0, r1, c1, anchor=None, cursor=None):
        """Highlight a rectangular block of cells."""
        rows, columns = self._shape()
        if not rows or not columns:
            return None
        self.block = (r0, c0, r1, c1)
        bounds = self.block_bounds()
        self.anchor = anchor if anchor is not None else (bounds[0], bounds[1])
        self.cursor = cursor if cursor is not None else (bounds[2], bounds[3])
        self._refresh_block()
        self._update_formula_bar()
        self._update_status_bar()
        return bounds

    def select_cell(self, row, col):
        """One cell: it becomes the block, the anchor and the cursor."""
        return self.select_block(row, col, row, col,
                                 anchor=(row, col), cursor=(row, col))

    def extend_block_to(self, row, col):
        """Stretch the block from the anchor to this cell."""
        rows, columns = self._shape()
        row = max(0, min(rows - 1, int(row)))
        col = max(0, min(columns - 1, int(col)))
        a_row, a_col = self.anchor
        return self.select_block(a_row, a_col, row, col,
                                 anchor=self.anchor, cursor=(row, col))

    def extend_block(self, d_row, d_col):
        """Shift+arrow: one row or column more (or less) in the block."""
        rows, columns = self._shape()
        if not rows or not columns:
            return False
        self.block_bounds()
        row, col = self.cursor
        row = max(0, min(rows - 1, row + d_row))
        col = max(0, min(columns - 1, col + d_col))
        self.extend_block_to(row, col)
        self.tree.see(str(row))
        self._refresh_outline()
        return True

    def move_cursor(self, d_row, d_col):
        """An arrow key without Shift: one cell, and the block collapses."""
        rows, columns = self._shape()
        if not rows or not columns:
            return False
        row, col = self.cursor
        row = max(0, min(rows - 1, row + d_row))
        col = max(0, min(columns - 1, col + d_col))
        self.select_cell(row, col)
        self.tree.see(str(row))
        return True

    def select_all_cells(self):
        rows, columns = self._shape()
        if not rows or not columns:
            return False
        self.select_block(0, 0, rows - 1, columns - 1,
                          anchor=(0, 0), cursor=(rows - 1, columns - 1))
        return True

    def select_rows_of_block(self):
        """Shift+Space: the whole rows the block touches."""
        bounds = self.block_bounds()
        if bounds is None:
            return False
        r0, _c0, r1, _c1 = bounds
        self.select_block(r0, 0, r1, len(self.df.columns) - 1,
                          anchor=(r0, 0), cursor=self.cursor)
        return True

    def select_columns_of_block(self):
        """Ctrl/Cmd+Space: the whole columns the block touches."""
        bounds = self.block_bounds()
        if bounds is None:
            return False
        _r0, c0, _r1, c1 = bounds
        self.select_block(0, c0, len(self.df) - 1, c1,
                          anchor=(0, c0), cursor=self.cursor)
        return True

    def selected_rows(self):
        """Row indices of the block."""
        bounds = self.block_bounds()
        return [] if bounds is None else list(range(bounds[0], bounds[2] + 1))

    def selected_columns(self):
        """Column names of the block."""
        bounds = self.block_bounds()
        if bounds is None:
            return []
        return [str(name) for name in self.df.columns[bounds[1]:bounds[3] + 1]]

    def edit_cursor(self):
        row, col = self.cursor
        self._begin_edit(str(row), col)
        return True

    # -- how the block is shown -------------------------------------------
    def covers_whole_rows(self):
        """True when the block reaches from the first to the last column."""
        bounds = self.block_bounds()
        if bounds is None:
            return False
        return bounds[1] == 0 and bounds[3] == len(self.df.columns) - 1

    def covers_whole_columns(self):
        """True when the block reaches from the first to the last row."""
        bounds = self.block_bounds()
        if bounds is None:
            return False
        return bounds[0] == 0 and bounds[2] == len(self.df) - 1

    def _refresh_block(self):
        """Show the block: whole rows are tinted, a part of a row outlined.

        A row can only be coloured as a whole, so the tint is used only when
        the block really covers every column of those rows (Shift+Space, a
        drag across all the columns, Ctrl/Cmd+A).  A single cell or a few
        columns of it are marked by the blue rectangle alone, which keeps
        editing one cell quiet.
        """
        bounds = self.block_bounds()
        rows = set()
        if bounds is not None and self.covers_whole_rows():
            rows = set(range(bounds[0], bounds[2] + 1))
        for item in self.tree.get_children():
            wanted = ("block",) if int(item) in rows else ()
            if tuple(self.tree.item(item, "tags")) != wanted:
                self.tree.item(item, tags=wanted)

        if hasattr(self, "row_tree"):
            active_rows = set(range(bounds[0], bounds[2] + 1)) if bounds is not None else set()
            for item in self.row_tree.get_children():
                wanted = ("active_row",) if int(item) in active_rows else ()
                if tuple(self.row_tree.item(item, "tags")) != wanted:
                    self.row_tree.item(item, tags=wanted)

        self._refresh_letters(bounds)
        self._refresh_outline()

    def _refresh_letters(self, bounds=None):
        """Tint the letter of every column the block touches."""
        labels = getattr(self, "_col_labels", None)
        if not labels:
            return
        if bounds is None:
            bounds = self.block_bounds()
        active = set(range(bounds[1], bounds[3] + 1)) if bounds is not None \
            else set()
        quiet = self.header_background()
        for index, name in enumerate(str(one) for one in self.df.columns):
            label = labels.get(name)
            if label is None:
                continue
            wanted = HEADER_ACTIVE if index in active else quiet
            try:
                if str(label.cget("background")) != wanted:
                    label.configure(background=wanted)
            except tk.TclError:
                continue

    def _outline_frames(self):
        if not self._outline:
            self._outline = [tk.Frame(self.tree, background=SELECT_COLOR)
                             for _ in range(4)]
        return self._outline

    def _hide_outline(self):
        for frame in self._outline:
            frame.place_forget()
        if hasattr(self, "_fill_handle") and self._fill_handle is not None:
            self._fill_handle.place_forget()
        self._hide_fill_feedback()

    def _layout_changed(self):
        self._refresh_outline()
        self._place_checks()
        if getattr(self, "auto_columns", False):
            # the window became wider: a blank sheet fills it with columns
            if self._grow_timer is not None:
                try:
                    self.after_cancel(self._grow_timer)
                except tk.TclError:
                    pass
            self._grow_timer = self.after(60, self._grow_now)

    def _grow_now(self):
        self._grow_timer = None
        self.grow_columns_to_fit()

    def _refresh_outline(self):
        """Draw the blue rectangle around the visible part of the block and the fill handle."""
        bounds = self.block_bounds()
        if bounds is None or not self.tree.get_children():
            self._hide_outline()
            return
        r0, c0, r1, c1 = bounds
        try:
            self.tree.update_idletasks()
        except tk.TclError:
            return
        first = self._visible_cell(r0, r1, c0)
        last = self._visible_cell(r1, r0, c1, from_bottom=True)
        if first is None or last is None:
            self._hide_outline()
            return
        x0, y0 = first[0], first[1]
        x1 = last[0] + last[2]
        y1 = last[1] + last[3]
        if x1 <= x0 or y1 <= y0:
            self._hide_outline()
            return
        top, bottom, left, right = self._outline_frames()
        width, height = x1 - x0, y1 - y0
        top.place(x=x0, y=y0, width=width, height=BLOCK_LINE)
        bottom.place(x=x0, y=y1 - BLOCK_LINE, width=width, height=BLOCK_LINE)
        left.place(x=x0, y=y0, width=BLOCK_LINE, height=height)
        right.place(x=x1 - BLOCK_LINE, y=y0, width=BLOCK_LINE, height=height)

        # Black square fill handle at the bottom-right corner of the selection
        handle = self._get_fill_handle()
        handle.place(x=x1 - 4, y=y1 - 4,
                     width=FILL_HANDLE_SIZE, height=FILL_HANDLE_SIZE)
        self._lift_overlays()

    def _lift_overlays(self):
        """Keep the fill handle above the cell editor.

        The editor of a cell is a child of the table too, and it is built
        after the outline, so without this it would lie on top of the black
        fill handle - the pointer would reach the text field instead of the
        handle, and the selection could not be pulled down any more.

        Only the handle is raised, never the blue frames: those carry no
        binding of their own, so above the editor they would only make a
        two pixel dead border around the text.
        """
        handle = getattr(self, "_fill_handle", None)
        if handle is not None:
            try:
                handle.lift()
            except tk.TclError:
                pass

    def _visible_cell(self, row, other, col, from_bottom=False):
        """bbox of a cell, walking towards `other` until one is on screen."""
        step = -1 if row > other else 1
        current = row
        while True:
            if self.tree.exists(str(current)):
                bbox = self.tree.bbox(str(current), f"#{col + 1}")
                if bbox:
                    return bbox
            if current == other:
                return None
            current += step

    # -- fill handle interaction -------------------------------------------
    def _get_fill_handle(self):
        if not hasattr(self, "_fill_handle") or self._fill_handle is None:
            self._fill_handle = tk.Frame(self.tree, background="#000000", cursor="crosshair")
            self._fill_handle.bind("<Button-1>", self._on_fill_press)
            self._fill_handle.bind("<B1-Motion>", self._on_fill_drag)
            self._fill_handle.bind("<ButtonRelease-1>", self._on_fill_release)
            self._fill_handle.bind("<Double-Button-1>", self._on_fill_double_click)
            self._fill_handle.bind("<Alt-Double-Button-1>", self._on_fill_double_click)
        return self._fill_handle

    def _get_fill_feedback(self):
        if not hasattr(self, "_fill_feedback") or not self._fill_feedback:
            self._fill_feedback = [tk.Frame(self.tree, background="#555555")
                                   for _ in range(4)]
        return self._fill_feedback

    def _show_fill_feedback(self, r0, r1, c0, c1):
        first = self._visible_cell(r0, r1, c0)
        last = self._visible_cell(r1, r0, c1, from_bottom=True)
        if first is None or last is None:
            self._hide_fill_feedback()
            return
        x0, y0 = first[0], first[1]
        x1 = last[0] + last[2]
        y1 = last[1] + last[3]
        if x1 <= x0 or y1 <= y0:
            self._hide_fill_feedback()
            return
        frames = self._get_fill_feedback()
        w, h = x1 - x0, y1 - y0
        frames[0].place(x=x0, y=y0, width=w, height=1)
        frames[1].place(x=x0, y=y1 - 1, width=w, height=1)
        frames[2].place(x=x0, y=y0, width=1, height=h)
        frames[3].place(x=x1 - 1, y=y0, width=1, height=h)

    def _hide_fill_feedback(self):
        if hasattr(self, "_fill_feedback") and self._fill_feedback:
            for f in self._fill_feedback:
                f.place_forget()

    def _on_fill_press(self, event):
        self._commit_edit()
        bounds = self.block_bounds()
        if bounds is None:
            return "break"
        self._fill_dragging = True
        self._fill_start_bounds = bounds
        self._fill_target_row = bounds[2]
        self._show_fill_feedback(bounds[2], bounds[2], bounds[1], bounds[3])
        return "break"

    def _on_fill_drag(self, event):
        if not getattr(self, "_fill_dragging", False):
            return "break"
        try:
            tree_y = event.y_root - self.tree.winfo_rooty()
        except (tk.TclError, AttributeError):
            tree_y = event.y

        row_id = self.tree.identify_row(tree_y)
        r0, c0, r1, c1 = self._fill_start_bounds
        if row_id and self.tree.exists(row_id):
            target_r = max(r1, int(row_id))
        else:
            if tree_y > self.tree.winfo_height() - 10:
                target_r = min(len(self.df) - 1, self._fill_target_row + 1)
                self._start_fill_auto_scroll()
            else:
                target_r = self._fill_target_row

        self._fill_target_row = target_r
        if target_r > r1:
            self._show_fill_feedback(r1 + 1, target_r, c0, c1)
            self._show_fill_hint(r0, r1, c0, target_r)
        else:
            self._hide_fill_feedback()
            self._update_status_bar()
        return "break"

    def _show_fill_hint(self, r0, r1, column, target_r):
        """Say in the status bar what pulling the handle down will write."""
        if not hasattr(self, "status_label"):
            return
        rows = target_r - r1
        step = self.series_step(r0, r1, column)
        anchor = self.cell_number(r1, column)
        if step is None or anchor is None:
            self.status_label.configure(
                text=f"Fill down: the value is copied into {rows} more "
                     f"row{'s' if rows != 1 else ''}")
            return
        preview = ", ".join(
            self._number_text(self.series_value(anchor, step, one))
            for one in range(1, min(rows, 3) + 1))
        if rows > 3:
            preview += ", ..."
        self.status_label.configure(
            text=f"Series, step {self._number_text(step)}:  {preview}"
                 f"   ({rows} row{'s' if rows != 1 else ''})")

    def _on_fill_release(self, _event=None):
        if not getattr(self, "_fill_dragging", False):
            return "break"
        self._stop_fill_auto_scroll()
        self._hide_fill_feedback()
        self._fill_dragging = False

        r0, c0, r1, c1 = self._fill_start_bounds
        target_r = getattr(self, "_fill_target_row", r1)
        if target_r > r1:
            self._execute_fill_down(r1, target_r, c0, c1, first_r=r0)
            self.select_block(r0, c0, target_r, c1, anchor=(r0, c0), cursor=(target_r, c1))
            self.tree.see(str(target_r))
        else:
            self._update_status_bar()
        return "break"

    def _on_fill_double_click(self, _event=None):
        self._commit_edit()
        bounds = self.block_bounds()
        if bounds is None:
            return "break"
        r0, c0, r1, c1 = bounds
        target_r = self._find_neighbor_extent(r1, c0, c1)
        if target_r > r1:
            self._execute_fill_down(r1, target_r, c0, c1, first_r=r0)
            self.select_block(r0, c0, target_r, c1, anchor=(r0, c0), cursor=(target_r, c1))
            self.tree.see(str(target_r))
        return "break"

    def _find_neighbor_extent(self, r1, c0, c1):
        """Find how far down adjacent columns have non-empty data."""
        rows_count = len(self.df)
        if rows_count <= r1 + 1:
            return r1

        left_c = c0 - 1
        left_extent = r1
        if left_c >= 0:
            r = r1 + 1
            while r < rows_count:
                val = self.df.iat[r, left_c]
                if pd.isna(val) or str(val).strip() == "":
                    break
                left_extent = r
                r += 1

        right_c = c1 + 1
        right_extent = r1
        if right_c < len(self.df.columns):
            r = r1 + 1
            while r < rows_count:
                val = self.df.iat[r, right_c]
                if pd.isna(val) or str(val).strip() == "":
                    break
                right_extent = r
                r += 1

        if left_extent > r1:
            return left_extent
        if right_extent > r1:
            return right_extent

        return rows_count - 1

    # -- a mathematical series instead of a copy ---------------------------
    def cell_number(self, row, column):
        """The value of one cell as a number, or None if it is not one."""
        if not (0 <= row < len(self.df) and 0 <= column < len(self.df.columns)):
            return None
        value = self.df.iat[row, column]
        if isinstance(value, bool):
            return None
        if isinstance(value, (int, float, np.integer, np.floating)):
            number = float(value)
        else:
            text = str(value).strip()
            if not text:
                return None
            number = to_float(text)
        if number is None or not np.isfinite(number):
            return None
        return number

    def series_step(self, r0, r1, column):
        """The step of the numbers selected in one column, or None.

        **Two or more numbers** in a column are read as a mathematical
        series, and the step is their average difference - so 1 and 3 go on
        as 5, 7, 9, ... and 10, 8 as 6, 4, 2, ...  Anything that is not a
        plain number (a formula, a text, an empty cell) has no step: such a
        cell is copied, exactly as before.
        """
        if r1 <= r0:
            return None                # one single cell is copied
        values = []
        for row in range(r0, r1 + 1):
            if (row, column) in self.cell_formulas:
                return None            # a formula is carried on, not counted
            number = self.cell_number(row, column)
            if number is None:
                return None
            values.append(number)
        if len(values) < 2:
            return None
        return (values[-1] - values[0]) / (len(values) - 1)

    @staticmethod
    def series_value(anchor, step, distance):
        """The `distance`-th member of the series that follows `anchor`."""
        anchor, step = float(anchor), float(step)
        value = round(anchor + step * int(distance), 10)
        if anchor.is_integer() and step.is_integer():
            return int(round(value))
        return value

    @staticmethod
    def _number_text(value):
        """A number the way it is written into a cell."""
        number = float(value)
        if number.is_integer():
            return str(int(number))
        return f"{round(number, 10):g}"

    def _set_cell_value(self, row, column, value):
        """Write one value into the frame and into the row on the screen."""
        name = self.df.columns[column]
        try:
            self.df.iat[row, column] = value
        except (ValueError, TypeError):
            self.df[name] = self.df[name].astype(object)
            self.df.iat[row, column] = value
        if self.tree.exists(str(row)):
            try:
                empty = value is None or pd.isna(value)
            except (TypeError, ValueError):
                empty = False
            self.tree.set(str(row), name, "" if empty else str(value))

    def _execute_fill_down(self, source_r, target_r, c0, c1, first_r=None):
        """Carry the block on downwards, from `source_r` to `target_r`.

        Every column decides for itself.  Two or more **numbers** selected
        in it are a mathematical series and it is continued with their
        step; a **formula** is replicated with its row references moved
        along; anything else is simply copied - which is what a single
        cell always does.
        """
        for c in range(c0, c1 + 1):
            step = None if first_r is None else self.series_step(first_r, source_r, c)
            source_formula = self.cell_formulas.get((source_r, c))
            source_val = self.df.iat[source_r, c]
            anchor = self.cell_number(source_r, c) if step is not None else None
            col_name = self.df.columns[c]
            for r in range(source_r + 1, target_r + 1):
                if step is not None:
                    self.cell_formulas.pop((r, c), None)
                    self._set_cell_value(
                        r, c, self.series_value(anchor, step, r - source_r))
                elif source_formula is not None:
                    delta_row = r - source_r
                    adj = adjust_formula_references(source_formula, delta_row=delta_row, delta_col=0)
                    self.cell_formulas[(r, c)] = adj
                else:
                    self.cell_formulas.pop((r, c), None)
                    self._set_cell_value(r, c, copy.deepcopy(source_val))

        self.recalculate_all()
        self._changed()
        self._update_formula_bar()
        self._update_status_bar()
        self._refresh_outline()

    def _start_fill_auto_scroll(self):
        if getattr(self, "_fill_auto_scroll_timer", None) is None:
            self._fill_auto_scroll_timer = self.after(AUTO_SCROLL_MS, self._fill_auto_scroll_step)

    def _stop_fill_auto_scroll(self):
        timer = getattr(self, "_fill_auto_scroll_timer", None)
        if timer is not None:
            try:
                self.after_cancel(timer)
            except (tk.TclError, ValueError):
                pass
            self._fill_auto_scroll_timer = None

    def _fill_auto_scroll_step(self):
        self._fill_auto_scroll_timer = None
        if not getattr(self, "_fill_dragging", False):
            return
        self._yview("scroll", 1, "units")
        if self._fill_target_row < len(self.df) - 1:
            self._fill_target_row += 1
            r0, c0, r1, c1 = self._fill_start_bounds
            self._show_fill_feedback(r1 + 1, self._fill_target_row, c0, c1)
        self._start_fill_auto_scroll()

    # -- row tree interactions (line numbers on the left) ------------------
    def _on_row_tree_wheel(self, event):
        if sys.platform == "darwin":
            delta = -int(event.delta)
        elif getattr(event, "num", None) == 4:
            delta = -1
        elif getattr(event, "num", None) == 5:
            delta = 1
        else:
            delta = -int(event.delta / 120)
        self.tree.yview_scroll(delta, "units")
        if hasattr(self, "row_tree"):
            self.row_tree.yview_scroll(delta, "units")
        self.after(1, self._refresh_outline)
        return "break"

    def _on_row_tree_click(self, event):
        row_id = self.row_tree.identify_row(event.y)
        if row_id and self.row_tree.exists(row_id):
            r = int(row_id)
            if 0 <= r < len(self.df) and len(self.df.columns):
                self._commit_edit()
                self.select_block(r, 0, r, len(self.df.columns) - 1,
                                  anchor=(r, 0), cursor=(r, len(self.df.columns) - 1))
                self._row_selecting = True
                self._row_press = r
        return "break"

    def _on_row_tree_drag(self, event):
        if getattr(self, "_row_selecting", False):
            row_id = self.row_tree.identify_row(event.y)
            if row_id and self.row_tree.exists(row_id):
                r = int(row_id)
                start = getattr(self, "_row_press", r)
                r0, r1 = min(start, r), max(start, r)
                self.select_block(r0, 0, r1, len(self.df.columns) - 1,
                                  anchor=(start, 0), cursor=(r, len(self.df.columns) - 1))
        return "break"

    def _on_row_tree_release(self, _event=None):
        self._row_selecting = False
        return "break"

    # -- clicking a column letter selects the whole column ------------------
    def _column_at_root(self, x_root):
        """Which column is under this screen position (the nearest one)."""
        columns = self.tree["columns"]
        if not columns:
            return None
        try:
            x = int(x_root - self.tree.winfo_rootx())
            width = int(self.tree.winfo_width())
        except tk.TclError:
            return None
        x = max(0, min(x, max(0, width - 1)))     # past the edge: stay inside
        column_id = self.tree.identify_column(x)
        try:
            index = int(str(column_id)[1:]) - 1
        except (TypeError, ValueError):
            return None
        if 0 <= index < len(self.df.columns):
            return index
        return None

    def select_whole_columns(self, c0, c1=None, anchor_col=None):
        """Highlight one column - or a range of them - from top to bottom."""
        rows, columns = self._shape()
        if not rows or not columns:
            return False
        c0 = max(0, min(columns - 1, int(c0)))
        c1 = c0 if c1 is None else max(0, min(columns - 1, int(c1)))
        start = c0 if anchor_col is None else max(0, min(columns - 1,
                                                         int(anchor_col)))
        self.select_block(0, c0, rows - 1, c1,
                          anchor=(0, start), cursor=(rows - 1, c1))
        return True

    def _hide_letter_tooltip(self, index):
        """A press on the letter puts its own hint away."""
        names = [str(one) for one in self.df.columns]
        label = (getattr(self, "_col_labels", {}) or {}).get(
            names[index] if 0 <= index < len(names) else None)
        tooltip = getattr(label, "tooltip", None)
        if tooltip is not None:
            tooltip._left()

    def _on_letter_click(self, index, _event=None):
        """A click on A, B, C, ... takes the whole column."""
        self._hide_letter_tooltip(index)
        if not len(self.df.columns) or not len(self.df):
            return "break"
        self._commit_edit()
        self.current_column = str(self.df.columns[index]) \
            if index < len(self.df.columns) else self.current_column
        self.select_whole_columns(index)
        self._letter_selecting = True
        self._letter_press = index
        self.tree.focus_set()
        return "break"

    def _on_letter_shift_click(self, index, _event=None):
        """Shift+click on a letter stretches the block of columns."""
        self._hide_letter_tooltip(index)
        if not len(self.df.columns) or not len(self.df):
            return "break"
        self._commit_edit()
        start = self.anchor[1] if self.anchor else index
        self.select_whole_columns(start, index, anchor_col=start)
        self._letter_selecting = True
        self._letter_press = start
        self.tree.focus_set()
        return "break"

    def _on_letter_drag(self, event):
        """Dragging along the letters selects a range of columns."""
        if not getattr(self, "_letter_selecting", False):
            return "break"
        index = self._column_at_root(event.x_root)
        if index is not None:
            start = getattr(self, "_letter_press", index)
            self.select_whole_columns(start, index, anchor_col=start)
        return "break"

    def _on_letter_release(self, _event=None):
        self._letter_selecting = False
        return "break"

    # -- scrolling keeps the outline in place ------------------------------
    def _yview(self, *args):
        self.tree.yview(*args)
        if hasattr(self, "row_tree"):
            self.row_tree.yview(*args)
        self.after(1, self._refresh_outline)

    def _xview(self, *args):
        self.tree.xview(*args)
        self.after(1, self._layout_changed)

    def _y_scrolled(self, first, last):
        self._v_scroll.set(first, last)
        if hasattr(self, "row_tree"):
            self.row_tree.yview_moveto(first)
        self.after(1, self._refresh_outline)

    def _x_scrolled(self, first, last):
        self._h_scroll.set(first, last)
        self.after(1, self._layout_changed)

    # -- appearance --------------------------------------------------------
    def apply_config(self):
        size = max(6, int(self.config_obj.get("table", "font_size")))
        row_height = int(size * 2.2)
        self.style.configure("APlot.Treeview", font=("TkDefaultFont", size),
                             rowheight=row_height)
        self.style.configure("APlot.Treeview.Heading", font=("TkDefaultFont", size))
        # the row numbers take the very background of the table itself: the
        # themes of the systems differ (the one of macOS is a dark grey), and
        # a hard coded light grey strip beside a dark table looks broken
        paper = self.table_background()
        ink = self.dim_foreground(paper)
        self.style.configure("APlot.RowHeader.Treeview", font=("TkDefaultFont", size),
                             rowheight=row_height, background=paper,
                             fieldbackground=paper, foreground=ink)
        self.style.configure("APlot.RowHeader.Treeview.Heading",
                             font=("TkDefaultFont", size, "bold"))
        self.style.map("APlot.RowHeader.Treeview",
                       background=[("selected", paper)],
                       foreground=[("selected", ink)])
        try:
            self.corner_box.configure(background=paper)
        except (tk.TclError, AttributeError):
            pass
        # the little x_B / x_T / y_L / y_R switches above the columns keep
        # their own, readable size whatever the table font is
        self.style.configure("APlot.Axis.TCheckbutton",
                             font=("TkDefaultFont", AXIS_CHECK_FONT), padding=0)
        width = self.column_width()
        for column in self.tree["columns"]:
            self.tree.column(column, width=width, minwidth=MIN_COLUMN_WIDTH)
        self.after(1, self._place_checks)

    def table_background(self):
        """The colour the table itself is painted with, whatever the theme."""
        for style_name, option in (("APlot.Treeview", "fieldbackground"),
                                   ("APlot.Treeview", "background"),
                                   ("Treeview", "fieldbackground"),
                                   ("Treeview", "background")):
            try:
                found = self.style.lookup(style_name, option)
            except tk.TclError:
                found = None
            if found:
                text = str(found).strip()
                if text and text.lower() not in ("none", "systemtransparent"):
                    return text
        try:      # the last resort: ask Tk what an empty table looks like
            return str(self.tree.cget("background"))
        except tk.TclError:
            return "#ffffff"

    @staticmethod
    def dim_foreground(_background=None):
        """The colour of the row numbers: the one of the column letters."""
        return HEADER_COLOR

    def column_width(self):
        """The width of one column: never narrower than its check buttons."""
        wanted = int(self.config_obj.get("table", "column_width"))
        return max(MIN_COLUMN_WIDTH, wanted)

    # -- data --------------------------------------------------------------
    def set_dataframe(self, df, check_all=False, blank=False,
                      keep_formulas=False):
        """Show a data frame; `check_all` ticks every column again.

        `blank` marks the empty sheet the program starts with: only that one
        grows more columns by itself when the window is made wider.  Data
        that was loaded or typed is never touched.

        A new table also starts with **no stored formulas**: they belong to
        the cells of the table that is being replaced, and left behind they
        would overwrite the values that have just arrived.  The operations
        that only reshape the same table (inserting a row, deleting a
        column, sorting) pass `keep_formulas=True` and move them themselves.
        """
        self.df = df.reset_index(drop=True)
        self.df.columns = self._unique_columns(self.df.columns)
        if not keep_formulas:
            self.cell_formulas = {}
        self.auto_columns = bool(blank)
        self.refresh(check_all=check_all)
        if self.auto_columns:
            self.after_idle(self.grow_columns_to_fit)

    # -- a blank sheet fills the window with columns ------------------------
    def blank_sheet(self):
        """True while nothing has been typed into the table."""
        if not getattr(self, "auto_columns", False):
            return False
        if self.df.empty or not len(self.df.columns):
            return True
        for row in self.df.itertuples(index=False, name=None):
            for value in row:
                if value is None:
                    continue
                if isinstance(value, float) and pd.isna(value):
                    continue
                if str(value).strip():
                    return False
        return True

    def columns_that_fit(self):
        """How many columns of the normal width the table can show."""
        try:
            width = int(self.tree.winfo_width())
        except tk.TclError:
            return 0
        if width <= 1:
            return 0
        return max(1, width // max(1, self.column_width()))

    def next_column_name(self):
        """`Y1`, `Y2`, ... - the next name that is still free."""
        taken = {str(one) for one in self.df.columns}
        index = len(taken)
        while True:
            name = f"Y{index}"
            if name not in taken:
                return name
            index += 1

    def grow_columns_to_fit(self):
        """Give the blank starting sheet as many columns as the window shows.

        Widening the window brings more columns; narrowing it keeps the ones
        that are there, so nothing a user may have typed can be lost.
        """
        if not self.blank_sheet():
            return 0
        wanted = min(self.columns_that_fit(), MAX_AUTO_COLUMNS)
        have = len(self.df.columns)
        if wanted <= have:
            return 0
        for _ in range(wanted - have):
            self.df[self.next_column_name()] = ["" for _ in range(len(self.df))]
        # check_all=False keeps the ticks the user set on the sheet so far;
        # the new columns get the first axis, as any new column does
        self.refresh(check_all=False)
        return wanted - have

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

    def refresh(self, check_all=False):
        self._cancel_edit()
        self._cancel_heading_edit()
        self.tree.delete(*self.tree.get_children())
        if hasattr(self, "row_tree"):
            self.row_tree.delete(*self.row_tree.get_children())
        columns = list(self.df.columns)
        width = self.column_width()
        self.tree["columns"] = columns
        for idx, col in enumerate(columns):
            c_letter = col_to_letter(idx)
            self.tree.heading(col, text=f"{c_letter}  ({col})")
            # minwidth keeps the two check buttons - and the numbers under
            # them - readable however narrow the window is made; the
            # horizontal scroll bar takes over from there
            self.tree.column(col, width=width, minwidth=MIN_COLUMN_WIDTH,
                             anchor="center", stretch=True)
        self.update_idletasks()
        for index, row in enumerate(self.df.itertuples(index=False, name=None)):
            self.tree.insert("", "end", iid=str(index),
                             values=["" if pd.isna(v) else str(v) for v in row])
            if hasattr(self, "row_tree"):
                self.row_tree.insert("", "end", iid=str(index),
                                     values=[str(index + 1)])
        self._build_checks(check_all=check_all)
        self._refresh_block()
        self._changed()

    def _changed(self):
        if self.on_change:
            self.on_change()

    def selected_row(self):
        """The first row of the highlighted block."""
        rows = self.selected_rows()
        return rows[0] if rows else None

    def add_row(self, focus=False, column=0):
        """Append one empty row (cheap: no full rebuild) and return its index."""
        if self.df.empty and not len(self.df.columns):
            return None
        index = len(self.df)
        self.df.loc[index] = ["" for _ in self.df.columns]
        self.tree.insert("", "end", iid=str(index),
                         values=["" for _ in self.df.columns])
        if hasattr(self, "row_tree"):
            self.row_tree.insert("", "end", iid=str(index),
                                 values=[str(index + 1)])
        self._changed()
        if focus:
            self.tree.see(str(index))
            if hasattr(self, "row_tree"):
                self.row_tree.see(str(index))
            column = max(0, min(int(column), len(self.df.columns) - 1))
            self.select_cell(index, column)
            self.after(1, lambda: self._begin_edit(str(index), column))
        return index

    # -- rows and columns around the selected cell --------------------------
    def shift_row_formulas(self, at, delta=1):
        """Make room: the formulas of the rows from `at` on move by `delta`."""
        self.cell_formulas = {((row + delta) if row >= at else row, col): formula
                              for (row, col), formula
                              in self.cell_formulas.items()}

    def shift_column_formulas(self, at, delta=1):
        """The same for the columns from `at` on."""
        self.cell_formulas = {(row, (col + delta) if col >= at else col): formula
                              for (row, col), formula
                              in self.cell_formulas.items()}

    def remap_row_formulas(self, old_rows):
        """`old_rows[i]` is the row that becomes row `i`."""
        place = {old: new for new, old in enumerate(old_rows)}
        self.cell_formulas = {(place[row], col): formula
                              for (row, col), formula
                              in self.cell_formulas.items() if row in place}

    def renumber_formulas(self, rows=None, columns=None):
        """Rewrite the *text* of every formula after a move of the table.

        Moving a formula to another cell is not enough: what it points at
        has moved too.  Inserting a row above row 14 turns `=log(A14)` into
        `=log(A15)` in every formula of the sheet - the one that moved down
        with it and the ones that only refer to that row - so that every
        formula goes on saying what it said before.

        `rows` is `(1-based row, how many)` and `columns` `(0-based
        column, how many)`; a negative count is a deletion, and a
        reference to something that is gone becomes `#REF!`.
        """
        if not self.cell_formulas:
            return False
        moved = {}
        for key, formula in self.cell_formulas.items():
            text = str(formula)
            if rows is not None and rows[1]:
                text = renumber_formula_rows(text, rows[0], rows[1])
            if columns is not None and columns[1]:
                text = renumber_formula_columns(text, columns[0], columns[1])
            moved[key] = text
        self.cell_formulas = moved
        return True

    def insert_row(self, at=None, focus=True):
        """Put one empty row at `at`; `None` appends it at the end.

        The row numbers below it move down, and so do the formulas that
        were stored in those cells.
        """
        if not len(self.df.columns):
            return None
        column = self.cursor[1] if self.cursor else 0
        total = len(self.df)
        if at is None or at >= total:
            return self.add_row(focus=focus, column=column)
        at = max(0, int(at))
        blank = pd.DataFrame([["" for _ in self.df.columns]],
                             columns=self.df.columns)
        frame = pd.concat([self.df.iloc[:at], blank, self.df.iloc[at:]],
                          ignore_index=True)
        self.shift_row_formulas(at, 1)          # the cells they sit in
        self.renumber_formulas(rows=(at + 1, 1))   # ... and what they read
        growing = getattr(self, "auto_columns", False)
        self.block = None
        self.set_dataframe(frame, check_all=False, keep_formulas=True)
        self.auto_columns = growing
        self.recalculate_all()
        column = max(0, min(column, len(self.df.columns) - 1))
        self.select_cell(at, column)
        if focus:
            self.tree.see(str(at))
            self.after(1, lambda: self._begin_edit(str(at), column))
        return at

    def insert_column(self, name, at=None):
        """Put a new empty column at `at`; `None` appends it at the right."""
        name = str(name).strip()
        if not name or name in [str(one) for one in self.df.columns]:
            return False
        if at is None or at > len(self.df.columns):
            at = len(self.df.columns)
        at = max(0, int(at))
        self.df.insert(at, name, ["" for _ in range(len(self.df))])
        self.shift_column_formulas(at, 1)
        self.renumber_formulas(columns=(at, 1))
        growing = getattr(self, "auto_columns", False)
        self.refresh()
        self.auto_columns = growing
        self.recalculate_all()      # the formulas point one column further
        self.current_column = name
        self.select_cell(self.cursor[0] if self.cursor else 0, at)
        self._changed()
        return True

    def remove_column(self, name):
        """Delete one column with its data, and its stored formulas."""
        columns = [str(one) for one in self.df.columns]
        name = str(name)
        if name not in columns or len(columns) <= 1:
            return False
        at = columns.index(name)
        # the formulas of that column go with it, the ones on its right
        # move one column to the left
        self.cell_formulas = {(row, col - 1 if col > at else col): formula
                              for (row, col), formula
                              in self.cell_formulas.items() if col != at}
        self.renumber_formulas(columns=(at, -1))
        growing = getattr(self, "auto_columns", False)
        self.current_column = None
        self.block = None
        self.set_dataframe(self.df.drop(columns=[name]), check_all=False,
                           keep_formulas=True)
        self.auto_columns = growing
        self.recalculate_all()
        self.select_cell(self.cursor[0] if self.cursor else 0,
                         max(0, min(at, len(self.df.columns) - 1)))
        return True

    def delete_row(self, index=None):
        """Delete one row, or every row of the block when none is given."""
        if index is None:
            return self.delete_selected_rows()
        self.block = None
        index = int(index)
        self.remap_row_formulas([one for one in range(len(self.df))
                                 if one != index])
        self.renumber_formulas(rows=(index + 1, -1))
        self.set_dataframe(self.df.drop(index=index), keep_formulas=True)
        self.recalculate_all()
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
    def _cell_at(self, x, y):
        """(row, column) of the cell under the pointer, or None."""
        row_id = self.tree.identify_row(y)
        column_id = self.tree.identify_column(x)
        if not row_id or not column_id or not self.tree.exists(row_id):
            return None
        col = int(column_id[1:]) - 1
        if not (0 <= col < len(self.df.columns)):
            return None
        return (int(row_id), col)

    def _on_click(self, event):
        self.tree.focus_set()
        region = self.tree.identify_region(event.x, event.y)
        column_id = self.tree.identify_column(event.x)
        if region == "heading" and column_id:
            self.after(1, lambda: self._begin_heading_edit(column_id))
            return
        if region != "cell":
            return
        cell = self._cell_at(event.x, event.y)
        if cell is None:
            return
        row, col = cell
        self.select_cell(row, col)
        self._selecting = True          # a drag from here selects
        self._press = (event.x, cell)
        self._text_dragging = False
        # the editor is opened at once, so that dragging inside the cell can
        # select its text right away
        self._begin_edit(str(row), col)

    def _on_shift_click(self, event):
        """Shift+click: stretch the block from the anchor to this cell."""
        self.tree.focus_set()
        region = self.tree.identify_region(event.x, event.y)
        column_id = self.tree.identify_column(event.x)
        if region == "heading" and column_id:      # a whole column
            col = int(column_id[1:]) - 1
            if 0 <= col < len(self.df.columns) and len(self.df):
                self._commit_edit()
                self.select_block(0, col, len(self.df) - 1, col,
                                  anchor=(0, col), cursor=(len(self.df) - 1, col))
            return "break"
        cell = self._cell_at(event.x, event.y)
        if cell is None:
            return "break"
        self._commit_edit()
        self.extend_block_to(*cell)
        self._selecting = True
        return "break"

    def _header_height(self):
        """Where the rows start: the heading is above that."""
        children = self.tree.get_children()
        if children:
            bbox = self.tree.bbox(children[0], "#1")
            if bbox:
                return int(bbox[1])
        return 20

    def _pointer_inside(self, x, y):
        return (0 <= x <= self.tree.winfo_width()
                and self._header_height() <= y <= self.tree.winfo_height())

    def _on_drag(self, event):
        """Dragging selects the text of the cell, or a block of cells.

        Tk keeps sending the motion events to the table (that is where the
        button went down), so both the text selection of the cell editor and
        the automatic scrolling have to be driven from here.
        """
        if not self._selecting:
            return None
        self._drag_point = (event.x, event.y)
        inside = self._pointer_inside(event.x, event.y)
        cell = self._cell_at(event.x, event.y)
        editor = self._editor
        press_cell = self._press[1] if self._press else None
        text_drag = (editor is not None and press_cell is not None
                     and (int(editor[2]), editor[3]) == press_cell
                     and (cell == press_cell
                          or (cell is None and inside and self._text_dragging)))
        if text_drag:
            self._drag_text(editor[0], event.x)
            return "break"
        if not inside:                  # past the edge: scroll and follow
            self._start_auto_scroll()
            return "break"
        self._stop_auto_scroll()
        if cell is None:
            return None
        if cell != self.cursor or self._editor is not None:
            self._commit_edit()         # leaving the cell: select a block
            self.extend_block_to(*cell)
            self.tree.focus_set()
        if self._near_edge(event.x, event.y):
            self._start_auto_scroll()
        return "break"

    # -- scrolling on while the pointer is dragged past the edge ------------
    def _near_edge(self, x, y):
        """(dx, dy) of the scrolling the pointer asks for, or None."""
        height, width = self.tree.winfo_height(), self.tree.winfo_width()
        header = self._header_height()
        step_y = 0
        if y > height - AUTO_SCROLL_EDGE:
            step_y = 1
        elif y < header + AUTO_SCROLL_EDGE:
            step_y = -1
        step_x = 0
        if x > width - AUTO_SCROLL_EDGE:
            step_x = 1
        elif x < AUTO_SCROLL_EDGE:
            step_x = -1
        return (step_x, step_y) if (step_x or step_y) else None

    def _start_auto_scroll(self):
        if self._auto_scroll is None:
            self._auto_scroll = self.after(1, self._auto_scroll_step)

    def _stop_auto_scroll(self):
        if self._auto_scroll is not None:
            try:
                self.after_cancel(self._auto_scroll)
            except (tk.TclError, ValueError):
                pass
            self._auto_scroll = None

    def _auto_scroll_step(self):
        """Scroll one row (or column) and take the block with it."""
        self._auto_scroll = None
        if not self._selecting or self._drag_point is None:
            return
        x, y = self._drag_point
        step = self._near_edge(x, y)
        if step is None:
            return
        step_x, step_y = step
        first, last = self.tree.yview()
        if step_y > 0 and last < 1.0:
            self.tree.yview_scroll(1, "units")
        elif step_y < 0 and first > 0.0:
            self.tree.yview_scroll(-1, "units")
        if step_x:
            self.tree.xview_scroll(step_x, "units")
        self.tree.update_idletasks()
        # the cell now under the pointer, pulled back into the visible area
        header = self._header_height()
        inside_y = min(max(y, header + 2), max(header + 2,
                                               self.tree.winfo_height() - 2))
        inside_x = min(max(x, 2), max(2, self.tree.winfo_width() - 2))
        cell = self._cell_at(inside_x, inside_y)
        if cell is not None:
            self._commit_edit()
            self.extend_block_to(*cell)
            self.tree.focus_set()
        self._refresh_outline()
        self._auto_scroll = self.after(AUTO_SCROLL_MS, self._auto_scroll_step)

    def _drag_text(self, entry, x):
        """Highlight the text of the edited cell with the pointer."""
        try:
            inside = x - entry.winfo_x()
            index = entry.index(f"@{max(0, int(inside))}")
            if not self._text_dragging:
                start = entry.index(f"@{max(0, int(self._press[0] - entry.winfo_x()))}")
                entry.selection_clear()
                entry.selection_from(start)
                entry.icursor(start)
                self._text_dragging = True
            entry.selection_to(index)
            entry.icursor(index)
            entry.focus_set()
        except (tk.TclError, AttributeError):
            pass

    def _on_drag_end(self, _event=None):
        self._stop_auto_scroll()
        self._selecting = False
        self._press = None
        self._text_dragging = False
        self._drag_point = None
        return None

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
    def _bind_text_editing(self, entry, cell=False):
        """Selection and copy bindings shared by the cell and heading editors."""
        for sequence in ("<Control-a>", "<Control-A>", "<Command-a>", "<Command-A>"):
            entry.bind(sequence, self._select_all)
        for sequence in ("<Control-c>", "<Control-C>", "<Command-c>", "<Command-C>"):
            entry.bind(sequence, self._copy_text)
        if not cell:                     # the heading editor holds text only
            entry.bind("<Shift-Up>", lambda e: self._extend_selection(e, "start"))
            entry.bind("<Shift-Down>", lambda e: self._extend_selection(e, "end"))
            return
        # in a cell, Shift+Up / Shift+Down grow the highlighted block
        entry.bind("<Shift-Up>", lambda _e: self._block_from_editor(-1, 0))
        entry.bind("<Shift-Down>", lambda _e: self._block_from_editor(1, 0))
        # Shift+Left / Shift+Right select the text of the cell, and grow the
        # block once the cursor has reached the end of it
        entry.bind("<Shift-Left>", lambda e: self._shift_arrow(e, -1))
        entry.bind("<Shift-Right>", lambda e: self._shift_arrow(e, 1))

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

    def _block_from_editor(self, d_row, d_col):
        """Leave the cell editor and grow the block of cells instead."""
        editor = self._editor
        if editor is not None:
            row_id, col_index = editor[2], editor[3]
            self._commit_edit()
            self.cursor = (int(row_id), col_index)
            if self.block is None:
                self.select_cell(int(row_id), col_index)
        self.tree.focus_set()
        self.extend_block(d_row, d_col)
        return "break"

    def _shift_arrow(self, event, d_col):
        """Shift+Left/Right: select text, then grow the block sideways."""
        widget = event.widget
        cursor = widget.index("insert")
        at_edge = (cursor == 0) if d_col < 0 else (cursor == len(widget.get()))
        if not at_edge:
            target = max(0, min(len(widget.get()), cursor + d_col))
            if not widget.selection_present():
                widget.selection_from(cursor)
            widget.selection_to(target)
            widget.icursor(target)
            return "break"
        return self._block_from_editor(0, d_col)

    @staticmethod
    def _extend_selection(event, where):
        """Shift+Up / Shift+Down inside a heading editor: whole text."""
        widget = event.widget
        target = 0 if where == "start" else len(widget.get())
        if not widget.selection_present():
            widget.selection_from(widget.index("insert"))  # set the anchor
        widget.selection_to(target)
        widget.icursor(target)
        return "break"

    def block_text(self):
        """The block as tab separated text, one line per row."""
        bounds = self.block_bounds()
        if bounds is None:
            return ""
        r0, c0, r1, c1 = bounds
        lines = []
        for row in range(r0, r1 + 1):
            values = []
            for col in range(c0, c1 + 1):
                value = self.df.iat[row, col]
                values.append("" if pd.isna(value) else str(value))
            lines.append("\t".join(values))
        return "\n".join(lines)

    def copy_block(self, _event=None):
        """Ctrl/Cmd+C: the whole highlighted block, rows and columns."""
        text = self.block_text()
        if not text:
            return False
        self.clipboard_clear()
        self.clipboard_append(text)
        return True

    def forget_formulas(self, cells):
        """A cell that was emptied or written over is not calculated any more.

        The formula of such a cell has to go with its value.  Left behind,
        it would put the old value back at the very next recalculation -
        the column would look empty and come back from the dead as soon as
        anything else in the sheet was touched.
        """
        gone = [key for key in self.cell_formulas if key in set(cells)]
        for key in gone:
            del self.cell_formulas[key]
        return len(gone)

    def clear_block(self, _event=None):
        """Delete: empty every cell of the block.

        The curves break at the emptied cells instead of jumping over them.
        """
        bounds = self.block_bounds()
        if bounds is None:
            return False
        r0, c0, r1, c1 = bounds
        for col in range(c0, c1 + 1):
            column = self.df.columns[col]
            if self.df[column].dtype != object:
                self.df[column] = self.df[column].astype(object)
            for row in range(r0, r1 + 1):
                self.df.iat[row, col] = ""
                if self.tree.exists(str(row)):
                    self.tree.set(str(row), column, "")
        # the formulas of those cells are gone with their values, and what
        # the rest of the sheet reads from them is worked out again
        self.forget_formulas([(row, col) for row in range(r0, r1 + 1)
                              for col in range(c0, c1 + 1)])
        self.recalculate_all()
        self._changed()
        self._update_formula_bar()
        self._update_status_bar()
        return True

    def cut_block(self, _event=None):
        """Ctrl/Cmd+X: copy the block and empty it."""
        if not self.copy_block():
            return False
        return self.clear_block()

    def paste_block(self, text=None, _event=None):
        """Ctrl/Cmd+V: write tab separated text starting at the block.

        The shape of the text decides the shape of what is written: two
        columns of numbers fill two columns of cells, starting at the top
        left cell of the highlighted block.
        """
        if text is None:
            text = self._clipboard_text()
            if not text:
                return False
        rows = [line.split("\t")
                for line in str(text).replace("\r\n", "\n").replace("\r", "\n").split("\n")]
        while rows and not any(cell.strip() for cell in rows[-1]):
            rows.pop()
        bounds = self.block_bounds()
        if bounds is None or not rows:
            return False
        r0, c0 = bounds[0], bounds[1]
        needed = r0 + len(rows)
        if needed > len(self.df):
            if self.config_obj.get("table", "auto_extend"):
                while len(self.df) < needed:
                    self.add_row()
            else:
                rows = rows[:len(self.df) - r0]
        columns = len(self.df.columns)
        written = []
        for offset, line in enumerate(rows):
            row = r0 + offset
            if row >= len(self.df):
                break
            for shift, cell in enumerate(line):
                col = c0 + shift
                if col >= columns:
                    break
                column = self.df.columns[col]
                value = coerce(cell.strip())
                try:
                    self.df.iat[row, col] = value
                except (ValueError, TypeError):
                    self.df[column] = self.df[column].astype(object)
                    self.df.iat[row, col] = value
                if self.tree.exists(str(row)):
                    self.tree.set(str(row), column,
                                  "" if value == "" else str(value))
                written.append((row, col))
        # a pasted value replaces a formula that stood in that cell
        self.forget_formulas(written)
        self.recalculate_all()
        last_row = min(len(self.df) - 1, r0 + len(rows) - 1)
        last_col = min(columns - 1, c0 + max(len(line) for line in rows) - 1)
        self.select_block(r0, c0, last_row, last_col)
        self._changed()
        return True

    def delete_selected_rows(self):
        """Remove every row the block touches."""
        rows = self.selected_rows()
        if not rows:
            return False
        keep = [index for index in range(len(self.df)) if index not in set(rows)]
        self.block = None
        self.remap_row_formulas(keep)      # the formulas follow their rows
        # ... and what they read moves up with the rows below them
        self.renumber_formulas(rows=(min(rows) + 1, -len(rows)))
        column = self.cursor[1] if self.cursor else 0
        self.set_dataframe(self.df.iloc[keep], keep_formulas=True)
        self.recalculate_all()
        first = min(rows)
        if len(self.df):
            self.select_cell(min(first, len(self.df) - 1),
                             max(0, min(column, len(self.df.columns) - 1)))
        return True

    def _begin_edit(self, row_id, col_index, retry=True):
        self._commit_edit()
        if not self.tree.exists(row_id) or not (0 <= col_index < len(self.df.columns)):
            return
        if self._selecting and self.block_cells()[0] > 1:
            return          # the pointer is drawing a block, not editing
        # opening a cell for editing makes that cell the whole selection
        self.select_cell(int(row_id), col_index)
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
        cell_formula = self.cell_formulas.get((int(row_id), col_index))
        init_val = cell_formula if cell_formula is not None else self.tree.set(row_id, column)
        var = tk.StringVar(value=init_val)
        # exportselection=False keeps the highlighted text visible even when
        # another widget (e.g. the Treeview) takes over the X selection.
        entry = tk.Entry(self.tree, textvariable=var, exportselection=False,
                         borderwidth=1, relief="solid", justify="center",
                         insertbackground=CARET_COLOR, insertwidth=2,
                         insertontime=CARET_ON_MS, insertofftime=CARET_OFF_MS)
        entry.place(x=x, y=y, width=width, height=height)
        entry.focus_set()
        entry.icursor("end")
        entry.select_range(0, "end")
        self._editor = (entry, var, row_id, col_index)
        # the editor must not bury the fill handle of the selection
        self._lift_overlays()
        # a diagram window that was just opened may still be holding the
        # keyboard: without it the cell shows no blinking cursor at all
        self._insist_editor_focus(entry)
        self.after(30, lambda box=entry: self._insist_editor_focus(box))

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
        entry.bind("<Escape>", lambda _e: self._leave_editor())
        entry.bind("<FocusOut>", lambda _e: self._commit_edit())
        # a block on the clipboard must fill a block of cells, not one cell
        for prefix in ("Control", "Command"):
            for letter in ("v", "V"):
                entry.bind(f"<{prefix}-{letter}>", self._paste_from_editor)
            for letter in ("x", "X"):
                entry.bind(f"<{prefix}-{letter}>", self._cut_from_editor)
        self._bind_text_editing(entry, cell=True)

    def _insist_editor_focus(self, entry):
        """Keep the keyboard - and the blinking cursor - inside the cell.

        A diagram window that has just been opened (or a property window
        that was used last) may still own the keyboard of the application.
        The cell editor then shows no cursor and swallows nothing that is
        typed, so it takes the keyboard back for itself.
        """
        if self._editor is None or self._editor[0] is not entry:
            return None
        try:
            if not entry.winfo_exists() or not entry.winfo_ismapped():
                return None
            if entry.focus_displayof() is not entry:
                entry.focus_force()
        except (tk.TclError, KeyError):
            pass
        return None

    # -- the clipboard while a cell is being edited -------------------------
    def _clipboard_text(self):
        try:
            return str(self.clipboard_get())
        except tk.TclError:
            return ""

    @staticmethod
    def is_block_text(text):
        """True when the clipboard holds more than one cell."""
        cleaned = str(text).replace("\r", "")
        while cleaned.endswith("\n"):
            cleaned = cleaned[:-1]
        return "\t" in cleaned or "\n" in cleaned

    def _paste_from_editor(self, _event=None):
        """Ctrl/Cmd+V in a cell: a block of cells fills a block of cells.

        A single value is left to the text editor, so it can be pasted into
        the middle of a cell; anything with tabs or line breaks is written
        into the table starting at the edited cell.
        """
        text = self._clipboard_text()
        if not self.is_block_text(text):
            return None                  # one value: the normal text paste
        editor = self._editor
        if editor is not None:
            row_id, col_index = editor[2], editor[3]
            self._commit_edit()
            self.select_cell(int(row_id), col_index)
        self.tree.focus_set()
        self.paste_block(text)
        return "break"

    def _cut_from_editor(self, event=None):
        """Ctrl/Cmd+X in a cell: the selected text, or the whole block."""
        entry = getattr(event, "widget", None)
        if entry is not None and entry.selection_present():
            return None                  # cutting text inside the cell
        editor = self._editor
        if editor is not None:
            row_id, col_index = editor[2], editor[3]
            self._commit_edit()
            self.select_cell(int(row_id), col_index)
        self.tree.focus_set()
        self.cut_block()
        return "break"

    def _leave_editor(self):
        """Escape: close the editor and work on the block with the keys."""
        editor = self._editor
        if editor is not None:
            self.cursor = (int(editor[2]), editor[3])
        self._cancel_edit()
        self.tree.focus_set()
        self._refresh_block()
        return "break"

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
        text_val = str(text).strip()
        if text_val.startswith("="):
            self.cell_formulas[(row, col_index)] = text_val
            value = self.eval_formula(text_val, row, col_index)
        else:
            self.cell_formulas.pop((row, col_index), None)
            value = coerce(text_val)

        try:
            self.df.iat[row, col_index] = value
        except (ValueError, TypeError):
            self.df[column] = self.df[column].astype(object)
            self.df.iat[row, col_index] = value

        self.recalculate_all()
        if self.tree.exists(row_id):
            self.tree.set(row_id, column, "" if value == "" else str(value))
        self._changed()
        self._update_formula_bar()
        self._update_status_bar()

    def eval_formula(self, formula_str, row, col):
        evaluator = FormulaEvaluator(self.df, self.cell_formulas)
        return evaluator.evaluate(formula_str, row, col)

    def recalculate_all(self):
        """Recalculate all formula cells across the table."""
        if not self.cell_formulas:
            return
        evaluator = FormulaEvaluator(self.df, self.cell_formulas)
        for (r, c), formula in list(self.cell_formulas.items()):
            if r < len(self.df) and c < len(self.df.columns):
                val = evaluator.evaluate(formula, r, c)
                col_name = self.df.columns[c]
                try:
                    self.df.iat[r, c] = val
                except (ValueError, TypeError):
                    self.df[col_name] = self.df[col_name].astype(object)
                    self.df.iat[r, c] = val
                if self.tree.exists(str(r)):
                    self.tree.set(str(r), col_name, "" if val == "" else str(val))

    def fill_down(self):
        """Excel-style Fill Down (Ctrl+D): replicate top cell formula/value down the selection."""
        bounds = self.block_bounds()
        if bounds is None:
            return False
        r0, c0, r1, c1 = bounds
        if r0 == r1:
            if r0 > 0:
                fill_r0 = r0 - 1
                fill_r1 = r0
            else:
                return False
        else:
            fill_r0 = r0
            fill_r1 = r1

        for c in range(c0, c1 + 1):
            top_formula = self.cell_formulas.get((fill_r0, c))
            top_val = self.df.iat[fill_r0, c]
            col_name = self.df.columns[c]
            for r in range(fill_r0 + 1, fill_r1 + 1):
                if top_formula is not None:
                    adjusted = adjust_formula_references(top_formula, delta_row=(r - fill_r0), delta_col=0)
                    self.cell_formulas[(r, c)] = adjusted
                else:
                    self.cell_formulas.pop((r, c), None)
                    try:
                        self.df.iat[r, c] = copy.deepcopy(top_val)
                    except (ValueError, TypeError):
                        self.df[col_name] = self.df[col_name].astype(object)
                        self.df.iat[r, c] = copy.deepcopy(top_val)

        self.recalculate_all()
        self._changed()
        self._update_formula_bar()
        self._update_status_bar()
        return True

    def select_cell_by_address(self, col_letter, row_1_based):
        col_idx = letter_to_col(col_letter)
        row_idx = row_1_based - 1
        if 0 <= row_idx < len(self.df) and 0 <= col_idx < len(self.df.columns):
            self.select_cell(row_idx, col_idx)
            self.tree.see(str(row_idx))

    def _update_formula_bar(self):
        if not hasattr(self, "formula_bar") or not len(self.df.columns) or not len(self.df):
            return
        r, c = self.cursor
        r = max(0, min(len(self.df) - 1, r))
        c = max(0, min(len(self.df.columns) - 1, c))
        c_letter = col_to_letter(c)
        c_name = str(self.df.columns[c])
        addr = f"{c_letter}{r + 1}"
        display_name = f"{addr} ({c_name})"

        if (r, c) in self.cell_formulas:
            formula_text = self.cell_formulas[(r, c)]
        else:
            val = self.df.iat[r, c]
            formula_text = "" if pd.isna(val) else str(val)
        self.formula_bar.set_cell(display_name, formula_text)

    def _update_status_bar(self):
        if not hasattr(self, "status_label"):
            return
        bounds = self.block_bounds()
        if bounds is None:
            self.status_label.configure(text="")
            return
        r0, c0, r1, c1 = bounds
        total_cells = (r1 - r0 + 1) * (c1 - c0 + 1)
        if total_cells <= 1:
            self.status_label.configure(text="")
            return

        nums = []
        for r in range(r0, r1 + 1):
            for c in range(c0, c1 + 1):
                val = self.df.iat[r, c]
                if isinstance(val, (int, float)) and np.isfinite(val):
                    nums.append(float(val))
                else:
                    try:
                        n = float(str(val).strip().replace(",", "."))
                        if np.isfinite(n):
                            nums.append(n)
                    except (ValueError, TypeError):
                        pass

        if nums:
            count = len(nums)
            total = sum(nums)
            avg = total / count
            min_v = min(nums)
            max_v = max(nums)
            text = f"Selected: {total_cells} cells (Numeric: {count})  |  Sum: {total:.4g}  |  Average: {avg:.4g}  |  Min: {min_v:.4g}  |  Max: {max_v:.4g}"
        else:
            text = f"Selected: {total_cells} cells"
        self.status_label.configure(text=text)

    def _formula_bar_commit(self, text):
        r, c = self.cursor
        if not (0 <= r < len(self.df) and 0 <= c < len(self.df.columns)):
            return
        text_val = str(text).strip()
        column = self.df.columns[c]
        if text_val.startswith("="):
            self.cell_formulas[(r, c)] = text_val
            val = self.eval_formula(text_val, r, c)
        else:
            self.cell_formulas.pop((r, c), None)
            val = coerce(text_val)

        try:
            self.df.iat[r, c] = val
        except (ValueError, TypeError):
            self.df[column] = self.df[column].astype(object)
            self.df.iat[r, c] = val

        self.recalculate_all()
        if self.tree.exists(str(r)):
            self.tree.set(str(r), column, "" if val == "" else str(val))
        self._changed()
        self._update_formula_bar()
        self._update_status_bar()

    def _formula_bar_cancel(self):
        self._update_formula_bar()

    def open_column_math(self):
        ColumnMathDialog(self.winfo_toplevel(), self)

    def sort_column(self, col_idx, ascending=True):
        if not len(self.df) or not (0 <= col_idx < len(self.df.columns)):
            return
        col_name = self.df.columns[col_idx]
        try:
            num_series = pd.to_numeric(self.df[col_name], errors='coerce')
            if num_series.notna().sum() > len(self.df) * 0.5:
                sorted_df = self.df.iloc[num_series.argsort(kind='stable') if ascending else (-num_series).argsort(kind='stable')]
            else:
                sorted_df = self.df.sort_values(by=col_name, ascending=ascending, kind='stable')
        except Exception:
            sorted_df = self.df.sort_values(by=col_name, ascending=ascending, kind='stable')

        self.remap_row_formulas(list(sorted_df.index))
        self.set_dataframe(sorted_df.reset_index(drop=True),
                           check_all=False, keep_formulas=True)
        self.recalculate_all()
        self._changed()

    def _show_context_menu(self, event):
        region = self.tree.identify_region(event.x, event.y)
        column_id = self.tree.identify_column(event.x)
        if region == "heading" and column_id:
            col_idx = int(column_id[1:]) - 1
            if 0 <= col_idx < len(self.df.columns):
                self._show_header_context_menu(col_idx, event)
            return

        cell = self._cell_at(event.x, event.y)
        if cell is not None:
            bounds = self.block_bounds()
            if bounds is None or not (bounds[0] <= cell[0] <= bounds[2] and bounds[1] <= cell[1] <= bounds[3]):
                self.select_cell(*cell)

        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label=f"Cut ({MODIFIER}+X)", command=self.cut_block)
        menu.add_command(label=f"Copy ({MODIFIER}+C)", command=self.copy_block)
        menu.add_command(label=f"Paste ({MODIFIER}+V)", command=self.paste_block)
        menu.add_separator()
        menu.add_command(label=f"Fill Down ({MODIFIER}+D)", command=self.fill_down)
        menu.add_command(label="Column Math...", command=self.open_column_math)
        menu.add_separator()
        menu.add_command(label="Clear Cells (Delete)", command=self.clear_block)
        menu.add_separator()
        menu.add_command(label="Insert Row Above",
                         command=lambda: self.insert_row(self.cursor[0]))
        menu.add_command(label="Insert Row Below",
                         command=lambda: self.insert_row(self.cursor[0] + 1))
        menu.add_command(label="Delete Row(s)", command=self.delete_selected_rows)
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _ask_new_column(self, where, col_idx):
        """The program asks for the name and inserts the column."""
        if self.on_add_column:
            return self.on_add_column(where, col_idx)
        return self.insert_column(self.next_column_name(),
                                  col_idx if where == "before" else col_idx + 1)

    def _ask_delete_column(self, name):
        if self.on_delete_column:
            return self.on_delete_column(name)
        return self.remove_column(name)

    def _show_header_context_menu(self, col_idx, event):
        col_name = str(self.df.columns[col_idx])
        self.current_column = col_name

        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label=f"Calculate Column '{col_name}'...", command=self.open_column_math)
        menu.add_separator()
        menu.add_command(label="Sort Ascending (A → Z)", command=lambda: self.sort_column(col_idx, ascending=True))
        menu.add_command(label="Sort Descending (Z → A)", command=lambda: self.sort_column(col_idx, ascending=False))
        menu.add_separator()
        menu.add_command(label="Fill Down (Ctrl+D)", command=self.fill_down)
        menu.add_separator()
        menu.add_command(
            label="Insert Column Before...",
            command=lambda: self._ask_new_column("before", col_idx))
        menu.add_command(
            label="Insert Column After...",
            command=lambda: self._ask_new_column("after", col_idx))
        menu.add_command(label=f"Rename '{col_name}'...", command=lambda: self._begin_heading_edit(f"#{col_idx + 1}"))
        menu.add_command(label=f"Delete Column '{col_name}'",
                         command=lambda: self._ask_delete_column(col_name))
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()


# --------------------------------------------------------------------------
# interactive plot window
# --------------------------------------------------------------------------

class PlotWindow(tk.Toplevel):
    """Figure window: all plot related interaction lives here."""

    # the copied object, shared by every diagram window of the program
    _clipboard = None

    HINT = ("One click selects (a text turns blue), a slow second click "
            "writes the text, a double click opens its properties   |   "
            "A curve: one click   |   Drag: move   |   "
            "Drag a control point: resize\n"
            "\"T\", the shape and the arrow button: add text, drawings and "
            "arrows   |   Shift: arrows at 45 deg steps   |   "
            f"{ACCEL_NAME}+C: copy the object, or the whole figure   |   "
            f"{ACCEL_NAME}+V: paste   |   "
            f"{ACCEL_NAME}+S: save   |   {ACCEL_NAME}+E: export   |   "
            "Arrow keys: move   |   Delete: remove")

    def __init__(self, master, df: pd.DataFrame, config: Config, app=None,
                 layout=None, plot_style="line_symbol"):
        super().__init__(master)
        self.title("Interactive Graph")
        self.settings = config
        self.app = app          # gives this window the full application menu
        plot_cfg = config.section("plot")
        grid_cfg = config.section("grid")
        self.geometry(f"{config.get('window', 'plot_width')}x"
                      f"{config.get('window', 'plot_height')}")

        self.df = df
        self.plot_style = plot_style
        self.series_style: dict = {}          # Y column name -> plot style code
        self.bar_containers: dict = {}        # Y column name -> BarContainer
        self.bar_cfg: dict = {}               # Y column name -> {width, color, alpha, edgecolor, edgewidth}
        self.errorbar_containers: dict = {}   # Y column name -> ErrorbarContainer
        self.error_cfg: dict = {}             # Y column name -> {type, value, column, capsize, capthick, elinewidth, color}
        self.histogram_cfg: dict = {}         # column name -> {bins, color, alpha, edgecolor, edgewidth}
        self.histogram_edges: dict = {}       # column name -> the bin edges it was counted with
        self.histogram_drawn: set = set()     # columns whose curve carries counts
        self.stairs_cfg: dict = {}            # column -> {edges, color, width, fill, ...}
        self.stairs_patches: dict = {}         # column -> the StepPatch of ax.stairs
        self.hist2d_cfg: dict = {}            # column -> {xbins, ybins, cmap, alpha, bar}
        self.hist2d_meshes: dict = {}         # column -> the QuadMesh of ax.hist2d
        self.hist2d_bars: dict = {}           # column -> the colour bar beside it
        self.pie_cfg: dict = {}               # column -> {start, percent, hole, labels, ...}
        self.pie_wedges: dict = {}            # column -> the wedges of ax.pie
        self.pie_texts: dict = {}             # column -> the texts drawn on it
        # in an error bar diagram: mean column -> the std column beside it
        self.error_partner: dict = {}
        self.lines: list[Line2D] = []
        self.series: dict = {}          # Y column name -> curve
        self.x_col = str(df.columns[0]) if len(df.columns) else ""
        self._auto_x_label = self.x_col   # the label as long as it is not renamed
        self.legends: dict = {}         # Y column name -> its own legend box
        # which axis every column belongs to: the single X column feeds the
        # bottom or the top X axis, every curve the left or the right Y axis
        self.layout = self._clean_layout(df, layout)
        self.x_side = self.layout["x_side"]
        self.series_axis: dict = {}     # Y column name -> "left" / "right"
        self._color_index = 0           # one colour per curve, on both axes
        self.ax2 = None                 # the right hand Y axis, when it is used
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
        # the four sides of the plot area can be selected and pulled
        self.frame_sides = {name: name for name in FRAME_ENDS}
        self._inline = None             # the in-place text editor, while open
        self._rename_click = None       # (kind, key, time) of the last click
        self._rename_prev = None        # the same, one click earlier
        self._pending_rename = None     # a slow second click, waiting for the
                                        # release: a drag moves the text instead
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
        self.text_offset = {"title": (0.0, 0.0), "x": (0.0, 0.0),
                            "y": (0.0, 0.0), "y2": (0.0, 0.0)}
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
                    # every axis carries its own colour and its two switches
                    "axis_color": safe_hex(config.get("frame", "color"),
                                           "#000000"),
                    "label_on": True, "ticks_on": True,
                    "grid": dict(grid_defaults)}
            for which in ("x", "y", "y2")
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
        self.protocol("WM_DELETE_WINDOW", self.close_window)
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

        button_background = "#999999"
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
        if self._inline is not None:
            return None        # the keyboard belongs to the little text editor
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
        """This diagram window became the active one: it takes the keyboard.

        A widget of this very window keeps it (a text being written in the
        little in-place editor, for instance), and so does a cell of the
        spreadsheet that is open for editing - it must keep its blinking
        cursor.  The keyboard is taken back from anything else that belongs
        to another window: after a property dialog was used, its own field
        may still be holding it.
        """
        try:
            current = self.focus_displayof()
        except (tk.TclError, KeyError):
            current = None
        if current is None or current is self:
            self.take_focus()
            return None
        try:
            if current.winfo_toplevel() is self:
                return None            # a widget of this window: it keeps it
        except tk.TclError:
            current = None
        app = getattr(self, "app", None)
        if app is not None and current is not None:
            try:
                if app.keyboard_busy(current):
                    return None        # a cell is being written: leave it
            except (tk.TclError, AttributeError):
                pass
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
                bind_both(f"<{modifier}-{letter}>", wrap(self.copy_shortcut))
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

    # -- the four axes: bottom / top X, left / right Y ----------------------
    @staticmethod
    def _clean_layout(df, layout):
        """Which axis every column of the data belongs to, safely defaulted."""
        columns = [str(one) for one in df.columns]
        given = layout or {}
        side = "top" if str(given.get("x_side")) == "top" else "bottom"
        raw = given.get("y") or {}
        sides = {name: ("right" if str(raw.get(name, "left")) == "right"
                        else "left")
                 for name in columns[1:]}
        return {"x": columns[0] if columns else None,
                "x_side": side, "y": sides}

    def plot_axes(self):
        """Every axes that can carry curves: the main one and the twin."""
        return [self.ax] if self.ax2 is None else [self.ax, self.ax2]

    def series_side(self, column):
        """"left" or "right": the Y axis one curve is drawn against."""
        return self.series_axis.get(column, "left")

    def right_axis_active(self):
        """True while at least one curve belongs to the right Y axis."""
        return any(side == "right" for side in self.series_axis.values())

    def axes_for_side(self, side):
        return self.ensure_right_axis() if side == "right" else self.ax

    def ensure_right_axis(self):
        """The second Y axis on the right, built the first time it is needed."""
        if self.ax2 is not None:
            return self.ax2
        ax2 = self.ax.twinx()          # same X axis, its own Y scale
        self.ax2 = ax2
        ax2.patch.set_visible(False)
        ax2.grid(False)
        for spine in ax2.spines.values():
            spine.set_visible(False)   # the frame is drawn by the main axes
        ax2.set_ylabel("")
        ax2.yaxis.label.set_picker(True)
        self._text_base["y2"] = ax2.yaxis.label.get_transform()
        self.apply_axis("y2", {**self.axis_cfg["y2"], "label": ""}, redraw=False)
        ax2.set_position(self.ax.get_position())
        return ax2

    def left_axis_active(self):
        """True while at least one curve belongs to the left Y axis."""
        return any(side == "left" for side in self.series_axis.values())

    def used_sides(self):
        """The sides of the plot area that really carry an axis.

        `No frame (X and Y only)` draws exactly these: the X axis on the
        side the `x_B` / `x_T` check button chose, and the Y axis - or both
        Y axes - the curves are drawn against.  So a diagram of a top X axis
        and a right Y axis shows those two lines and nothing else.
        """
        if self.plot_style == "pie":
            return []                  # a pie stands on no axis
        sides = ["top" if self.x_side == "top" else "bottom"]
        right = self.right_axis_active()
        if self.left_axis_active() or not right:
            sides.append("left")
        if right:
            sides.append("right")
        return sides

    def left_axis_shown(self):
        """True while the left Y axis carries a scale worth drawing."""
        return self.left_axis_active() or not self.right_axis_active()

    def _apply_axis_sides(self):
        """Draw the X axis at the bottom or at the top, and the right Y axis.

        Only the axes that are really used show their numbers: with every
        curve on the right hand scale the left one disappears completely,
        numbers, tick marks and label together.
        """
        top = self.x_side == "top"
        both = self.frame_cfg.get("style") in ("box_in", "box_out")
        right = self.right_axis_active()
        left = self.left_axis_shown()
        # the "Tick range, labels and fonts" switch of each axis page
        x_ticks = bool(self.axis_cfg["x"].get("ticks_on", True))
        y_ticks = bool(self.axis_cfg["y"].get("ticks_on", True))
        y2_ticks = bool(self.axis_cfg["y2"].get("ticks_on", True))
        self.ax.xaxis.set_ticks_position("top" if top else "bottom")
        self.ax.xaxis.set_label_position("top" if top else "bottom")
        self.ax.tick_params(axis="x", which="both",
                            top=(both or top) and x_ticks,
                            bottom=(both or not top) and x_ticks,
                            labeltop=top and x_ticks,
                            labelbottom=(not top) and x_ticks)
        # with a closed frame the opposite side keeps its tick marks, but not
        # when the right hand Y axis has a scale of its own
        self.ax.yaxis.set_visible(left)
        self.ax.tick_params(axis="y", which="both",
                            left=(left or both) and y_ticks,
                            right=(both and not right) and y_ticks,
                            labelleft=left and y_ticks, labelright=False)
        if self.ax2 is not None:
            self.ax2.set_visible(right)
            self.ax2.yaxis.set_ticks_position("right")
            self.ax2.yaxis.set_label_position("right")
            self.ax2.tick_params(axis="y", which="both", left=False,
                                 right=right and y2_ticks,
                                 labelleft=False, labelright=right and y2_ticks)
        self._apply_y_grid()
        self._apply_axis_colors()
        return None

    def spine_owner(self, name):
        """Which axis page owns the colour of one side of the plot area."""
        if name in HORIZONTAL_SIDES:
            return "x"
        if name == "left":
            return "y"
        return "y2" if self.right_axis_active() else "y"

    def axis_color(self, which):
        """The colour of one axis line and of its tick marks."""
        cfg = self.axis_cfg.get(which) or {}
        return safe_hex(cfg.get("axis_color", "#000000"), "#000000")

    def _apply_axis_colors(self):
        """Every axis paints its own line and its own tick marks."""
        for name, spine in self.ax.spines.items():
            spine.set_color(self.axis_color(self.spine_owner(name)))
        self.ax.tick_params(axis="x", which="both", color=self.axis_color("x"))
        self.ax.tick_params(axis="y", which="both", color=self.axis_color("y"))
        if self.ax2 is not None:
            self.ax2.tick_params(axis="y", which="both",
                                 color=self.axis_color("y2"))
        return None

    def _apply_y_grid(self):
        """The Y grid belongs to the Y axis whose numbers are shown."""
        owner = "y" if self.left_axis_shown() else "y2"
        for which, ax in (("y", self.ax), ("y2", self.ax2)):
            if ax is None:
                continue
            cfg = self.axis_cfg[which]
            grid = cfg["grid"]
            if which == owner and grid["major"]:
                ax.grid(True, which="major", axis="y", color=grid["color"],
                        linestyle=grid["style"], linewidth=grid["width"])
            else:
                ax.grid(False, which="major", axis="y")
            if which == owner and grid["minor"] and cfg["minor"]:
                ax.grid(True, which="minor", axis="y", color=grid["color"],
                        linestyle=grid["style"],
                        linewidth=max(0.3, grid["width"] * 0.6))
            else:
                ax.grid(False, which="minor", axis="y")
        return None

    def set_x_side(self, side, redraw=True):
        """Put the X axis under or above the plot area."""
        side = "top" if str(side) == "top" else "bottom"
        if side == self.x_side:
            return False
        self.x_side = side
        self.layout["x_side"] = side
        self.apply_frame(self.frame_cfg, redraw=False)   # spines follow
        if redraw:
            self.draw()
        return True

    def move_series(self, column, side):
        """Draw one curve against the left or the right Y axis."""
        side = "right" if str(side) == "right" else "left"
        line = self.series.get(column)
        if line is None:
            return False
        target = self.axes_for_side(side)
        if line.axes is not target:
            try:
                line.remove()
            except (ValueError, AttributeError):
                pass
            target.add_line(line)
            line.set_transform(target.transData)
        changed = self.series_axis.get(column) != side
        self.series_axis[column] = side
        self.refresh_fill(column)
        if changed:
            self._rescale()
            self.apply_frame(self.frame_cfg, redraw=False)
        return changed

    def measure_data(self, ax, scalex=True, scaley=True):
        """Fit the automatic range to the curves, ignoring the filled areas.

        A fill that reaches "down to the axis" takes its baseline from the
        range that is valid at that moment.  Left in the calculation it
        would push that baseline further down at every redraw - the range
        would creep away, and a diagram would not even come back from its
        own file unchanged.  So the areas are hidden while the range is
        measured: they are a picture of the curves, not data of their own.
        """
        hidden = [fill for fill in self.fills.values()
                  if getattr(fill, "axes", None) is ax and fill.get_visible()]
        for fill in hidden:
            fill.set_visible(False)
        try:
            ax.relim(visible_only=True)
            ax.autoscale_view(scalex=scalex, scaley=scaley)
        finally:
            for fill in hidden:
                fill.set_visible(True)
        return None

    def _rescale(self):
        """Let the automatic ranges follow the data of both Y axes."""
        if self.plot_style == "pie" and not [
                name for name, style in self.series_style.items()
                if style != "pie"]:
            return                     # a pie has no range to follow
        auto_x = self.axis_cfg["x"]["auto"]
        auto_y = self.axis_cfg["y"]["auto"]
        if (auto_x or auto_y) and self.ax.lines:
            self.measure_data(self.ax, scalex=auto_x, scaley=auto_y)
        if self.ax2 is not None and self.ax2.lines:
            if self.axis_cfg["y2"]["auto"]:
                self.measure_data(self.ax2, scalex=False, scaley=True)

    @staticmethod
    def _series_data(df, x_col, y_col):
        """Numeric X/Y pairs of one column, gaps kept as gaps.

        Nothing is thrown away: every empty cell - in the Y column, in the X
        column, or a whole empty row - becomes "not a number", and matplotlib
        neither draws a point there nor connects the two sides of it.  So a
        gap left in the table really is a gap in the curve instead of a
        straight line across it.
        """
        data = pd.DataFrame({
            "x": pd.to_numeric(df[x_col], errors="coerce"),
            "y": pd.to_numeric(df[y_col], errors="coerce"),
        })
        return (data["x"].to_numpy(dtype=float),
                data["y"].to_numpy(dtype=float))

    @staticmethod
    def _cycle_color(index):
        """The index-th colour of matplotlib's own colour sequence."""
        cycle = matplotlib.rcParams.get("axes.prop_cycle")
        colors = list((cycle.by_key().get("color") if cycle else None) or [])
        if not colors:
            return PALETTE_FALLBACK
        return colors[int(index) % len(colors)]

    def _create_line(self, x, y, y_col, x_col, side="left", style=None):
        """New curve drawn with the defaults of the configuration file.

        The colour is taken from the sequence by hand, so that a curve on the
        right hand Y axis is not painted in the same colour as the first one
        on the left: the second axes would start the sequence again.
        """
        plot_cfg = self.settings.section("plot")
        target = self.axes_for_side(side)
        color = self._cycle_color(self._color_index)
        self._color_index += 1
        series_st = style or self.plot_style
        self.series_style[y_col] = series_st

        if series_st == "line":
            l_style = code_of(LINE_STYLES, plot_cfg["line_style"], "-")
            if l_style.lower() == "none":
                l_style = "-"
            m_style = "None"
        elif series_st == "scatter":
            l_style = "none"
            m_style = code_of(MARKERS, plot_cfg["marker"], "o")
            if m_style.lower() == "none":
                m_style = "o"
        elif series_st in ("bar", "histogram", "stairs", "hist2d", "pie"):
            l_style = "none"        # the artist beside the curve is the plot
            m_style = "None"
        elif series_st == "errorbar":
            l_style = "none"
            m_style = code_of(MARKERS, plot_cfg["marker"], "o")
            if m_style.lower() == "none":
                m_style = "o"
        else:  # line_symbol
            l_style = code_of(LINE_STYLES, plot_cfg["line_style"], "-")
            if l_style.lower() == "none":
                l_style = "-"
            m_style = code_of(MARKERS, plot_cfg["marker"], "o")
            if m_style.lower() == "none":
                m_style = "o"

        line, = target.plot(
            x, y, color=color,
            linestyle=l_style,
            linewidth=float(plot_cfg["line_width"]),
            marker=m_style,
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
        self.series_axis[y_col] = "right" if target is self.ax2 else "left"
        self.fill_state.setdefault(y_col, self.default_fill_state(plot_cfg))
        self.refresh_series_visuals(y_col)
        return line

    def _clear_bar(self, column):
        old = self.bar_containers.pop(column, None)
        if old is not None:
            try:
                old.remove()
            except Exception:
                for patch in getattr(old, "patches", []):
                    try:
                        patch.remove()
                    except Exception:
                        pass

    def refresh_bar(self, column):
        self._clear_bar(column)
        st = self.series_style.get(column, self.plot_style)
        if st != "bar":
            return None
        line = self.series.get(column)
        if line is None:
            return None
        x_data, y_data = line.get_data()
        if len(x_data) == 0:
            return None
        target = line.axes if line.axes is not None else self.ax
        cfg = self.bar_cfg.setdefault(column, {
            "width": 0.8, "color": safe_hex(line.get_color()), "alpha": 0.85,
            "edgecolor": safe_hex(line.get_color()), "edgewidth": 1.0,
            "hatch": ""
        })
        cfg.setdefault("hatch", "")
        w = float(cfg.get("width", 0.8))
        try:
            x_arr = np.asarray(x_data, dtype=float)
            if len(x_arr) > 1:
                diffs = np.diff(np.sort(x_arr))
                pos_diffs = diffs[diffs > 0]
                if len(pos_diffs) > 0 and w <= 1.0:
                    w = float(cfg.get("width", 0.8)) * float(np.min(pos_diffs))
        except (ValueError, TypeError):
            pass

        container = target.bar(
            x_data, y_data, width=w,
            color=cfg.get("color", line.get_color()),
            edgecolor=cfg.get("edgecolor", safe_hex(line.get_color())),
            linewidth=float(cfg.get("edgewidth", 1.0)),
            alpha=float(cfg.get("alpha", 0.85)),
            hatch=(cfg.get("hatch") or None),
            label="_nolegend_",
            zorder=line.get_zorder() - 0.2
        )
        for patch in container.patches:
            patch.aplot_series = str(column)
            patch.set_picker(True)
        self.bar_containers[column] = container
        return container

    def _clear_errorbar(self, column):
        old = self.errorbar_containers.pop(column, None)
        if old is not None:
            try:
                old.remove()
            except Exception:
                for coll in getattr(old, "lines", []):
                    try:
                        coll.remove()
                    except Exception:
                        pass

    def partner_column(self, column):
        """The column that holds the error bars of one curve.

        In an error bar diagram the pairs are worked out when the curves are
        built (`curve_columns`).  For a single curve that was switched to
        this style by hand, the column standing right after it in the table
        is taken - which is what "the next column" means.
        """
        found = self.error_partner.get(column)
        if found and found in self.df.columns:
            return found
        names = [str(one) for one in self.df.columns]
        text = str(column)
        if text in names:
            index = names.index(text) + 1
            if index < len(names):
                return names[index]
        return None

    def _error_from_column(self, name, y_arr):
        """The error bar lengths read from one column of the table."""
        name = str(name or "")
        if not name or name not in self.df.columns:
            return None
        values = pd.to_numeric(self.df[name], errors="coerce").to_numpy(float)
        values = np.abs(values)
        if len(values) >= len(y_arr):
            return values[:len(y_arr)]
        return np.pad(values, (0, len(y_arr) - len(values)),
                      constant_values=np.nan)

    def refresh_errorbar(self, column):
        self._clear_errorbar(column)
        st = self.series_style.get(column, self.plot_style)
        if st != "errorbar":
            return None
        line = self.series.get(column)
        if line is None:
            return None
        x_data, y_data = line.get_data()
        if len(x_data) == 0:
            return None
        target = line.axes if line.axes is not None else self.ax
        cfg = self.error_cfg.setdefault(column, {
            "type": "pair", "value": 5.0, "column": "",
            "capsize": 4.0, "capthick": 1.5, "elinewidth": 1.5,
            "color": line.get_color()
        })

        err_type = cfg.get("type", "pair")
        err_val = float(cfg.get("value", 5.0))
        y_arr = np.asarray(y_data, dtype=float)

        if err_type == "pair":
            # the column right after this one holds the standard deviation
            yerr = self._error_from_column(self.partner_column(column), y_arr)
            if yerr is None:            # no column left over: fall back to 5 %
                yerr = np.abs(y_arr * 0.05)
        elif err_type == "percent":
            yerr = np.abs(y_arr * (err_val / 100.0))
        elif err_type == "fixed":
            yerr = np.full_like(y_arr, err_val)
        elif err_type == "std":
            finite_y = y_arr[np.isfinite(y_arr)]
            std = float(np.std(finite_y)) if len(finite_y) > 1 else 1.0
            yerr = np.full_like(y_arr, std)
        elif err_type == "column":
            yerr = self._error_from_column(cfg.get("column", ""), y_arr)
            if yerr is None:
                yerr = np.abs(y_arr * 0.05)
        else:
            yerr = np.abs(y_arr * 0.05)

        color = cfg.get("color", line.get_color())
        capsize = float(cfg.get("capsize", 4.0))
        capthick = float(cfg.get("capthick", 1.5))
        elinewidth = float(cfg.get("elinewidth", 1.5))

        container = target.errorbar(
            x_data, y_data, yerr=yerr, fmt='none',
            ecolor=color, elinewidth=elinewidth,
            capsize=capsize, capthick=capthick,
            label="_nolegend_", zorder=line.get_zorder() + 0.1
        )
        for artist in container.get_children():
            artist.aplot_series = str(column)
            artist.set_picker(True)
        self.errorbar_containers[column] = container
        return container

    def _clear_histogram(self, column):
        self._clear_bar(f"hist_{column}")

    @staticmethod
    def _bin_widths(centers):
        """Bar widths that make the bars of a histogram touch each other."""
        centers = np.asarray(centers, dtype=float)
        if len(centers) < 2:
            return np.ones_like(centers)
        order = np.argsort(centers)
        steps = np.diff(centers[order])
        steps = steps[steps > 0]
        step = float(np.min(steps)) if len(steps) else 1.0
        return np.full_like(centers, step)

    # -- a histogram counts the values of one column by itself --------------
    @staticmethod
    def default_histogram_cfg(line=None):
        return {"bins": HISTOGRAM_BINS,
                "color": safe_hex(line.get_color() if line is not None
                                  else PALETTE_FALLBACK, PALETTE_FALLBACK),
                "alpha": 0.85, "edgecolor": "#ffffff", "edgewidth": 1.0,
                "hatch": ""}

    def histogram_bins(self, column):
        """How many bins the sample of one column is counted into."""
        cfg = self.histogram_cfg.get(column) or {}
        try:
            count = int(float(cfg.get("bins", HISTOGRAM_BINS)))
        except (TypeError, ValueError):
            count = HISTOGRAM_BINS
        return max(1, min(count, MAX_HISTOGRAM_BINS))

    @staticmethod
    def sample_values(df, column):
        """The numbers of one column: the sample a histogram counts.

        Empty cells and text are not values, so they are simply left out -
        a histogram has no gaps, it has counts.
        """
        if df is None or str(column) not in [str(one) for one in df.columns]:
            return np.array([], dtype=float)
        values = pd.to_numeric(df[column], errors="coerce").to_numpy(dtype=float)
        return values[np.isfinite(values)]

    def histogram_points(self, df, column):
        """The centre of every bin and how many values fell into it.

        This is the statistics `ax.hist` does: the range the sample covers
        is cut into `bins` equal parts and the values are counted.  One
        column of raw measurements is all a histogram needs, so the first
        column of the table is a sample of its own as well.
        """
        values = self.sample_values(df, column)
        if len(values) == 0:
            self.histogram_edges.pop(column, None)
            return np.array([], dtype=float), np.array([], dtype=float)
        counts, edges = np.histogram(values, bins=self.histogram_bins(column))
        self.histogram_edges[column] = edges
        centers = (edges[:-1] + edges[1:]) / 2.0
        return centers, counts.astype(float)

    # -- one single column: the X axis is the row number --------------------
    @staticmethod
    def has_numbers(df, column):
        """True when that column holds at least one number."""
        return bool(len(PlotWindow.sample_values(df, column)))

    def row_numbers_mode(self, df=None):
        """True while the first column is the only column with numbers.

        One column of values is a series of measurements, not an X axis: it
        becomes the first curve and the **row number** of the table becomes
        the X axis, exactly as the numbers at the left of the spreadsheet
        show them.  A histogram never needs this - it counts every column
        of its own accord.
        """
        if self.plot_style in ("histogram", "pie"):
            return False               # neither of them reads an X axis
        frame = self.df if df is None else df
        if frame is None or not len(frame.columns):
            return False
        columns = [str(one) for one in frame.columns]
        if not self.has_numbers(frame, columns[0]):
            return False
        return not any(self.has_numbers(frame, name) for name in columns[1:])

    @staticmethod
    def row_number_points(df, column):
        """The values of one column against the row numbers of the table.

        The first row is 1, so the X value of a point is the number that
        stands beside it in the spreadsheet.  Empty cells stay gaps.
        """
        values = pd.to_numeric(df[column], errors="coerce").to_numpy(dtype=float)
        return (np.arange(1, len(values) + 1, dtype=float), values)

    def x_axis_name(self):
        """What the X axis carries: the first column, or the row number."""
        if self.row_numbers_mode():
            return ROW_AXIS_LABEL
        return str(self.df.columns[0]) if len(self.df.columns) else ""

    def series_points(self, df, x_col, y_col, style=None):
        """The X/Y pairs one curve is drawn from.

        Every style reads the first column as X and the column itself as Y.
        There are two exceptions: a **histogram** counts the raw values of
        the column itself, so the pairs are its bin centres and counts;
        and a table whose **first column is the only filled one** has no X
        column at all, so that column is drawn against the row numbers.
        """
        style = style or self.series_style.get(y_col, self.plot_style)
        if style == "histogram":
            return self.histogram_points(df, y_col)
        columns = [str(one) for one in df.columns]
        if columns and str(y_col) == columns[0] and self.row_numbers_mode(df):
            return self.row_number_points(df, y_col)
        return self._series_data(df, x_col, y_col)

    def refresh_histogram(self, column):
        """Count the values of `column` again and draw the bars."""
        self._clear_histogram(column)
        st = self.series_style.get(column, self.plot_style)
        line = self.series.get(column)
        if st != "histogram" or line is None:
            return None
        cfg = self.histogram_cfg.setdefault(
            column, self.default_histogram_cfg(line))
        for key, value in self.default_histogram_cfg(line).items():
            cfg.setdefault(key, value)

        # the statistics is made here and now: a changed number of bins,
        # or changed data, is counted again
        centers, counts = self.histogram_points(self.df, column)
        line.set_data(centers, counts)     # the curve behind the bars
        self.histogram_drawn.add(column)
        if not len(centers):
            return None
        edges = self.histogram_edges.get(column)
        widths = (np.diff(np.asarray(edges, dtype=float))
                  if edges is not None and len(edges) > 1
                  else self._bin_widths(centers))
        target = line.axes if line.axes is not None else self.ax

        container = target.bar(
            centers, counts, width=widths, align="center",
            color=cfg.get("color", line.get_color()),
            edgecolor=cfg.get("edgecolor", "#ffffff"),
            linewidth=float(cfg.get("edgewidth", 1.0)),
            alpha=float(cfg.get("alpha", 0.85)),
            hatch=(cfg.get("hatch") or None),
            label="_nolegend_",
            zorder=line.get_zorder() - 0.2
        )
        for patch in container.patches:
            patch.aplot_series = str(column)
            patch.set_picker(True)
        self.bar_containers[f"hist_{column}"] = container
        return container

    def restore_series_data(self, column):
        """Put the values of a column back on its curve after a histogram.

        While a curve is drawn as a histogram it carries the counts of the
        bins, not the data of the table.  Switching that curve to another
        style has to give it its own values against the X column again.
        """
        self.histogram_drawn.discard(column)
        self.histogram_edges.pop(column, None)
        line = self.series.get(column)
        if line is None or str(column) not in [str(one) for one in self.df.columns]:
            return False
        x_name = self.x_col if self.x_col in self.df.columns else \
            str(self.df.columns[0])
        line.set_data(*self._series_data(self.df, x_name, column))
        return True

    # -- a stepped outline: ax.stairs ---------------------------------------
    def _clear_stairs(self, column):
        patch = self.stairs_patches.pop(column, None)
        if patch is not None:
            try:
                patch.remove()
            except (ValueError, AttributeError):
                pass

    @staticmethod
    def default_stairs_cfg(line=None):
        return {"edges": "mid", "width": 1.8, "fill": False, "alpha": 0.35,
                "baseline": False,
                "color": safe_hex(line.get_color() if line is not None
                                  else PALETTE_FALLBACK, PALETTE_FALLBACK),
                "hatch": ""}

    @staticmethod
    def stairs_edges(x_data, mode="mid"):
        """The `N + 1` edges of `N` values: where the steps stand.

        `mid` puts the step halfway between two X values (every value is
        valid around its own X), `post` at the X value itself and `pre`
        just before it.
        """
        x_arr = np.asarray(x_data, dtype=float)
        count = len(x_arr)
        if count == 0:
            return np.array([0.0, 1.0])
        if count == 1:
            return np.array([x_arr[0] - 0.5, x_arr[0] + 0.5])
        first_step = x_arr[1] - x_arr[0] or 1.0
        last_step = x_arr[-1] - x_arr[-2] or 1.0
        if str(mode) == "post":
            return np.concatenate([x_arr, [x_arr[-1] + last_step]])
        if str(mode) == "pre":
            return np.concatenate([[x_arr[0] - first_step], x_arr])
        middles = (x_arr[:-1] + x_arr[1:]) / 2.0
        return np.concatenate([[x_arr[0] - first_step / 2.0], middles,
                               [x_arr[-1] + last_step / 2.0]])

    def refresh_stairs(self, column):
        """Draw the values of one column as a staircase."""
        self._clear_stairs(column)
        st = self.series_style.get(column, self.plot_style)
        line = self.series.get(column)
        if st != "stairs" or line is None:
            return None
        cfg = self.stairs_cfg.setdefault(column,
                                         self.default_stairs_cfg(line))
        for key, value in self.default_stairs_cfg(line).items():
            cfg.setdefault(key, value)
        y_arr = np.asarray(line.get_ydata(), dtype=float)
        if not len(y_arr) or not bool(np.isfinite(y_arr).any()):
            return None
        edges = self.stairs_edges(line.get_xdata(), cfg.get("edges", "mid"))
        target = line.axes if line.axes is not None else self.ax
        filled = bool(cfg.get("fill"))
        # a filled staircase needs a floor to stand on; an open one is a
        # line and may hang in the air
        baseline = 0.0 if (filled or cfg.get("baseline")) else None
        patch = target.stairs(
            np.nan_to_num(y_arr, nan=0.0), edges, baseline=baseline,
            fill=filled, color=cfg.get("color", line.get_color()),
            linewidth=float(cfg.get("width", 1.8)),
            alpha=(float(cfg.get("alpha", 0.35)) if filled else None),
            hatch=(cfg.get("hatch") or None),
            label="_nolegend_", zorder=line.get_zorder())
        if filled:
            # a crisp outline over a see-through face, as a filled area does
            colour = cfg.get("color", line.get_color())
            patch.set_alpha(None)
            patch.set_facecolor(to_rgba(colour, float(cfg.get("alpha", 0.35))))
            patch.set_edgecolor(colour)
        patch.aplot_series = str(column)
        patch.set_picker(True)
        self.stairs_patches[column] = patch
        return patch

    # -- the X/Y pairs counted in a grid: ax.hist2d -------------------------
    def _clear_hist2d(self, column):
        bar = self.hist2d_bars.pop(column, None)
        if bar is not None:
            try:
                bar.remove()               # the colour bar and its own axes
            except (ValueError, AttributeError, KeyError):
                pass
        mesh = self.hist2d_meshes.pop(column, None)
        if mesh is not None:
            try:
                mesh.remove()
            except (ValueError, AttributeError):
                pass

    @staticmethod
    def default_hist2d_cfg(_line=None):
        return {"xbins": HIST2D_BINS, "ybins": HIST2D_BINS, "cmap": "viridis",
                "alpha": 1.0, "colorbar": False, "hide_empty": True}

    def hist2d_bins(self, column, which="xbins"):
        cfg = self.hist2d_cfg.get(column) or {}
        try:
            count = int(float(cfg.get(which, HIST2D_BINS)))
        except (TypeError, ValueError):
            count = HIST2D_BINS
        return max(1, min(count, MAX_HIST2D_BINS))

    def hist2d_pairs(self, column):
        """The X/Y pairs of one curve, without the gaps."""
        line = self.series.get(column)
        if line is None:
            return np.array([], dtype=float), np.array([], dtype=float)
        x_arr = np.asarray(line.get_xdata(), dtype=float)
        y_arr = np.asarray(line.get_ydata(), dtype=float)
        good = np.isfinite(x_arr) & np.isfinite(y_arr)
        return x_arr[good], y_arr[good]

    def refresh_hist2d(self, column):
        """Count the X/Y pairs of one curve into a grid of cells."""
        self._clear_hist2d(column)
        st = self.series_style.get(column, self.plot_style)
        line = self.series.get(column)
        if st != "hist2d" or line is None:
            return None
        cfg = self.hist2d_cfg.setdefault(column, self.default_hist2d_cfg(line))
        for key, value in self.default_hist2d_cfg(line).items():
            cfg.setdefault(key, value)
        x_arr, y_arr = self.hist2d_pairs(column)
        if len(x_arr) < 2:
            return None
        target = line.axes if line.axes is not None else self.ax
        bins = [self.hist2d_bins(column, "xbins"),
                self.hist2d_bins(column, "ybins")]
        try:
            _counts, _xe, _ye, mesh = target.hist2d(
                x_arr, y_arr, bins=bins, cmap=str(cfg.get("cmap", "viridis")),
                alpha=float(cfg.get("alpha", 1.0)),
                cmin=(1 if cfg.get("hide_empty", True) else None),
                zorder=line.get_zorder() - 0.3)
        except (ValueError, TypeError):
            return None
        mesh.aplot_series = str(column)
        mesh.set_picker(True)
        mesh.set_label("_nolegend_")
        self.hist2d_meshes[column] = mesh
        if cfg.get("colorbar"):
            self._add_color_bar(column, mesh, target)
        return mesh

    def _add_color_bar(self, column, mesh, target):
        """A colour scale beside the plot area, in axes of its own.

        It is an inset of the plot area, so it follows it wherever the
        frame is dragged and never takes room away from the diagram.
        """
        try:
            cax = target.inset_axes([1.02, 0.0, 0.035, 1.0])
            bar = self.fig.colorbar(mesh, cax=cax)
            bar.outline.set_linewidth(float(self.frame_cfg.get("width", 1.0)))
            size = int(self.axis_cfg["y"].get("tick_size", 12))
            cax.tick_params(labelsize=size)
            for artist in (cax, bar.outline):
                artist.set_in_layout(True)
            self.hist2d_bars[column] = bar
            return bar
        except (ValueError, TypeError, AttributeError):
            return None

    # -- the values of one column as slices: ax.pie -------------------------
    def _clear_pie(self, column):
        for artist in (list(self.pie_wedges.pop(column, ()) or ())
                       + list(self.pie_texts.pop(column, ()) or ())):
            try:
                artist.remove()
            except (ValueError, AttributeError):
                pass

    @staticmethod
    def default_pie_cfg(_line=None):
        return {"start": PIE_START_ANGLE, "percent": True, "decimals": 1,
                "hole": 0.0, "labels": "column", "cmap": "tab10",
                "edgecolor": "#ffffff", "edgewidth": 1.0, "explode": 0.0,
                "clockwise": True, "label_size": 11}

    def pie_values(self, column):
        """The slices of a pie: the numbers of one column and their names."""
        names = [str(one) for one in self.df.columns]
        if str(column) not in names:
            return np.array([], dtype=float), []
        raw = pd.to_numeric(self.df[column], errors="coerce").to_numpy(float)
        good = np.isfinite(raw) & (np.abs(raw) > 0)
        values = np.abs(raw[good])              # a slice has no sign
        cfg = self.pie_cfg.get(column) or {}
        wanted = str(cfg.get("labels", "column"))
        rows = np.nonzero(good)[0]
        if wanted == "none":
            return values, []
        if wanted == "row" or names[0] == str(column):
            return values, [str(int(one) + 1) for one in rows]
        source = self.df[names[0]]
        return values, [("" if pd.isna(source.iat[int(one)])
                         else str(source.iat[int(one)])) for one in rows]

    def refresh_pie(self, column):
        """Draw one column as a pie: one slice per row."""
        self._clear_pie(column)
        st = self.series_style.get(column, self.plot_style)
        line = self.series.get(column)
        if st != "pie" or line is None:
            return None
        cfg = self.pie_cfg.setdefault(column, self.default_pie_cfg(line))
        for key, value in self.default_pie_cfg(line).items():
            cfg.setdefault(key, value)
        values, labels = self.pie_values(column)
        if not len(values):
            return None
        target = line.axes if line.axes is not None else self.ax
        colors = self.slice_colors(cfg.get("cmap", "tab10"), len(values))
        explode = float(cfg.get("explode", 0.0) or 0.0)
        hole = max(0.0, min(float(cfg.get("hole", 0.0) or 0.0), 0.95))
        percent = None
        if cfg.get("percent"):
            percent = f"%.{max(0, int(cfg.get('decimals', 1)))}f%%"
        try:
            wedges, texts, *rest = target.pie(
                values, labels=(labels or None), colors=colors,
                startangle=float(cfg.get("start", PIE_START_ANGLE)),
                counterclock=bool(cfg.get("clockwise", True)),
                autopct=percent,
                explode=([explode] + [0.0] * (len(values) - 1)
                         if explode else None),
                textprops={"fontsize": int(cfg.get("label_size", 11))},
                wedgeprops={"width": (1.0 - hole) if hole else None,
                            "edgecolor": cfg.get("edgecolor", "#ffffff"),
                            "linewidth": float(cfg.get("edgewidth", 1.0))})
        except (ValueError, TypeError):
            return None
        written = list(texts) + list(rest[0] if rest else [])
        for wedge in wedges:
            wedge.aplot_series = str(column)
            wedge.set_picker(True)
        self.pie_wedges[column] = list(wedges)
        self.pie_texts[column] = written
        target.set_aspect("equal")
        return wedges

    @staticmethod
    def slice_colors(name, count):
        """`count` colours taken from a colour map, for the pie slices."""
        try:
            cmap = matplotlib.colormaps[str(name)]
        except (KeyError, AttributeError, TypeError):
            cmap = matplotlib.colormaps["tab10"]
        if getattr(cmap, "N", 256) <= 32:        # a table of distinct colours
            return [cmap(index % cmap.N) for index in range(max(1, count))]
        if count <= 1:
            return [cmap(0.5)]
        return [cmap(index / (count - 1)) for index in range(count)]

    # -- what every style draws beside (or instead of) its curve -----------
    # the styles that draw an artist of their own next to the curve
    EXTRA_ARTISTS = ("bar", "errorbar", "histogram", "stairs", "hist2d", "pie")
    # ... and those whose curve is not drawn at all: that artist is the plot
    CARRIER_ONLY = ("bar", "histogram", "stairs", "hist2d", "pie")

    def clear_extras(self, column, keep=None):
        """Remove what every other style drew beside this curve."""
        for style in self.EXTRA_ARTISTS:
            if style != keep:
                getattr(self, f"_clear_{style}")(column)

    def refresh_series_visuals(self, column):
        """Draw one curve the way its own plot style says.

        Every style has exactly one place here: what the other styles drew
        beside the curve is removed, the curve itself is given the line and
        the marker its style allows, and the artist of the style (bars,
        error bars, a staircase, a grid of counts, slices) is drawn.
        """
        st = self.series_style.get(column, self.plot_style)
        line = self.series.get(column)
        if line is not None:
            if st != "histogram" and column in self.histogram_drawn:
                self.restore_series_data(column)
            self.clear_extras(column, keep=st)
            if st in self.CARRIER_ONLY:
                # the curve itself is not drawn: the artist beside it is
                line.set_linestyle("none")
                line.set_marker("None")
            elif st == "line":
                line.set_marker("None")     # this style has no marker at all
            elif st == "scatter":
                line.set_linestyle("none")  # ... and this one no line
            # line_symbol and errorbar: the Line and the Marker check button
            # of the curve dialog decide, so nothing is put back here - or
            # those two switches (and a saved diagram) would lose what the
            # user chose.  A new curve gets its line and marker from
            # _create_line, and changing the style from _on_style_changed.
            if st in self.EXTRA_ARTISTS:
                getattr(self, f"refresh_{st}")(column)
        self.refresh_fill(column)

    # -- filled area under a curve -----------------------------------------
    @staticmethod
    def default_fill_state(plot_cfg):
        return {
            "on": bool(plot_cfg.get("fill_under", False)),
            "follow": bool(plot_cfg.get("fill_follows_line", True)),
            "color": safe_hex(plot_cfg.get("fill_color"), PALETTE_FALLBACK),
            "alpha": float(plot_cfg.get("fill_alpha", 0.35)),
            "hatch": code_of(HATCH_PATTERNS, plot_cfg.get("fill_pattern"), ""),
            "base": code_of(FILL_BASES, plot_cfg.get("fill_base"), "bottom"),
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
        ax = line.axes if line.axes is not None else self.ax
        base = 0.0 if cfg.get("base", "zero") == "zero" else ax.get_ylim()[0]
        # the filled area is only a picture of the curve: it must not grow
        # the data limits, or a fill reaching the bottom of the axes would
        # push that bottom further down at every redraw
        limits = ax.dataLim.get_points().copy()
        ignoring = getattr(ax, "ignore_existing_data_limits", False)
        fill = ax.fill_between(
            x_data, y_data, base,
            facecolor=to_rgba(color, alpha),
            edgecolor=to_rgba(color, 1.0) if hatch else "none",
            hatch=hatch, linewidth=0.0, label="_nolegend_",
            zorder=line.get_zorder() - 0.5)
        # fill_between() asks the axes to grow its limits around the new
        # polygon, and matplotlib does that lazily - so putting dataLim back
        # is not enough on its own.  Hanging the very same collection back
        # with autolim=False takes it out of the calculation for good.
        try:
            fill.remove()
            ax.add_collection(fill, autolim=False)
        except (AttributeError, ValueError):
            pass
        try:
            ax.dataLim.set_points(limits)
            ax.ignore_existing_data_limits = ignoring
        except (AttributeError, ValueError):
            pass
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
            if getattr(self, "_auto_x_label", None) == old:
                self._auto_x_label = str(new)
            self.x_col = new
            if old not in self.series:
                self.draw()          # that column is only an X axis
                return
            # a histogram, or a single filled column, draws it as a curve
            # as well: it has to be renamed like any other curve
        line = self.series.get(old)
        if line is None:
            return
        # rebuild dictionaries so that the column order is kept
        self.series = {(new if key == old else key): value
                       for key, value in self.series.items()}
        self.series_axis = {(new if key == old else key): value
                            for key, value in self.series_axis.items()}
        self.legend_state = {(new if key == old else key): value
                             for key, value in self.legend_state.items()}
        self.fill_state = {(new if key == old else key): value
                           for key, value in self.fill_state.items()}
        self.fills = {(new if key == old else key): value
                      for key, value in self.fills.items()}
        if old in self.series_style:
            self.series_style[new] = self.series_style.pop(old)
        if old in self.bar_cfg:
            self.bar_cfg[new] = self.bar_cfg.pop(old)
        if old in self.error_cfg:
            self.error_cfg[new] = self.error_cfg.pop(old)
        for store in (self.histogram_cfg, self.stairs_cfg,
                      self.hist2d_cfg, self.pie_cfg, self.stairs_patches,
                      self.hist2d_meshes, self.hist2d_bars,
                      self.pie_wedges, self.pie_texts):
            if old in store:
                store[new] = store.pop(old)
        if old in self.bar_containers:
            self.bar_containers[new] = self.bar_containers.pop(old)
        if f"hist_{old}" in self.bar_containers:
            self.bar_containers[f"hist_{new}"] = \
                self.bar_containers.pop(f"hist_{old}")
        if old in self.histogram_edges:
            self.histogram_edges[new] = self.histogram_edges.pop(old)
        if old in self.histogram_drawn:
            self.histogram_drawn.discard(old)
            self.histogram_drawn.add(new)
        if old in self.errorbar_containers:
            self.errorbar_containers[new] = self.errorbar_containers.pop(old)
        if line.get_label() == getattr(line, "aplot_series", None):
            line.set_label(str(new))
        line.aplot_series = str(new)
        self.refresh_legend()
        self.draw()

    def curve_columns(self, columns):
        """Which columns become curves, and where their error bars come from.

        Every diagram reads the **first** column as the X axis and the
        second one as the values of the first curve.  An **error bar**
        diagram reads the columns in pairs after that: `x`, mean, std,
        mean, std, ... - so the third column is the length of the error bar
        of the second one, the fifth belongs to the fourth, and so on.  In
        every other kind of diagram each column after the first one is a
        curve of its own.

        A **histogram** is the exception: it counts the values of a column
        by itself and needs nothing else, so *every* column - the first one
        included - is a sample and a curve of its own.

        A table whose **first column is the only filled one** is the other
        exception: there is no X column to read, so that column is the one
        and only curve and the X axis becomes the row number.
        """
        columns = [str(one) for one in columns]
        if self.plot_style == "histogram":
            return columns, {}
        if self.plot_style == "pie":
            # one pie fills the whole plot area, so exactly one column is
            # drawn: the first one that holds numbers.  The first column of
            # the table names the slices, unless it is the only one there is.
            candidates = columns[1:] or columns[:1]
            for name in candidates:
                if self.has_numbers(self.df, name):
                    return [name], {}
            return candidates[:1], {}
        if self.row_numbers_mode():
            return columns[:1], {}
        if len(columns) < 2:
            return [], {}
        rest = columns[1:]
        if self.plot_style != "errorbar":
            return rest, {}
        curves, partner = [], {}
        for index in range(0, len(rest), 2):
            mean = rest[index]
            curves.append(mean)
            if index + 1 < len(rest):
                partner[mean] = rest[index + 1]
        return curves, partner

    def _plot_data(self, _plot_cfg=None):
        columns = list(self.df.columns)
        if not columns:
            return 0
        x_col = columns[0]
        sides = self.layout.get("y", {})
        curves, partner = self.curve_columns(columns)
        self.error_partner = dict(partner)
        for y_col in curves:
            x, y = self.series_points(self.df, x_col, y_col,
                                      style=self.plot_style)
            if len(x) and bool(np.isfinite(y).any()):
                self._create_line(x, y, y_col, x_col,
                                  sides.get(str(y_col), "left"),
                                  style=self.plot_style)
        return len(self.lines)

    def remove_series(self, column):
        """Take one curve out of the diagram with everything that belongs to it."""
        line = self.series.pop(column, None)
        if line is None:
            return False
        if line in self.lines:
            self.lines.remove(line)
        dialog = self._dialogs.pop(id(line), None)
        if dialog is not None and dialog.winfo_exists():
            dialog.destroy()
        self.clear_extras(column)
        self.series_style.pop(column, None)
        self.bar_cfg.pop(column, None)
        self.error_cfg.pop(column, None)
        self.histogram_cfg.pop(column, None)
        self.stairs_cfg.pop(column, None)
        self.hist2d_cfg.pop(column, None)
        self.pie_cfg.pop(column, None)
        self.histogram_edges.pop(column, None)
        self.histogram_drawn.discard(column)
        fill = self.fills.pop(column, None)
        if fill is not None:
            fill.remove()
        self.fill_state.pop(column, None)
        legend = self.legends.pop(column, None)
        if legend is not None:
            legend.remove()
        self.legend_state.pop(column, None)
        self.series_axis.pop(column, None)
        line.remove()
        return True

    def update_data(self, df, layout=None):
        """Replace the plotted values but keep every style setting.

        Curves are matched by column name: existing ones only get new data,
        a new column becomes a new curve, a deleted column disappears.  The
        layout says which axis every column belongs to now, so moving a tick
        from `y_L` to `y_R` in the table moves that curve to the other side.
        """
        columns = list(df.columns)
        # one column on its own is enough: a histogram counts it, and every
        # other diagram draws it against the row numbers
        if not columns:
            return False
        self.df = df
        x_col = columns[0]
        self.x_col = x_col
        if layout is not None:
            self.layout = self._clean_layout(df, layout)
            self.x_side = self.layout["x_side"]
        sides = self.layout.get("y", {})
        curves, partner = self.curve_columns(columns)
        self.error_partner = dict(partner)

        for y_col in curves:
            x, y = self.series_points(df, x_col, y_col)
            side = sides.get(str(y_col), self.series_side(y_col))
            line = self.series.get(y_col)
            if line is None:
                # an empty column gets no curve (and no legend box) yet -
                # it becomes one as soon as a value is typed into it
                if len(x) and bool(np.isfinite(y).any()):
                    self._create_line(x, y, y_col, x_col, side)
            else:
                line.set_data(x, y)
                self.move_series(y_col, side)
                self.refresh_series_visuals(y_col)

        for y_col in [name for name in self.series if name not in curves]:
            self.remove_series(y_col)

        # the curves follow the order of the columns, so a column that is
        # ticked again comes back in its own place and not at the end
        order = [name for name in curves if name in self.series]
        self.series = {name: self.series[name] for name in order}
        self.series_axis = {name: self.series_axis[name] for name in order
                            if name in self.series_axis}

        self._refresh_x_label()  # a second filled column ends the row numbers
        self._rescale()          # manual ranges are left untouched
        self.apply_frame(self.frame_cfg, redraw=False)
        self.refresh_fills()
        self.refresh_legend()
        self.draw()
        return True

    def _refresh_x_label(self):
        """Follow what the X axis carries, as long as it was never renamed.

        The name of the first column and the word "Row" swap places when a
        second column is filled (or emptied).  A label the user has written
        himself is never touched.
        """
        wanted = self.x_axis_name()
        remembered = getattr(self, "_auto_x_label", wanted)
        if wanted == remembered:
            return False
        automatic = str(self.axis_label("x")) == remembered
        self._auto_x_label = wanted
        if not automatic:
            return False            # it carries a text of its own now
        self.apply_axis("x", {**self.axis_cfg["x"], "label": wanted},
                        redraw=False)
        return True

    # -- the diagram as a matplotlib program -------------------------------
    @staticmethod
    def _literal(value):
        """One value as Python source."""
        if isinstance(value, (np.floating, float)):
            value = float(value)
            return repr(round(value, 6))
        if isinstance(value, (np.integer, int)) and not isinstance(value, bool):
            return repr(int(value))
        if isinstance(value, (list, tuple)):
            return "[" + ", ".join(PlotWindow._literal(one) for one in value) + "]"
        if isinstance(value, np.ndarray):
            return PlotWindow._literal([float(one) for one in value])
        return repr(value)

    def _script_data(self):
        """The plotted columns as plain Python lists."""
        lines = ["DATA = {"]
        columns = []
        for name in [self.x_col] + list(self.series):
            if name not in columns:     # a histogram counts the X column too
                columns.append(name)
        for mean, std in self.error_partner.items():      # the error columns
            if std not in columns:
                columns.append(std)
        for cfg in self.error_cfg.values():
            name = str(cfg.get("column", ""))
            if name and name not in columns:
                columns.append(name)
        for name in columns:
            if name not in self.df.columns:
                continue
            values = pd.to_numeric(self.df[name], errors="coerce").to_numpy(float)
            numbers = ", ".join("float('nan')" if not np.isfinite(one)
                                else repr(round(float(one), 10))
                                for one in values)
            lines.append(f"    {name!r}: [{numbers}],")
        lines.append("}")
        if self.row_numbers_mode() and columns:
            # the only filled column is drawn against the row numbers
            lines.append("")
            lines.append("# the X values: the row numbers of the table")
            lines.append("ROWS = np.arange(1, len(DATA[%r]) + 1, dtype=float)"
                         % str(columns[0]))
        return lines

    def to_script(self):
        """A stand-alone matplotlib program that draws this very diagram."""
        lit = self._literal
        cfg = self.frame_cfg
        dpi = float(self.fig.get_dpi())
        out = [
            '"""Diagram exported from ' + APP_NAME + '.',
            "",
            "Run it with:   python3 this_file.py",
            "It needs numpy and matplotlib and nothing else - the data is",
            "written into the file, so it runs anywhere.",
            '"""',
            "import numpy as np",
            "import matplotlib.pyplot as plt",
            "from matplotlib.legend import Legend",
            "from matplotlib.patches import Ellipse, Polygon, Rectangle",
            "from matplotlib.ticker import (AutoMinorLocator, MultipleLocator,",
            "                               NullLocator)",
            "from matplotlib.transforms import Affine2D",
            "",
        ]
        out += self._script_data()
        out += [
            "",
            f"DPI = {lit(dpi)}",
            "PT = 72.0 / DPI          # the distances are given in pixels",
            "",
            "",
            "def turned(ax, centre, angle):",
            '    """The plot area, turned by `angle` degrees around a point."""',
            "    if not angle:",
            "        return ax.transAxes",
            "    px, py = ax.transAxes.transform(centre)",
            "    return ax.transAxes + Affine2D().rotate_deg_around(",
            "        float(px), float(py), float(angle))",
            "",
            "",
            "fig = plt.figure(figsize=("
            f"{lit(float(self.fig.get_figwidth()))}, "
            f"{lit(float(self.fig.get_figheight()))}), dpi=DPI)",
        ]
        figure_bg = cfg.get("figure_background", "#ffffff")
        out.append("fig.set_facecolor(%s)" % lit("none" if figure_bg == "none"
                                                 else figure_bg))
        out += [
            "ax = fig.add_subplot(111)",
            "ax.set_position([%s, %s, %s, %s])" % (
                lit(cfg["left"]), lit(cfg["bottom"]),
                lit(cfg["x_length"]), lit(cfg["y_length"])),
            "ax.set_facecolor(%s)" % lit(cfg.get("background", "#ffffff")),
        ]
        out += self._script_axes()
        out += self._script_curves()
        out += self._script_texts()
        out += self._script_objects()
        out += [
            "",
            "# fig.savefig(\"diagram.png\", dpi=300, bbox_inches=\"tight\")",
            "plt.show()",
            "",
        ]
        return "\n".join(out)

    def _script_axes(self):
        """Frame, ticks, ranges, grid - for every axis that is in use."""
        lit = self._literal
        cfg = self.frame_cfg
        style = cfg.get("style", "none")
        both = style in ("box_in", "box_out")
        top = self.x_side == "top"
        right = self.right_axis_active()
        left = self.left_axis_shown()
        used = self.used_sides()
        out = ["", "# ---------------------------------------------- the frame"]
        for name in ("left", "right", "top", "bottom"):
            visible = style != "none" or name in used
            out.append("ax.spines[%s].set_visible(%s)" % (lit(name), visible))
            if visible:
                out.append("ax.spines[%s].set_linewidth(%s)"
                           % (lit(name), lit(cfg["width"])))
                out.append("ax.spines[%s].set_color(%s)"
                           % (lit(name), lit(self.axis_color(
                               self.spine_owner(name)))))
        out.append("ax.tick_params(which='both', width=%s, direction=%s)"
                   % (lit(cfg["width"]),
                      lit("in" if style == "box_in" else "out")))
        out.append("ax.tick_params(which='major', length=%s)"
                   % lit(cfg["major_tick_length"]))
        out.append("ax.tick_params(which='minor', length=%s)"
                   % lit(cfg["minor_tick_length"]))

        for which in ("x", "y", "y2"):
            if which == "y2" and not right:
                continue
            axis_cfg = self.axis_cfg[which]
            name = {"x": "ax", "y": "ax", "y2": "ax2"}[which]
            if which == "y2":
                out += ["", "ax2 = ax.twinx()", "ax2.patch.set_visible(False)",
                        "for spine in ax2.spines.values():",
                        "    spine.set_visible(False)",
                        "ax2.tick_params(which='both', width=%s, direction=%s)"
                        % (lit(cfg["width"]),
                           lit("in" if style == "box_in" else "out")),
                        "ax2.tick_params(which='major', length=%s)"
                        % lit(cfg["major_tick_length"]),
                        "ax2.tick_params(which='minor', length=%s)"
                        % lit(cfg["minor_tick_length"])]
            out.append("")
            out.append(f"# ---------------------------------- the "
                       f"{AXIS_NAMES.get(which, which)}")
            setter = {"x": "set_xlabel", "y": "set_ylabel",
                      "y2": "set_ylabel"}[which]
            out.append("%s.%s(%s, fontsize=%s, color=%s, labelpad=%s * PT)"
                       % (name, setter, lit(self.axis_label(which)),
                          lit(axis_cfg["label_size"]),
                          lit(axis_cfg["label_color"]),
                          lit(axis_cfg["label_pad"])))
            if not axis_cfg.get("label_on", True):
                out.append("%s.%saxis.label.set_visible(False)"
                           % (name, "x" if which == "x" else "y"))
            axis_name = "x" if which == "x" else "y"
            ticks_on = bool(axis_cfg.get("ticks_on", True))
            out.append("%s.tick_params(axis=%s, which='both', labelsize=%s, "
                       "labelcolor=%s, pad=%s * PT, color=%s)"
                       % (name, lit(axis_name), lit(axis_cfg["tick_size"]),
                          lit(axis_cfg["tick_color"]), lit(axis_cfg["tick_pad"]),
                          lit(self.axis_color(which))))
            if which == "x":
                out.append("ax.xaxis.set_ticks_position(%s)"
                           % lit("top" if top else "bottom"))
                out.append("ax.xaxis.set_label_position(%s)"
                           % lit("top" if top else "bottom"))
                out.append("ax.tick_params(axis='x', which='both', top=%s, "
                           "bottom=%s, labeltop=%s, labelbottom=%s)"
                           % ((both or top) and ticks_on,
                              (both or not top) and ticks_on,
                              top and ticks_on, (not top) and ticks_on))
            elif which == "y":
                out.append("ax.yaxis.set_visible(%s)" % left)
                out.append("ax.tick_params(axis='y', which='both', left=%s, "
                           "right=%s, labelleft=%s, labelright=False)"
                           % ((left or both) and ticks_on,
                              (both and not right) and ticks_on,
                              left and ticks_on))
            else:
                out.append("ax2.yaxis.set_ticks_position('right')")
                out.append("ax2.yaxis.set_label_position('right')")
                out.append("ax2.tick_params(axis='y', which='both', left=False, "
                           "right=%s, labelleft=False, labelright=%s)"
                           % (ticks_on, ticks_on))
            low, high = self.current_limits(which)
            out.append("%s.set_%slim(%s, %s)"
                       % (name, axis_name, lit(float(low)), lit(float(high))))
            step = axis_cfg.get("step")
            if not axis_cfg.get("auto", True) and step:
                out.append("%s.%saxis.set_major_locator(MultipleLocator(%s))"
                           % (name, axis_name, lit(float(step))))
            minor = int(axis_cfg.get("minor", 0) or 0)
            out.append("%s.%saxis.set_minor_locator(%s)"
                       % (name, axis_name,
                          f"AutoMinorLocator({minor + 1})" if minor
                          else "NullLocator()"))
            grid = axis_cfg["grid"]
            owner = (which == "x") or (which == ("y" if left else "y2"))
            for kind, on, factor in (("major", grid["major"], 1.0),
                                     ("minor", grid["minor"] and minor, 0.6)):
                if owner and on:
                    out.append("%s.grid(True, which=%s, axis=%s, color=%s, "
                               "linestyle=%s, linewidth=%s)"
                               % (name, lit(kind), lit(axis_name),
                                  lit(grid["color"]), lit(grid["style"]),
                                  lit(max(0.3, grid["width"] * factor))))
                else:
                    out.append("%s.grid(False, which=%s, axis=%s)"
                               % (name, lit(kind), lit(axis_name)))
        return out

    def _script_curves(self):
        """The curves, their filled areas and their legend boxes."""
        lit = self._literal
        out = ["", "# ---------------------------------------------- the curves",
               "curves = {}"]
        # with only the first column filled the X values are the row numbers
        x_data = ("ROWS" if self.row_numbers_mode()
                  else f"DATA[{lit(str(self.x_col))}]")
        for number, (column, line) in enumerate(self.series.items(), start=1):
            target = "ax2" if self.series_side(column) == "right" else "ax"
            st = self.series_style.get(column, self.plot_style)
            # a column name may be anything at all, so the helper variables
            # are numbered instead of being named after it
            tag = f"s{number}"
            if st == "bar":
                b_cfg = self.bar_cfg.get(column, {})
                bw = float(b_cfg.get("width", 0.8))
                ba = float(b_cfg.get("alpha", 0.85))
                bc = store_color(b_cfg.get("color", line.get_color()))
                bec = store_color(b_cfg.get("edgecolor", line.get_color()))
                bew = float(b_cfg.get("edgewidth", 1.0))
                out.append(
                    f"bars_{tag} = {target}.bar({x_data}, "
                    f"DATA[{lit(str(column))}], "
                    f"width={bw}, color={lit(bc)}, edgecolor={lit(bec)}, "
                    f"linewidth={bew}, alpha={ba}, "
                    f"label={lit(str(line.get_label()))})"
                )
                out.append(f"curves[{lit(str(column))}] = bars_{tag}[0]")
            elif st == "errorbar":
                e_cfg = self.error_cfg.get(column, {})
                err_type = e_cfg.get("type", "percent")
                err_val = float(e_cfg.get("value", 5.0))
                capsize = float(e_cfg.get("capsize", 4.0))
                capthick = float(e_cfg.get("capthick", 1.5))
                elinewidth = float(e_cfg.get("elinewidth", 1.5))
                ec = store_color(e_cfg.get("color", line.get_color()))
                values = f"np.asarray(DATA[{lit(str(column))}], float)"
                partner = self.partner_column(column)
                if err_type == "pair" and partner in self.df.columns:
                    # the column beside this one holds the standard deviation
                    out.append(f"yerr_{tag} = np.abs(np.asarray("
                               f"DATA[{lit(str(partner))}], float))")
                elif err_type == "fixed":
                    out.append(f"yerr_{tag} = np.full_like({values}, {err_val})")
                elif err_type == "std":
                    out.append(f"yerr_{tag} = np.full_like({values}, "
                               f"np.nanstd({values}))")
                elif err_type == "column" and e_cfg.get("column") in self.df.columns:
                    out.append(f"yerr_{tag} = np.abs(np.asarray("
                               f"DATA[{lit(str(e_cfg['column']))}], float))")
                elif err_type == "percent":
                    out.append(f"yerr_{tag} = np.abs({values} * "
                               f"{err_val / 100.0})")
                else:
                    out.append(f"yerr_{tag} = np.abs({values} * 0.05)")
                out.append(
                    f"bars_{tag} = {target}.errorbar("
                    f"{x_data}, DATA[{lit(str(column))}], "
                    f"yerr=yerr_{tag}, "
                    f"color={lit(ec)}, fmt={lit(str(line.get_marker()))}, "
                    f"markersize={float(line.get_markersize())}, "
                    f"capsize={capsize}, capthick={capthick}, "
                    f"elinewidth={elinewidth}, "
                    f"label={lit(str(line.get_label()))})"
                )
                out.append(f"curves[{lit(str(column))}] = bars_{tag}")
            elif st == "stairs":
                s_cfg = self.stairs_cfg.get(column, {})
                s_filled = bool(s_cfg.get("fill"))
                s_color = store_color(s_cfg.get("color", line.get_color()))
                s_base = (0.0 if (s_filled or s_cfg.get("baseline")) else None)
                edges = self.stairs_edges(line.get_xdata(),
                                          s_cfg.get("edges", "mid"))
                out.append(f"edges_{tag} = {lit(edges)}")
                out.append(
                    f"bars_{tag} = {target}.stairs(np.nan_to_num("
                    f"np.asarray(DATA[{lit(str(column))}], float), nan=0.0), "
                    f"edges_{tag}, baseline={lit(s_base)}, fill={s_filled}, "
                    f"color={lit(s_color)}, "
                    f"linewidth={float(s_cfg.get('width', 1.8))}, "
                    f"hatch={lit(s_cfg.get('hatch') or None)}, "
                    f"label={lit(str(line.get_label()))})"
                )
                if s_filled:
                    face = list(to_rgba(s_color,
                                        float(s_cfg.get("alpha", 0.35))))
                    out.append(f"bars_{tag}.set_alpha(None)")
                    out.append(f"bars_{tag}.set_facecolor({lit(face)})")
                    out.append(f"bars_{tag}.set_edgecolor({lit(s_color)})")
                out.append(f"curves[{lit(str(column))}] = bars_{tag}")
            elif st == "hist2d":
                g_cfg = self.hist2d_cfg.get(column, {})
                out.append(f"gx_{tag} = np.asarray({x_data}, float)")
                out.append(f"gy_{tag} = np.asarray("
                           f"DATA[{lit(str(column))}], float)")
                out.append(f"ok_{tag} = np.isfinite(gx_{tag}) "
                           f"& np.isfinite(gy_{tag})")
                out.append(
                    f"_counts, _xe, _ye, mesh_{tag} = {target}.hist2d("
                    f"gx_{tag}[ok_{tag}], gy_{tag}[ok_{tag}], "
                    f"bins=[{self.hist2d_bins(column, 'xbins')}, "
                    f"{self.hist2d_bins(column, 'ybins')}], "
                    f"cmap={lit(str(g_cfg.get('cmap', 'viridis')))}, "
                    f"alpha={float(g_cfg.get('alpha', 1.0))}, "
                    f"cmin={lit(1 if g_cfg.get('hide_empty', True) else None)})"
                )
                out.append(f"curves[{lit(str(column))}] = mesh_{tag}")
                if g_cfg.get("colorbar"):
                    out.append(f"cax_{tag} = {target}.inset_axes("
                               f"[1.02, 0.0, 0.035, 1.0])")
                    out.append(f"fig.colorbar(mesh_{tag}, cax=cax_{tag})")
            elif st == "pie":
                p_cfg = self.pie_cfg.get(column, {})
                values, labels = self.pie_values(column)
                colors = [list(to_rgba(one)) for one in
                          self.slice_colors(p_cfg.get("cmap", "tab10"),
                                            len(values))]
                hole = max(0.0, min(float(p_cfg.get("hole", 0.0) or 0.0), 0.95))
                explode = float(p_cfg.get("explode", 0.0) or 0.0)
                percent = (f"%.{max(0, int(p_cfg.get('decimals', 1)))}f%%"
                           if p_cfg.get("percent") else None)
                out.append(f"vals_{tag} = {lit(values)}")
                out.append(
                    f"bars_{tag} = {target}.pie(vals_{tag}, "
                    f"labels={lit(labels or None)}, colors={lit(colors)}, "
                    f"startangle={float(p_cfg.get('start', PIE_START_ANGLE))}, "
                    f"counterclock={bool(p_cfg.get('clockwise', True))}, "
                    f"autopct={lit(percent)}, "
                    f"explode={lit(([explode] + [0.0] * (len(values) - 1)) if explode else None)}, "
                    f"textprops={{'fontsize': "
                    f"{int(p_cfg.get('label_size', 11))}}}, "
                    f"wedgeprops={{'width': {lit((1.0 - hole) if hole else None)}, "
                    f"'edgecolor': {lit(store_color(p_cfg.get('edgecolor', '#ffffff')))}, "
                    f"'linewidth': {float(p_cfg.get('edgewidth', 1.0))}}})[0]"
                )
                out.append(f"{target}.set_aspect('equal')")
                out.append(f"curves[{lit(str(column))}] = bars_{tag}[0]")
            elif st == "histogram":
                h_cfg = self.histogram_cfg.get(column, {})
                h_alpha = float(h_cfg.get("alpha", 0.85))
                h_color = store_color(h_cfg.get("color", line.get_color()))
                h_edge = store_color(h_cfg.get("edgecolor", "#ffffff"))
                h_width = float(h_cfg.get("edgewidth", 1.0))
                bins = self.histogram_bins(column)
                # the column holds raw values: matplotlib counts them itself
                out.append(f"sample_{tag} = np.asarray("
                           f"DATA[{lit(str(column))}], float)")
                out.append(f"sample_{tag} = sample_{tag}"
                           f"[np.isfinite(sample_{tag})]")
                out.append(
                    f"counts_{tag}, edges_{tag}, bars_{tag} = {target}.hist("
                    f"sample_{tag}, bins={bins}, "
                    f"color={lit(h_color)}, edgecolor={lit(h_edge)}, "
                    f"linewidth={h_width}, alpha={h_alpha}, "
                    f"label={lit(str(line.get_label()))})"
                )
                out.append(f"curves[{lit(str(column))}] = bars_{tag}[0]")
            else:
                out.append(
                    "curves[%s], = %s.plot(%s, DATA[%s], linestyle=%s, "
                    "linewidth=%s, color=%s, marker=%s, markersize=%s,"
                    % (lit(str(column)), target, x_data,
                       lit(str(column)), lit(str(line.get_linestyle())),
                       lit(float(line.get_linewidth())),
                       lit(store_color(line.get_color())),
                       lit(str(line.get_marker())),
                       lit(float(line.get_markersize()))))
                out.append(
                    "    markerfacecolor=%s, markeredgecolor=%s, "
                    "markeredgewidth=%s, label=%s)"
                    % (lit(store_color(line.get_markerfacecolor())),
                       lit(store_color(line.get_markeredgecolor())),
                       lit(float(line.get_markeredgewidth())),
                       lit(str(line.get_label()))))
            if not line.get_visible():
                out.append("curves[%s].set_visible(False)" % lit(str(column)))
            fill = self.fill_state.get(column) or {}
            if fill.get("on"):
                color = (store_color(line.get_color()) if fill.get("follow")
                         else fill.get("color", "#1f77b4"))
                base = ("0.0" if fill.get("base", "zero") == "zero"
                        else f"{target}.get_ylim()[0]")
                out.append(
                    "%s.fill_between(%s, DATA[%s], %s, facecolor=%s, "
                    "alpha=%s, hatch=%s, edgecolor=%s, linewidth=0.0, "
                    "label='_nolegend_', zorder=%s)"
                    % (target, x_data, lit(str(column)), base,
                       lit(color), lit(float(fill.get("alpha", 0.35))),
                       lit(fill.get("hatch") or None),
                       lit(color if fill.get("hatch") else "none"),
                       lit(float(line.get_zorder()) - 0.5)))
        if self.legend_visible and self.legends:
            out.append("")
            out.append("# every curve has a legend box of its own")
            for column in self.legends:
                state = self.legend_state.get(column) or {}
                line = self.series.get(column)
                if line is None:
                    continue
                edge = state.get("edge", "none")
                face = state.get("face", "none")
                out.append(
                    "legend = Legend(ax, [curves[%s]], [%s], loc=%s, "
                    "bbox_to_anchor=%s, bbox_transform=ax.transAxes, "
                    "prop={'size': %s}, framealpha=1.0)"
                    % (lit(str(column)), lit(str(line.get_label())),
                       lit(state.get("loc", "upper right")),
                       lit([float(one) for one in state.get("pos", (0.5, 0.5))]),
                       lit(int(state.get("size", 10)))))
                out.append("for text in legend.get_texts():")
                out.append("    text.set_color(%s)"
                           % lit(state.get("color", "#000000")))
                out.append("legend.get_frame().set_edgecolor(%s)" % lit(edge))
                out.append("legend.get_frame().set_linewidth(%s)"
                           % lit(0.0 if edge == "none" else 0.8))
                out.append("legend.get_frame().set_facecolor(%s)" % lit(face))
                out.append("ax.add_artist(legend)")
        return out

    def _script_texts(self):
        """The title and the dragged places of the three axis texts."""
        lit = self._literal
        out = ["", "# ----------------------------------- the title and the texts",
               "ax.set_title(%s, fontsize=%s, color=%s, pad=%s * PT)"
               % (lit(self.ax.get_title()),
                  lit(float(self.ax.title.get_fontsize())),
                  lit(store_color(self.ax.title.get_color())),
                  lit(float(self.fonts["title_pad"])))]
        artists = {"title": "ax.title", "x": "ax.xaxis.label",
                   "y": "ax.yaxis.label", "y2": "ax2.yaxis.label"}
        for name, artist in artists.items():
            if name == "y2" and self.ax2 is None:
                continue
            dx, dy = self.text_offset.get(name, (0.0, 0.0))
            if not dx and not dy:
                continue
            if name == "title":
                out.append("ax._autotitlepos = False")
            out.append("%s.set_transform(%s.get_transform() + "
                       "Affine2D().translate(%s, %s))"
                       % (artist, artist, lit(float(dx)), lit(float(dy))))
        return out

    def _script_objects(self):
        """The text boxes, the drawings and the arrows, as they are drawn."""
        lit = self._literal
        out = []
        if self.note_state:
            out += ["", "# ------------------------------------- the text boxes"]
        for state in self.note_state.values():
            edge, face = state.get("edge", "none"), state.get("face", "none")
            out.append(
                "ax.text(%s, %s, %s, transform=ax.transAxes, fontsize=%s, "
                "color=%s, ha='left', va='center', rotation=%s,"
                % (lit(float(state["pos"][0])), lit(float(state["pos"][1])),
                   lit(str(state["text"])), lit(int(state["size"])),
                   lit(state["color"]), lit(float(state.get("angle", 0.0) or 0.0))))
            out.append(
                "        rotation_mode='anchor', clip_on=False, zorder=6,")
            out.append(
                "        bbox={'boxstyle': 'round,pad=0.35', 'facecolor': %s, "
                "'edgecolor': %s, 'linewidth': %s})"
                % (lit(face), lit(edge), lit(0.0 if edge == "none" else 0.8)))

        if self.shape_state:
            out += ["", "# --------------------------------------- the drawings"]
        for key, state in self.shape_state.items():
            kind = state["kind"]
            x, y = float(state["x"]), float(state["y"])
            w, h = float(state["w"]), float(state["h"])
            angle = self.angle_of(state)
            centre = self.shape_centre(state)
            face = state.get("face", "none")
            common = ("transform=turned(ax, (%s, %s), %s), clip_on=False, "
                      "zorder=5, edgecolor=%s, linestyle=%s, linewidth=%s, "
                      "facecolor=%s"
                      % (lit(centre[0]), lit(centre[1]), lit(angle),
                         lit(state["edge"]), lit(state["style"]),
                         lit(float(state["width"])),
                         lit("none" if face == "none"
                             else to_hex(to_rgba(face, state.get("alpha", 0.6)),
                                         keep_alpha=True))))
            if kind == "line":
                ends = ([[x, y + h], [x + w, y]] if state.get("flip")
                        else [[x, y], [x + w, y + h]])
                out.append("ax.add_patch(Polygon(%s, closed=False, fill=False, %s))"
                           % (lit(ends), common))
            elif kind == "triangle":
                points = [[x + w / 2, y + h], [x, y], [x + w, y]]
                out.append("ax.add_patch(Polygon(%s, closed=True, %s))"
                           % (lit(points), common))
            elif kind in ("circle", "ellipse"):
                out.append("ax.add_patch(Ellipse((%s, %s), %s, %s, %s))"
                           % (lit(x + w / 2), lit(y + h / 2), lit(w), lit(h),
                              common))
            else:
                out.append("ax.add_patch(Rectangle((%s, %s), %s, %s, %s))"
                           % (lit(x), lit(y), lit(w), lit(h), common))

        if self.arrow_state:
            out += ["", "# ----------------------------------------- the arrows"]
        for key, state in self.arrow_state.items():
            points, shaft_end = self._head_polygon(state)
            out.append(
                "ax.plot([%s, %s], [%s, %s], transform=ax.transAxes, color=%s, "
                "linestyle=%s, linewidth=%s, solid_capstyle='butt', "
                "clip_on=False, zorder=5, label='_nolegend_')"
                % (lit(float(state["tail"][0])), lit(float(shaft_end[0])),
                   lit(float(state["tail"][1])), lit(float(shaft_end[1])),
                   lit(state["color"]), lit(state["style"]),
                   lit(float(state["width"]))))
            if points is None:
                continue
            corners = [[float(one[0]), float(one[1])] for one in points]
            if state["head"] == "chevron":
                out.append(
                    "ax.plot(%s, %s, transform=ax.transAxes, color=%s, "
                    "linestyle='-', linewidth=%s, solid_joinstyle='miter', "
                    "clip_on=False, zorder=5, label='_nolegend_')"
                    % (lit([one[0] for one in corners]),
                       lit([one[1] for one in corners]),
                       lit(state["color"]), lit(float(state["width"]))))
            else:
                out.append(
                    "ax.add_patch(Polygon(%s, closed=True, "
                    "transform=ax.transAxes, facecolor=%s, edgecolor=%s, "
                    "linewidth=%s, clip_on=False, zorder=5))"
                    % (lit(corners), lit(state["color"]), lit(state["color"]),
                       lit(max(0.2, float(state["width"]) * 0.5))))
        return out

    # -- saving / restoring the whole diagram ------------------------------
    def to_state(self):
        """Everything that makes this diagram look the way it looks."""
        axes = {}
        for which in ("x", "y", "y2"):
            if which == "y2" and self.ax2 is None:
                continue
            low, high = self.current_limits(which)
            cfg = self.axis_cfg[which]
            axes[which] = {
                "label": self.axis_label(which), "auto": cfg["auto"],
                "min": float(low), "max": float(high),
                "step": cfg["step"], "minor": cfg["minor"],
                "label_size": cfg["label_size"], "tick_size": cfg["tick_size"],
                "label_color": cfg["label_color"], "tick_color": cfg["tick_color"],
                "label_pad": cfg["label_pad"], "tick_pad": cfg["tick_pad"],
                "axis_color": self.axis_color(which),
                "label_on": bool(cfg.get("label_on", True)),
                "ticks_on": bool(cfg.get("ticks_on", True)),
                "grid": dict(cfg["grid"]),
            }
        series = []
        for y_col, line in self.series.items():
            state = self.legend_state.get(y_col) or self.default_legend_state(0)
            series.append({
                "column": str(y_col), "label": line.get_label(),
                "axis": self.series_side(y_col),
                "plot_style": self.series_style.get(y_col, self.plot_style),
                "bar_cfg": dict(self.bar_cfg.get(y_col, {})),
                "error_cfg": dict(self.error_cfg.get(y_col, {})),
                "histogram_cfg": dict(self.histogram_cfg.get(y_col, {})),
                "stairs_cfg": dict(self.stairs_cfg.get(y_col, {})),
                "hist2d_cfg": dict(self.hist2d_cfg.get(y_col, {})),
                "pie_cfg": dict(self.pie_cfg.get(y_col, {})),
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
            "plot_style": self.plot_style,
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
            "x_side": self.x_side,
            "error_partner": {str(mean): str(std)
                              for mean, std in self.error_partner.items()},
        }

    def apply_state(self, state):
        """Rebuild the appearance stored by to_state()."""
        figure = state.get("figure") or {}
        if figure:
            self.fig.set_size_inches(figure.get("width", self.fig.get_figwidth()),
                                     figure.get("height", self.fig.get_figheight()))
            self.fig.set_dpi(figure.get("dpi", self.fig.get_dpi()))

        if "plot_style" in state:
            self.plot_style = state["plot_style"]

        legend = state.get("legend") or {}
        self.legend_visible = bool(legend.get("visible", self.legend_visible))
        self.legend_loc = legend.get("location", self.legend_loc)
        self.fonts["legend"] = int(legend.get("size", self.fonts["legend"]))
        self.fonts["legend_color"] = legend.get("color", self.fonts["legend_color"])

        side = state.get("x_side")
        if side in ("bottom", "top"):
            self.x_side = side
            self.layout["x_side"] = side

        pairs = state.get("error_partner")
        if isinstance(pairs, dict):      # which column holds which error
            self.error_partner = {str(mean): str(std)
                                  for mean, std in pairs.items()}

        saved_series = state.get("series")
        if saved_series is not None:
            # the file decides which curves exist: a column that was not
            # plotted when it was saved does not appear now either
            wanted = {entry.get("column") for entry in saved_series}
            for column in [name for name in self.series if name not in wanted]:
                self.remove_series(column)

        for index, entry in enumerate(saved_series or []):
            column = entry.get("column")
            line = self.series.get(column)
            if line is None:
                continue
            self.move_series(column, entry.get("axis", "left"))
            self.layout.setdefault("y", {})[str(column)] = self.series_side(column)
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
            if "plot_style" in entry:
                self.series_style[column] = entry["plot_style"]
            if "bar_cfg" in entry:
                self.bar_cfg[column] = dict(entry["bar_cfg"])
            if "error_cfg" in entry:
                self.error_cfg[column] = dict(entry["error_cfg"])
            if "histogram_cfg" in entry:
                self.histogram_cfg[column] = dict(entry["histogram_cfg"])
            if "stairs_cfg" in entry:
                self.stairs_cfg[column] = dict(entry["stairs_cfg"])
            if "hist2d_cfg" in entry:
                self.hist2d_cfg[column] = dict(entry["hist2d_cfg"])
            if "pie_cfg" in entry:
                self.pie_cfg[column] = dict(entry["pie_cfg"])
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
            self.refresh_series_visuals(column)

        # a histogram counted its bins again just now: the automatic range
        # follows those counts (a range that was set by hand is restored
        # below and wins over this)
        self._rescale()

        # a file written before the axis colours existed carried one colour
        # for the whole frame: give it to all three axes, so it looks the same
        old_color = (state.get("frame") or {}).get("color")
        for which in ("x", "y", "y2"):
            cfg = (state.get("axes") or {}).get(which)
            if cfg is None:
                continue
            if which == "y2" and self.ax2 is None and not self.right_axis_active():
                continue          # no curve on the right: nothing to restore
            if "axis_color" not in cfg and old_color:
                cfg = {**cfg, "axis_color": old_color}
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
        # what the X axis really carries: the first column, or - when that
        # column is the only filled one - the row number of the table
        x_col = self.x_axis_name()
        self._auto_x_label = x_col
        if self.plot_style == "pie":
            # a pie has no axes: no label, no numbers, no frame lines, and
            # it must stay round whatever the shape of the window
            x_col = ""
            self._auto_x_label = ""
            for which in ("x", "y"):
                self.axis_cfg[which] = {**self.axis_cfg[which], "label": "",
                                        "label_on": False, "ticks_on": False}
            plot_cfg = {**plot_cfg, "y_label": ""}
            self.ax.set_aspect("equal")
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
        if self.ax2 is not None:
            self._text_base["y2"] = self.ax2.yaxis.label.get_transform()
            if not self.ax2.get_ylabel():
                # the name of the first column drawn there is a useful start
                right = [name for name, side in self.series_axis.items()
                         if side == "right"]
                if right:
                    self.apply_axis("y2", {**self.axis_cfg["y2"],
                                           "label": str(right[0])}, redraw=False)
        self._rescale()

    def _reapply_distances(self):
        """Turn the stored pixel distances into points for the current dpi."""
        for which in ("x", "y", "y2"):
            if which == "y2" and self.ax2 is None:
                continue
            ax, axis, axis_name = self._axis_pair(which)
            axis.labelpad = self.points(self.axis_cfg[which]["label_pad"])
            ax.tick_params(axis=axis_name, which="both",
                           pad=self.points(self.axis_cfg[which]["tick_pad"]))
        self.ax.set_title(self.ax.get_title(), fontsize=self.fonts["title"],
                          color=safe_hex(self.fonts["title_color"], "#000000"),
                          pad=self.points(self.fonts["title_pad"]))
        self.ax.title.set_picker(True)
        self.apply_text_offsets()

    def _on_resize(self, _event=None):
        """The Tk canvas may change the resolution: keep the pixels honest."""
        if self._inline is not None:   # the editor would sit in the wrong place
            self.commit_inline_edit()
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

    def legend_handle(self, column, line):
        """What is drawn in front of the legend text of one curve.

        A bar chart and a histogram draw their curve with no line and no
        marker at all - the bars are patches beside it - so the curve itself
        would leave an empty space in front of the text.  One of the bars is
        used instead, and an error bar plot shows its own container, so the
        little sample really looks like what is in the diagram.
        """
        style = self.series_style.get(column, self.plot_style)
        if style == "stairs":
            patch = self.stairs_patches.get(column)
            return patch if patch is not None else line
        if style == "pie":
            wedges = self.pie_wedges.get(column) or []
            return wedges[0] if wedges else line
        if style == "hist2d":
            # a QuadMesh cannot be drawn in a legend box: a little patch of
            # the middle colour of its scale stands for it
            cfg = self.hist2d_cfg.get(column) or {}
            colors = self.slice_colors(cfg.get("cmap", "viridis"), 3)
            return Rectangle((0, 0), 1, 1, facecolor=colors[len(colors) // 2],
                             edgecolor="none")
        if style == "bar":
            container = self.bar_containers.get(column)
        elif style == "histogram":
            container = self.bar_containers.get(f"hist_{column}")
        elif style == "errorbar":
            container = self.errorbar_containers.get(column)
            # the marker of the curve and one error bar through it, so the
            # sample in front of the text looks like a point of the diagram
            return (line, container) if container is not None else line
        else:
            return line
        patches = list(getattr(container, "patches", ()) or ())
        return patches[0] if patches else line

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
            handle = self.legend_handle(y_col, line)
            legend = Legend(self.ax, [handle], [label], loc=state["loc"],
                            bbox_to_anchor=state["pos"],
                            bbox_transform=self.ax.transAxes,
                            prop={"size": state["size"]}, framealpha=1.0,
                            # ndivide=1: the parts are drawn over each other, so a marker with
                            # an error bar through it is one single sample
                            handler_map={tuple: HandlerTuple(ndivide=1)})
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
            "flip": False,          # a line drawn from top left to bottom right
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
        if state["kind"] in OPEN_SHAPES:   # a horizontal line stays horizontal
            w, h = state["w"], state["h"]
        else:
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
        if state["kind"] == "line":
            ends = ([[x, y + h], [x + w, y]] if state.get("flip")
                    else [[x, y], [x + w, y + h]])
            common["facecolor"] = "none"        # a stroke has nothing to fill
            patch = Polygon(ends, closed=False, fill=False, **common)
        elif state["kind"] == "triangle":
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
            state = self.shape_state[key]
            if state["kind"] in OPEN_SHAPES:
                return None      # its two ends give the direction, as an arrow
            return self.shape_centre(state)
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
                "text": self.text_offset, "axis": self.frame_sides}.get(kind)

    def select_object(self, kind, key):
        """Remember the object the keyboard commands work on."""
        store = self._selection_store(kind)
        if store is not None and key in store:
            if kind == "text" and not self.text_shown(key):
                kind = None             # only a text that is really there
            if kind == "axis" and not self.ax.spines[key].get_visible():
                kind = None             # only a line that is really drawn
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
            return self.text_artist(key) if self.text_shown(key) else None
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
            if artist is None or not self.text_shown(key):
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

    # -- writing a text in place -------------------------------------------
    def text_value(self, kind, key):
        """The text of one editable object, as the user sees it."""
        if kind == "note":
            state = self.note_state.get(key)
            return "" if state is None else str(state.get("text", ""))
        if kind == "text":
            return self.ax.get_title() if key == "title" else self.axis_label(key)
        if kind == "legend":
            line = self.series.get(key)
            label = "" if line is None else str(line.get_label())
            return "" if not label or label.startswith("_") else label
        return ""

    def set_text_value(self, kind, key, text):
        """Give one editable object a new text, everything else unchanged."""
        text = str(text)
        if kind == "text":
            if key == "title":
                self.ax.set_title(
                    text, fontsize=self.fonts["title"],
                    color=safe_hex(self.fonts["title_color"], "#000000"),
                    pad=self.points(self.fonts["title_pad"]))
                self.ax.title.set_picker(True)
                self.apply_text_offset("title")   # set_title resets the place
            else:
                cfg = dict(self.axis_cfg[key])
                cfg["label"] = text
                self.apply_axis(key, cfg)
        elif kind == "note":
            state = self.note_state.get(key)
            if state is None:
                return None
            state["text"] = text
            self._marked = None            # the artist itself is rebuilt
            if not text.strip():
                self.remove_note(key)      # an empty text box goes away
                return None
            self.refresh_note(key)
        elif kind == "legend":
            line = self.series.get(key)
            if line is None:
                return None
            line.set_label(text.strip() if text.strip() else "_nolegend_")
            self._marked = None
            self.refresh_legend()
        else:
            return None
        self._refresh_highlight()
        return None

    def inline_target(self, kind, key):
        """The artist an in-place editor would sit on, or None."""
        if kind == "note":
            return self.notes.get(key)
        if kind == "text":
            return self.text_artist(key) if self.text_shown(key) else None
        if kind == "legend":
            legend = self.legends.get(key)
            if legend is None:
                return None
            texts = list(legend.get_texts())
            return texts[0] if texts else None
        return None

    def is_editing_inline(self):
        """True while a text is being written straight on the diagram."""
        return self._inline is not None

    def _inline_font(self, artist):
        """A Tk font of about the size the artist is drawn with."""
        try:
            points = float(artist.get_fontsize())
        except (AttributeError, TypeError, ValueError):
            points = 12.0
        pixels = max(8, int(round(points * float(self.fig.get_dpi()) / 72.0)))
        try:
            return tkfont.Font(family=INLINE_FAMILY, size=-pixels)
        except tk.TclError:
            return tkfont.Font(size=-pixels)

    def _inline_geometry(self, artist, font, value):
        """Where the little editor goes and how big it is, in widget pixels."""
        widget = self.canvas.get_tk_widget()
        widget.update_idletasks()
        width_px = max(1, widget.winfo_width())
        height_px = max(1, widget.winfo_height())
        try:
            box = artist.get_window_extent(self._renderer())
            centre = (0.5 * (box.x0 + box.x1),
                      height_px - 0.5 * (box.y0 + box.y1))
        except (RuntimeError, ValueError, AttributeError):
            centre = (0.5 * width_px, 0.5 * height_px)
        lines = value.split("\n") or [""]
        text_w = max([font.measure(line) for line in lines] + [0])
        line_h = font.metrics("linespace")
        width = max(INLINE_MIN_WIDTH, text_w + 2 * INLINE_PAD + 6)
        height = len(lines) * line_h + 2 * INLINE_PAD + 4
        x = int(round(centre[0] - width / 2.0))
        y = int(round(centre[1] - height / 2.0))
        x = max(0, min(x, width_px - int(width)))
        y = max(0, min(y, height_px - int(height)))
        return x, y, int(width), int(height)

    def begin_inline_edit(self, kind, key, x=None, y=None):
        """Open a small text box over one text, cursor where the pointer is.

        This is the second, slower click of the Finder-like rename: one click
        selects the object, a second one within RENAME_DELAY milliseconds -
        too slow to be a double click - lets the text itself be rewritten.
        """
        if kind not in EDITABLE_KINDS:
            return None
        artist = self.inline_target(kind, key)
        if artist is None:
            return None
        self.cancel_inline_edit()
        widget = self.canvas.get_tk_widget()
        value = self.text_value(kind, key)
        font = self._inline_font(artist)
        left, top, width, height = self._inline_geometry(artist, font, value)
        # the blinking cursor: its colour is set by hand, because the colour
        # the system gives it can be white - invisible on the white editor
        caret = max(2, int(round(font.metrics("linespace") / 9.0)))
        editor = tk.Text(widget, font=font, wrap="none", undo=True,
                         borderwidth=1, relief="solid", highlightthickness=1,
                         highlightcolor=SELECT_COLOR, highlightbackground=SELECT_COLOR,
                         padx=INLINE_PAD, pady=INLINE_PAD,
                         insertwidth=caret, insertborderwidth=0,
                         insertbackground=CARET_COLOR,
                         insertontime=CARET_ON_MS, insertofftime=CARET_OFF_MS,
                         selectbackground=SELECT_COLOR, selectforeground="#ffffff",
                         background="#ffffff", foreground="#000000")
        try:      # older Tk versions do not know this one
            editor.configure(insertunfocussed="hollow")
        except tk.TclError:
            pass
        editor.insert("1.0", value)
        # the arrow keys, Delete and copy/paste of the window would move or
        # remove the selected object: inside the editor they belong to the text
        editor.bindtags((str(editor), "Text", "all"))
        editor.bind("<Return>", self._inline_return)
        editor.bind("<KP_Enter>", self._inline_return)
        editor.bind("<Shift-Return>", lambda _e: None)
        editor.bind("<Escape>", lambda _e: (self.cancel_inline_edit(), "break")[1])
        editor.bind("<FocusOut>", lambda _e: self.commit_inline_edit())
        editor.place(x=left, y=top, width=width, height=height)
        self._inline = {"kind": kind, "key": key, "editor": editor,
                        "value": value, "artist": artist}
        artist.set_visible(False)          # the editor takes its place
        self.draw()
        editor.focus_set()
        try:
            editor.update_idletasks()      # the text has to be laid out first
        except tk.TclError:
            pass
        if x is not None and y is not None:
            try:
                pointer_x = int(round(float(x))) - left
                pointer_y = int(round(widget.winfo_height() - float(y))) - top
                editor.mark_set("insert", f"@{pointer_x},{pointer_y}")
            except (tk.TclError, TypeError, ValueError):
                editor.mark_set("insert", "end")
        else:
            editor.mark_set("insert", "end")
        editor.see("insert")
        # the cursor only blinks in the widget that holds the keyboard, and
        # the click that opened the editor is still on its way to the canvas
        self._insist_inline_focus(editor)
        self.after(30, lambda box=editor: self._insist_inline_focus(box))
        self.flash("Write the text and press Enter - Escape keeps the old one")
        return editor

    def _insist_inline_focus(self, editor):
        """Keep the keyboard - and with it the blinking cursor - in the editor."""
        if self._inline is None or self._inline["editor"] is not editor:
            return None
        try:
            if not editor.winfo_exists():
                return None
            if editor.focus_displayof() is not editor:
                editor.focus_force()
        except (tk.TclError, KeyError):
            pass
        return None

    def _inline_return(self, _event=None):
        self.commit_inline_edit()
        return "break"

    def inline_text(self):
        """What the open editor holds at the moment, or None."""
        if self._inline is None:
            return None
        try:
            return self._inline["editor"].get("1.0", "end-1c")
        except tk.TclError:
            return None

    def _close_inline(self):
        """Take the editor away and show the text again."""
        inline, self._inline = self._inline, None
        self._pending_rename = None
        if inline is None:
            return None
        artist = inline["artist"]
        try:
            artist.set_visible(True)
        except AttributeError:
            pass
        editor = inline["editor"]
        try:
            if editor.winfo_exists():
                editor.destroy()
        except tk.TclError:
            pass
        self.take_focus()
        return inline

    def commit_inline_edit(self, _event=None):
        """Keep what was written and close the editor."""
        if self._inline is None:
            return None
        text = self.inline_text()
        inline = self._close_inline()
        if inline is None:
            return None
        if text is None:
            text = inline["value"]
        if text != inline["value"]:
            self.set_text_value(inline["kind"], inline["key"], text)
        self.select_object(inline["kind"], inline["key"])
        self._rename_click = None
        self.draw()
        return text

    def cancel_inline_edit(self, _event=None):
        """Throw the writing away and close the editor."""
        inline = self._close_inline()
        if inline is None:
            return None
        self._rename_click = None
        self.draw()
        return inline["value"]

    def _arm_inline_edit(self, kind, key, event):
        """Remember a slow second click on an already selected text.

        The editor is not opened here but when the button is released: a
        press that turns into a drag moves the text, exactly as before, and
        only a press-and-release on the same spot starts the writing.
        """
        now = time.monotonic()
        previous, self._rename_prev = self._rename_prev, None
        self._rename_click = (kind, key, now)
        self._pending_rename = None
        if (previous is None or previous[0] != kind or previous[1] != key
                or self.selection != (kind, key)
                or (now - previous[2]) * 1000.0 > RENAME_DELAY):
            return False
        self._rename_click = None
        self._pending_rename = {"kind": kind, "key": key,
                                "x": event.x, "y": event.y}
        return True

    def _open_pending_rename(self):
        """The release after a slow second click opens the little editor."""
        pending, self._pending_rename = self._pending_rename, None
        if pending is None or self._inline is not None:
            return None
        return self.begin_inline_edit(pending["kind"], pending["key"],
                                      pending["x"], pending["y"])

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
        if kind == "axis":
            return self.move_axes(dx_pixels, dy_pixels)
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

    def close_window(self, *_args):
        """The window button: an edited graph is not thrown away silently."""
        app = self.app
        if app is not None and hasattr(app, "plot_closing"):
            if not app.plot_closing(self):
                return False
        self.destroy()
        if app is not None and hasattr(app, "plot_closed"):
            app.plot_closed(self)
        return True

    def figure_image(self, path=None, dpi=None, transparent=None):
        """Write a picture of the diagram, without the selection marks."""
        if path is None:
            path = os.path.join(tempfile.gettempdir(),
                                f"aplot_figure_{os.getpid()}.png")
        selection = self.selection
        self.select_object(None, None)
        try:
            self.canvas.draw()
            if transparent is None:
                transparent = self.frame_cfg.get("figure_background") == "none"
            self.fig.savefig(path, dpi=dpi or self.fig.get_dpi(),
                             bbox_inches="tight", transparent=bool(transparent),
                             facecolor=self.fig.get_facecolor())
        finally:
            if selection is not None:
                self.select_object(*selection)
            self.canvas.draw_idle()
        return path

    def copy_figure_to_clipboard(self, *_args):
        """Cmd/Ctrl+C with nothing selected: the whole diagram as a picture."""
        try:
            path = self.figure_image(dpi=CLIPBOARD_DPI)
        except (OSError, ValueError) as error:
            messagebox.showerror("Error", f"Could not draw the picture: {error}",
                                 parent=self)
            return False
        if copy_png_to_clipboard(path):
            self.flash("The diagram is on the clipboard as a picture")
            return True
        messagebox.showinfo(
            "Clipboard",
            "This system has no tool to put a picture on the clipboard.\n"
            f"The picture was written to:\n{path}", parent=self)
        return False

    def copy_shortcut(self, *_args):
        """Cmd/Ctrl+C: the selected object, or the whole diagram as a picture."""
        if self.selection is not None:
            return self.copy_selection()
        return self.copy_figure_to_clipboard()

    def export_figure(self, *_args):
        """Save the diagram as an image file, without the selection marks."""
        return self.save_figure_clean()

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
        if kind == "axis" and self.axis_side(key) is not None:
            return self.axis_handle_positions(key)
        if kind == "shape" and key in self.shape_state:
            state = self.shape_state[key]
            if state["kind"] in OPEN_SHAPES:
                return list(self.line_ends(state))   # the two ends, as an arrow
            return self.shape_handle_positions(state)
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
            # a control point is a tool, not a part of the picture: it must
            # not make a saved image any bigger
            self._handles.set_in_layout(False)
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
            self._rotator.set_in_layout(False)
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

    def line_ends(self, state):
        """The two ends of a drawn line, in the coordinates of the plot area."""
        x, y, w, h = state["x"], state["y"], state["w"], state["h"]
        ends = ([(x, y + h), (x + w, y)] if state.get("flip")
                else [(x, y), (x + w, y + h)])
        angle = self.angle_of(state)
        if angle:
            centre = self.shape_centre(state)
            ends = [self._turn_point(point, centre, angle) for point in ends]
        return ends

    def set_line_ends(self, key, first, second):
        """Put the two ends of a drawn line where they are asked for.

        The ends are the line, exactly as the tip and the tail are the arrow,
        so any earlier rotation is taken into the new pair of points.
        """
        state = self.shape_state.get(key)
        if state is None or state["kind"] not in OPEN_SHAPES:
            return False
        (x0, y0), (x1, y1) = first, second
        state["x"], state["w"] = float(min(x0, x1)), float(abs(x1 - x0))
        state["y"], state["h"] = float(min(y0, y1)), float(abs(y1 - y0))
        state["flip"] = bool((x1 - x0) * (y1 - y0) < 0)
        state["angle"] = 0.0
        self.refresh_shape(key)
        return True

    def _line_hit(self, state, x, y, tolerance=None):
        """Distance test against a drawn line: a stroke has no inside."""
        first, second = (np.array(self.ax.transAxes.transform(point), dtype=float)
                         for point in self.line_ends(state))
        segment = second - first
        length = float(np.hypot(*segment))
        if length < 1e-6:
            return False
        point = np.array([x, y], dtype=float)
        position = float(np.clip(np.dot(point - first, segment) / length ** 2,
                                 0.0, 1.0))
        distance = float(np.hypot(*(point - (first + position * segment))))
        return distance <= (tolerance if tolerance is not None
                            else max(4.0, float(state["width"]) + 3.0))

    def shape_at(self, x, y):
        """Key of the drawn object under the pointer, or None."""
        if x is None or y is None:
            return None
        for key in reversed(list(self.shapes)):        # topmost first
            state = self.shape_state.get(key)
            if state is not None and state["kind"] in OPEN_SHAPES:
                if self._line_hit(state, x, y):
                    return key
                continue
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
        self.cancel_inline_edit()
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
    def text_shown(self, name):
        """True while one of the three axis texts is really on the diagram."""
        artist = self.text_artist(name)
        if artist is None or not artist.get_text() or not artist.get_visible():
            return False
        if name == "y":
            return self.left_axis_shown()
        if name == "y2":
            return self.right_axis_active()
        return True

    def text_artist(self, name):
        if name == "y2":
            return None if self.ax2 is None else self.ax2.yaxis.label
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
        for name in ("title", "x", "y", "y2"):
            self.apply_text_offset(name)

    def reset_text_offsets(self):
        for name in ("title", "x", "y", "y2"):
            self.text_offset[name] = (0.0, 0.0)
        self.apply_text_offsets()
        self.draw()

    def text_at(self, x, y):
        """Name of the movable text under the pointer, or None."""
        if x is None or y is None:
            return None
        renderer = self._renderer()
        for name in ("title", "x", "y", "y2"):
            artist = self.text_artist(name)
            if artist is None or not self.text_shown(name):
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
        pending = self._pending_rename
        if pending is not None and event.x is not None and event.y is not None:
            if (abs(event.x - pending["x"]) > 3.0
                    or abs(event.y - pending["y"]) > 3.0):
                self._pending_rename = None    # this is a drag, not a rename
        if self._shape_drag is not None:
            if event.x is None or event.y is None:
                return
            drag = self._shape_drag
            key = drag["key"]
            mode = drag["mode"]
            if mode == "axis-end":             # pull the end of an axis
                self.resize_axis(drag["key"], drag["index"],
                                 self._figure_point(event))
                self._refresh_handles()
                self.draw()
                return
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
            state = self.shape_state[key]
            snap = self._shift_active(event)
            if mode == "line-end":             # one end of a line, as an arrow
                fixed = drag.get("fixed")
                if fixed is None:
                    fixed = self.line_ends(state)[1 - drag["index"]]
                if snap:
                    point = self._snap_point(fixed, point)
                self.set_line_ends(key, fixed, point)
                self._refresh_handles()
                self.draw()
                return
            if drag["mode"] == "new":          # rubber band from the anchor
                anchor = drag["anchor"]
                if state["kind"] in OPEN_SHAPES:
                    # Shift keeps the new line at 45 degree steps, as an arrow
                    if snap:
                        point = self._snap_point(anchor, point)
                    self.set_line_ends(key, anchor, point)
                    self.draw()
                    return
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

    def _on_release(self, event=None):
        self._finish_drag(event)
        self._open_pending_rename()

    def _finish_drag(self, _event=None):
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
        if shape_drag is not None and shape_drag["mode"] in ("rotate", "axis-end"):
            self._refresh_handles()
            self.draw()
            return
        if shape_drag is not None:
            key = shape_drag["key"]
            state = self.shape_state.get(key)
            if state is not None:
                if shape_drag["mode"] == "new" and state["kind"] in OPEN_SHAPES:
                    ends = self.line_ends(state)
                    first = np.array(self.ax.transAxes.transform(ends[0]))
                    second = np.array(self.ax.transAxes.transform(ends[1]))
                    if float(np.hypot(*(second - first))) < 12.0:  # a plain click
                        self.set_line_ends(key, ends[0],
                                           (ends[0][0] + 0.18, ends[0][1]))
                        self._refresh_handles()
                elif shape_drag["mode"] == "new" and (
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
        axis_end = self.axis_end_at(event.x, event.y)
        if axis_end is not None:
            _kind, which = self.selection
            cursor = ("sb_h_double_arrow"
                      if self.axis_side(which) in HORIZONTAL_SIDES
                      else "sb_v_double_arrow")
        elif index == ROTATE_HANDLE:
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
        if which == "x":
            return self.ax.get_xlabel()
        if which == "y2":
            return "" if self.ax2 is None else self.ax2.get_ylabel()
        return self.ax.get_ylabel()

    def current_limits(self, which):
        if which == "x":
            return self.ax.get_xlim()
        if which == "y2":
            return (0.0, 1.0) if self.ax2 is None else self.ax2.get_ylim()
        return self.ax.get_ylim()

    def _axis_pair(self, which):
        """(axes, axis, "x"/"y") of one of the three axis pages."""
        if which == "y2":
            ax = self.ensure_right_axis()
            return ax, ax.yaxis, "y"
        if which == "x":
            return self.ax, self.ax.xaxis, "x"
        return self.ax, self.ax.yaxis, "y"

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

        used = self.used_sides()
        for name, spine in self.ax.spines.items():
            # a closed frame draws all four sides, "no frame" only the lines
            # the axes in use actually sit on
            spine.set_visible(closed or name in used)
            spine.set_linewidth(width)
            spine.set_picker(6)          # clicking the frame opens this dialog

        # the colours belong to the three axis pages (see _apply_axis_colors)
        self.ax.tick_params(
            which="both", width=width,
            top=(style == "box_in" or style == "box_out"),
            right=(style == "box_in" or style == "box_out"),
            direction="in" if style == "box_in" else "out")
        self.ax.tick_params(which="major", length=major_length)
        self.ax.tick_params(which="minor", length=minor_length)
        if self.ax2 is not None:
            for spine in self.ax2.spines.values():
                spine.set_visible(False)   # the main axes draws the frame
            self.ax2.tick_params(which="both", width=width,
                                 direction="in" if style == "box_in" else "out")
            self.ax2.tick_params(which="major", length=major_length)
            self.ax2.tick_params(which="minor", length=minor_length)
            self.ax2.set_facecolor("none")

        background = cfg.get("background", "#ffffff")
        figure_background = cfg.get("figure_background", "#ffffff")
        self.ax.set_facecolor("none" if background == "none" else background)
        self.fig.set_facecolor("none" if figure_background == "none"
                               else figure_background)

        self.ax.set_position([cfg["left"], cfg["bottom"],
                              cfg["x_length"], cfg["y_length"]])
        if self.ax2 is not None:
            self.ax2.set_position(self.ax.get_position())
        self.frame_cfg = {"style": style, "width": width, "color": color,
                          "major_tick_length": major_length,
                          "minor_tick_length": minor_length,
                          "background": background,
                          "figure_background": figure_background,
                          "left": float(cfg["left"]), "bottom": float(cfg["bottom"]),
                          "x_length": float(cfg["x_length"]),
                          "y_length": float(cfg["y_length"])}
        self._apply_axis_sides()     # bottom or top X, left or right Y
        kind, key = self.selection or (None, None)
        if kind == "axis" and not self.ax.spines[key].get_visible():
            self.select_object(None, None)   # that line is not drawn any more
        # the plot area moved: the pixel geometry of the objects is rebuilt
        self.refresh_shapes()
        self.refresh_arrows()
        self._refresh_handles()
        if redraw:
            self.draw()

    def apply_axis(self, which, cfg, redraw=True):
        """Range / ticks / minor ticks / grid / fonts of one axis."""
        ax, axis, axis_name = self._axis_pair(which)

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
        stored = self.axis_cfg.get(which, {})
        axis_color = safe_hex(cfg.get("axis_color",
                                      stored.get("axis_color", "#000000")),
                              "#000000")
        label_on = bool(cfg.get("label_on", stored.get("label_on", True)))
        ticks_on = bool(cfg.get("ticks_on", stored.get("ticks_on", True)))
        axis.label.set_fontsize(label_size)
        axis.label.set_color(label_color)
        axis.label.set_visible(label_on)     # the section switch of the dialog
        axis.label.set_picker(True)
        axis.labelpad = self.points(label_pad)      # distance of the label
        ax.tick_params(axis=axis_name, which="both", labelsize=tick_size,
                       labelcolor=tick_color, pad=self.points(tick_pad))

        if cfg["auto"]:
            axis.set_major_locator(AutoLocator())
            ax.autoscale(enable=True, axis=axis_name)
            self.measure_data(ax)
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
        if which == "x":
            if grid["major"]:
                ax.grid(True, which="major", axis="x", color=grid["color"],
                        linestyle=grid["style"], linewidth=grid["width"])
            else:
                ax.grid(False, which="major", axis="x")
            if grid["minor"] and minor:
                ax.grid(True, which="minor", axis="x", color=grid["color"],
                        linestyle=grid["style"],
                        linewidth=max(0.3, grid["width"] * 0.6))
            else:
                ax.grid(False, which="minor", axis="x")

        self.axis_cfg[which] = {
            "auto": cfg["auto"], "step": cfg.get("step"), "minor": minor,
            "label_size": label_size, "tick_size": tick_size,
            "label_color": label_color, "tick_color": tick_color,
            "label_pad": label_pad, "tick_pad": tick_pad,
            "axis_color": axis_color, "label_on": label_on,
            "ticks_on": ticks_on,
            "grid": dict(grid),
        }
        if which in ("y", "y2"):  # fills reaching the bottom follow the range
            for column, fill_cfg in self.fill_state.items():
                if (fill_cfg.get("on") and fill_cfg.get("base") == "bottom"
                        and self.series_side(column) == ("right" if which == "y2"
                                                         else "left")):
                    self.refresh_fill(column)
        self._apply_axis_sides()     # which numbers are shown, and the grid
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
        # a curve or bar or errorbar is never "selected": one click opens its properties
        series_name = getattr(artist, "aplot_series", None)
        if series_name is not None and series_name in self.series:
            self.open_series_dialog(self.series[series_name])
            return
        if isinstance(artist, Line2D) and artist in self.lines:
            self.open_series_dialog(artist)
            return

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

    def axis_end_at(self, x, y, tolerance=8.0):
        """Index of the axis control point under the pointer, or None."""
        kind, key = self.selection or (None, None)
        if kind != "axis":
            return None
        for index, point in enumerate(self.axis_handle_positions(key)):
            px, py = self.ax.transAxes.transform(point)
            if abs(px - x) <= tolerance and abs(py - y) <= tolerance:
                return index
        return None

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
        if kind in ("frame", "axis"):
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
        if self._inline is not None:       # a click elsewhere finishes writing
            self.commit_inline_edit()
        if event.dblclick:                 # every object needs two clicks
            self._rename_click = None      # a real double click is not a rename
            self._rename_prev = None
            self._pending_rename = None
            self._on_double_click(event)
            return
        if event.button != 1:
            return
        self._pending_rename = None
        # only a second click on the very same, already selected text opens
        # the in-place editor: any other click starts the count again
        self._rename_prev, self._rename_click = self._rename_click, None
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
            mode = "resize"
            if kind == "axis":
                mode = "axis-end"
            elif kind == "arrow":
                mode = "arrow-end"
            elif (kind == "shape"
                  and self.shape_state[key]["kind"] in OPEN_SHAPES):
                mode = "line-end"         # a line is dragged by its two ends
            self._shape_drag = {"key": key, "index": index, "mode": mode}
            if mode == "line-end":
                # the end that stays is remembered, so that dragging one end
                # past the other one does not swap them mid-drag
                ends = self.line_ends(self.shape_state[key])
                self._shape_drag["fixed"] = tuple(ends[1 - index])
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
            self._arm_inline_edit("note", key, event)
            self.select_object("note", key)
            self.announce_selection()
            self.draw()
            self._start_text_drag(f"{NOTE_KEY}{key}", event)
            return
        name = self.text_at(event.x, event.y)
        if name is not None:              # the title or an axis label
            self._arm_inline_edit("text", name, event)
            self.select_object("text", name)
            self.announce_selection()
            self.draw()
            self._start_text_drag(name, event)
            return
        y_col, legend = self.legend_at(event.x, event.y)
        if legend is not None:            # select a legend box and drag it
            self._arm_inline_edit("legend", y_col, event)
            self.select_object("legend", y_col)
            self.announce_selection()
            self.draw()
            self._start_legend_drag(y_col, event)
            return
        side = self.frame_axis_at(event.x, event.y)
        if side is not None:              # an axis line: select it to resize
            self.select_object("axis", side)
            self.draw()
            self.flash(f"{SIDE_NAMES.get(side, side)} selected - drag one of "
                       "its ends to resize it, double click for frame and origin")
            return
        if self.selection is not None:    # clicking elsewhere deselects
            self.select_object(None, None)
            self.draw()

    def frame_side_at(self, x, y):
        """Name of the visible frame side under the pointer, or None."""
        if x is None or y is None:
            return None
        box = self.ax.get_window_extent()
        tolerance = max(4.0, self.frame_cfg["width"] + 3.0)
        vertical = box.y0 - tolerance <= y <= box.y1 + tolerance
        horizontal = box.x0 - tolerance <= x <= box.x1 + tolerance
        sides = {"left": horizontal and vertical and abs(x - box.x0) <= tolerance,
                 "right": horizontal and vertical and abs(x - box.x1) <= tolerance,
                 "bottom": horizontal and vertical and abs(y - box.y0) <= tolerance,
                 "top": horizontal and vertical and abs(y - box.y1) <= tolerance}
        for name, hit in sides.items():
            if hit and self.ax.spines[name].get_visible():
                return name
        return None

    def frame_axis_at(self, x, y):
        """The side of the plot area whose line is under the pointer.

        One of "bottom", "top", "left" and "right" - the side itself, so
        that the control points appear on the line that was clicked.
        """
        return self.frame_side_at(x, y)

    def frame_hit(self, x, y):
        """True when the pointer is on one of the visible frame sides."""
        return self.frame_side_at(x, y) is not None

    # -- the axes are resized by their two ends ----------------------------
    @staticmethod
    def axis_side(which):
        """The frame side one name means ("x" and "y" are the old names)."""
        name = SIDE_ALIASES.get(str(which), str(which))
        return name if name in FRAME_ENDS else None

    def axis_handle_positions(self, which):
        """The two ends of one axis, in the coordinates of the plot area.

        Each of the four sides has its own pair: the bottom and the top line
        end in the lower and the upper corners, the left and the right line
        in the corners of their own edge.
        """
        side = self.axis_side(which)
        if side is None:
            return [(0.0, 0.0), (1.0, 0.0)]
        return [tuple(point) for point in FRAME_ENDS[side]]

    def _figure_point(self, event):
        """The pointer as a fraction of the whole figure."""
        point = self.fig.transFigure.inverted().transform((event.x, event.y))
        return (float(point[0]), float(point[1]))

    def resize_axis(self, which, index, point):
        """Pull one end of an axis: the plot area grows or shrinks there.

        The two horizontal sides (the bottom and the top X axis) carry the
        width of the diagram, the two vertical ones (the left and the right
        Y axis) its height - whichever of them is pulled.
        """
        side = self.axis_side(which) or "bottom"
        cfg = dict(self.frame_cfg)
        left, bottom = float(cfg["left"]), float(cfg["bottom"])
        width, height = float(cfg["x_length"]), float(cfg["y_length"])
        if side in HORIZONTAL_SIDES:
            if index == 0:                      # the left end moves
                right = left + width
                left = min(max(0.02, point[0]), right - MIN_AXIS_SIZE)
                width = right - left
            else:                               # the right end moves
                width = min(max(MIN_AXIS_SIZE, point[0] - left), 0.995 - left)
        else:
            if index == 0:                      # the bottom end moves
                top = bottom + height
                bottom = min(max(0.02, point[1]), top - MIN_AXIS_SIZE)
                height = top - bottom
            else:                               # the top end moves
                height = min(max(MIN_AXIS_SIZE, point[1] - bottom), 0.995 - bottom)
        cfg.update({"left": left, "bottom": bottom,
                    "x_length": width, "y_length": height})
        self.apply_frame(cfg)
        return cfg

    def move_axes(self, dx_pixels, dy_pixels):
        """Shift the whole plot area, keeping its size (the arrow keys)."""
        cfg = dict(self.frame_cfg)
        width = float(self.fig.get_figwidth() * self.fig.get_dpi())
        height = float(self.fig.get_figheight() * self.fig.get_dpi())
        if width <= 0 or height <= 0:
            return False
        left = float(cfg["left"]) + float(dx_pixels) / width
        bottom = float(cfg["bottom"]) + float(dy_pixels) / height
        cfg["left"] = min(max(0.02, left), 0.995 - float(cfg["x_length"]))
        cfg["bottom"] = min(max(0.02, bottom), 0.995 - float(cfg["y_length"]))
        self.apply_frame(cfg)
        return True

    def _axis_hit(self, event):
        """Which axis region (tick labels / axis label) was clicked?"""
        if event.x is None or event.y is None:
            return None
        box = self.ax.get_window_extent()
        if box.x0 <= event.x <= box.x1:
            if self.x_side == "top":
                if box.y1 < event.y <= box.y1 + 80:
                    return "x"
            elif box.y0 - 80 <= event.y < box.y0:
                return "x"
        if box.y0 <= event.y <= box.y1:
            if box.x0 - 90 <= event.x < box.x0 and self.left_axis_shown():
                return "y"
            if self.right_axis_active() and box.x1 < event.x <= box.x1 + 90:
                return "y2"
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

        def set_plot_style(st):
            if column is not None:
                self.series_style[column] = st
                self.refresh_series_visuals(column)
                # a histogram carries its own counts: the range follows
                self._rescale()

        def set_bar_cfg(cfg):
            if column is not None:
                self.bar_cfg[column] = cfg
                self.refresh_series_visuals(column)

        def set_histogram_cfg(cfg):
            if column is None:
                return
            before = self.histogram_bins(column)
            self.histogram_cfg[column] = cfg
            self.refresh_series_visuals(column)
            if before != self.histogram_bins(column):
                self._rescale()      # other bins, other counts and range

        def set_stairs_cfg(cfg):
            if column is not None:
                self.stairs_cfg[column] = cfg
                self.refresh_series_visuals(column)
                self._rescale()      # other edges, other range

        def set_hist2d_cfg(cfg):
            if column is not None:
                self.hist2d_cfg[column] = cfg
                self.refresh_series_visuals(column)

        def set_pie_cfg(cfg):
            if column is not None:
                self.pie_cfg[column] = cfg
                self.refresh_series_visuals(column)

        def set_error_cfg(cfg):
            if column is not None:
                self.error_cfg[column] = cfg
                self.refresh_series_visuals(column)

        cols = list(self.df.columns)
        return self._show_dialog(id(line), lambda: SeriesStyleDialog(
            self, line,
            on_change=lambda: (self.refresh_series_visuals(column), self.refresh_legend(), self.draw()),
            on_close=lambda _d: self._dialogs.pop(id(line), None),
            legend_size=state.get("size", self.fonts["legend"]),
            legend_color=state.get("color", self.fonts["legend_color"]),
            on_legend_style=set_legend_style,
            fill=self.fill_state.get(column),
            on_fill=set_fill,
            plot_style=self.series_style.get(column, self.plot_style),
            on_plot_style=set_plot_style,
            bar_cfg=self.bar_cfg.get(column),
            on_bar_cfg=set_bar_cfg,
            histogram_cfg=self.histogram_cfg.get(column),
            on_histogram_cfg=set_histogram_cfg,
            stairs_cfg=self.stairs_cfg.get(column),
            on_stairs_cfg=set_stairs_cfg,
            hist2d_cfg=self.hist2d_cfg.get(column),
            on_hist2d_cfg=set_hist2d_cfg,
            pie_cfg=self.pie_cfg.get(column),
            on_pie_cfg=set_pie_cfg,
            error_cfg=self.error_cfg.get(column),
            on_error_cfg=set_error_cfg,
            available_columns=cols))

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
            self, f"{AXIS_NAMES.get(which, which.upper())} label",
            self.axis_label(which),
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

The main window holds the data table.  The first column is normally the
independent variable (the X axis); every further column is drawn as a
separate curve.  Two cases do without an X column: a **histogram** counts
every column as a sample of raw values, and a sheet whose **first column is
the only filled one** draws that column against the **row numbers**.

### Toolbar

| Button | What it does |
| --- | --- |
| Plot (Split button) | Clicking the main button opens a NEW diagram with the active plotting style. Clicking the dropdown arrow opens the style menu to choose among 9 styles. |
| Update plot | Sends the current data to the diagrams that are already open, keeping every style setting. |
| Add row (icon, split button) | Inserts an empty row **around the selected cell** and starts editing it. The arrow chooses the place: above, below, or at the end of the sheet. |
| Delete row (icon) | Deletes every row the highlighted block touches. |
| Add column (icon, split button) | Asks for a name and inserts an empty column **around the selected cell**. The arrow chooses: before, after, or at the right end of the sheet. |
| Delete column (icon) | Deletes the column of the selected cell (after a confirmation). |
| Settings... | Opens the settings editor (see section 4). |

Clearing, copying and pasting cells are done with the keys (`Delete`,
`Ctrl/Cmd+C`, `Ctrl/Cmd+V`, `Ctrl/Cmd+X`), and `Random data` is in the
`File` menu.

### The row and column icons

The four row and column tools are **coloured icons**, drawn in the same
style as the `T`, shape and arrow buttons of the diagram window.  Each one
is a tiny picture of a sheet of three bands - lying down for the rows,
standing up for the columns - and the band that is painted shows exactly
what will happen:

* **Blue adds.**  The blue band is the new row or column, drawn where it
  will appear: at the top or the bottom of the little sheet for a row,
  at the left or the right for a column.  A band standing **apart** from
  the other two means the far end of the whole sheet.  A blue `⊕` marks
  the button as one that adds something.
* **Red deletes.**  The red band in the middle is the row or column that
  goes away, and the red `⊗` says that something is removed.

Resting the pointer on any of them brings a **popup text** that spells the
operation out in words - *"Add row: inserts an empty row below the selected
cell (the arrow chooses the place)"*, *"Delete column: removes the column of
the selected cell, with its data"*, and so on.  The text follows the place
that is chosen, so the button always says what it is about to do.

**Adding around the selected cell.**  The two adding icons are **split
buttons**, like `Plot`:

* **Clicking the icon** inserts the row or column at the place the icon
  shows, measured from the **selected cell** (or from the highlighted
  block).  A new row pushes the rows below it down, a new column pushes
  the columns on its right to the right, and the formulas of those cells
  move with them - **references and all**, see below.
* **Clicking the arrow** opens the three places.  Choosing one does it
  right away **and** becomes the new default of the icon, so the next
  click repeats it.

| Place | Where the new row / column goes |
| --- | --- |
| Above / Before | Directly above the selected row, or directly to the left of the selected column. |
| Below / After | Directly below the selected row, or directly to the right of the selected column (the default). |
| At the end | The bottom of the sheet, or its right hand end - the old behaviour. |

A column inserted **before the first one** becomes the new X column: the
`x_B` / `x_T` check buttons move to it and the old first column becomes a
curve.  The same tools sit in the right click menus as well: `Insert Row
Above` / `Insert Row Below` on a cell, and `Insert Column Before...` /
`Insert Column After...` on a column heading.

### Plotting styles (Plot Split Button)

The **Plot** button in the main window toolbar is a split button that combines
an immediate action with a style menu:

* **Clicking the main button** opens a new diagram drawn with whichever style is
  currently active (indicated by its vector icon on the button face).
* **Clicking the dropdown arrow** opens the menu of all **6 plotting styles**:
  * **Line + Symbol**: A smooth or solid line connecting data points, with
    distinct marker symbols (circles, squares, diamonds, etc.).
  * **Line**: Clean continuous lines without markers, ideal for dense time
    series, spectra, and continuous functions.
  * **Scatter**: Discrete data markers without connecting lines (crosses `x`,
    plus signs `+`, circles, squares, etc.), ideal for point clouds and
    uncorrelated samples.
  * **Bar Chart**: Vertical rectangular bars for categorical, discrete, or
    binned data. Bar width, fill opacity (alpha), edge line width, and colors
    can be customized in Curve Properties.
  * **Error Bar**: Data points with vertical error bars and horizontal end caps.
    Error bounds can be calculated automatically (as a percentage, a fixed
    value, or standard deviation) or driven directly from a separate column in
    the spreadsheet table.
  * **Histogram**: The distribution of a column of raw values, counted by
    the diagram itself into a given number of bins (20 by default, set per
    curve in `Curve properties`). Every column is a sample of its own, and
    one single column is enough.
  * **Stairs**: A stepped outline of the values (`ax.stairs`) - one flat
    tread per point instead of a straight line between two of them. The
    step may stand midway between two X values, at the X value itself or
    just before it, and the staircase can be left open or filled with a
    colour and a pattern.
  * **2D Histogram**: The X/Y **pairs** counted in a grid of cells
    (`ax.hist2d`): where the points crowd together the cell is brighter.
    The number of bins across X and up Y, the colour scale, the opacity and
    an optional colour bar are all settings of the curve.
  * **Pie Chart**: The values of **one** column as slices of a circle
    (`ax.pie`). The first column of the table names the slices, the
    percentages can be written on them, and the pie may be turned, pulled
    apart or opened into a doughnut.

Selecting a style updates the button icon and immediately opens a diagram
rendered in that style. Any curve's style can also be switched individually at
any time from the **Curve properties** dialog.

### The formula bar and Excel-like operations

Directly above the table sits the **Formula Bar**, giving APlot full spreadsheet
capabilities similar to Excel:

* **Cell Address Box** (left): Displays the coordinate of the currently focused
  cell (e.g., `A1`, `B3`). You can type any valid cell reference here and press
  `Enter` to jump straight to that cell.
* **fx Symbol**: Indicates formula entry mode.
* **Formula / Value Entry**: Displays and edits either the raw formula (starting
  with `=`) or the plain text value of the active cell.
* **Commit (`✓`) button**: Confirms and saves the formula or value (`Enter`).
* **Cancel (`✕`) button**: Discards edits and restores previous content (`Esc`).

The bar carries nothing else: **filling down** and the **column operations**
live where they are needed and do not take room above the sheet.

* **Fill down**: `Ctrl/Cmd+D`, the black fill handle of the selection, or
  `Fill Down` in the right click menu of a cell or a heading.  It copies the
  top cell's formula or value down across the selected block of rows,
  automatically adjusting relative row references (e.g. `=A1+B1` becomes
  `=A2+B2`, `=A3+B3`) while preserving absolute references (e.g. `$A$1`).
  Pulled with the **black square**, two selected numbers make a series
  instead of a copy - see `Pulling a series out of two numbers` below.
* **Column Math**: `Column Math...` in the right click menu of a cell, or
  `Calculate Column '<name>'...` in the right click menu of a heading.  It
  calculates entire columns at once using presets or mathematical formulas.

### Excel-style cell fill handle and row/column numbering

* **Interactive Fill Handle (black square)**:
  * When any cell or block of cells is selected, a solid black square handle appears at the bottom-right corner of the selection outline.
  * **Click and Drag Down**: Pulling the black square down carries the
    selection on across the rows below, with a real-time feedback outline,
    and computes the results at once.  What is written depends on what was
    selected - a **series**, a **formula** or a **copy**; see the next
    section.
  * **Option+Double-Click / Double-Click**: Double-clicking the fill handle (or pressing `Option`/`Alt` while double-clicking) automatically fills down all rows until the adjacent left or right column has empty cells, exactly like Microsoft Excel - and if there is no neighbouring column with data, down to the last row of the sheet.
  * The handle is always **on top of the cell editor**, so it can be grabbed
    at once - also right after walking to the cell with the arrow keys,
    while the cell is still open for typing.

#### Pulling a series out of two numbers

Selecting **two or more cells** of a column before pulling the black square
turns the fill handle into a **series generator**: the step is worked out
from the numbers themselves and the series is continued for as many rows as
the handle is pulled over.

| Selected | Pulled down |
| --- | --- |
| `1` | `1, 1, 1, 1, ...` - one cell alone is copied, as before |
| `1`, `3` | `5, 7, 9, 11, ...` - the difference is the step |
| `10`, `8` | `6, 4, 2, 0, -2, ...` - a falling series counts down |
| `0.5`, `0.75` | `1.0, 1.25, 1.5, ...` - fractions are exact |
| `2`, `4`, `6` | `8, 10, 12, ...` - three or more cells work as well |

* The step of **two** cells is simply their difference.  With **more** than
  two it is their **average** difference, so an evenly spaced selection is
  continued exactly and an uneven one carries on from the last value with
  the average step.
* **`Option`/`Alt`+double click** (or a plain double click) on the black
  square writes the series all the way down: to the end of the data in the
  neighbouring column, or to the last row of the sheet if there is none.
* Every **column** of the selection decides for itself, so a block of two
  rows and three columns pulled down gives three series with three
  different steps.
* Whole numbers stay whole (`1, 3, 5`, never `1.0, 3.0, 5.0`).
* Anything that is **not a plain number** - a text, an empty cell - is
  copied, exactly as it was before, and a **formula** is still replicated
  with its row references moved along (`=A1*10` becomes `=A2*10`,
  `=A3*10`, ...).
* While the handle is being pulled, the **status bar** at the bottom says
  what will be written: *"Series, step 2:  5, 7, 9, ...   (7 rows)"* or
  *"Fill down: the value is copied into 3 more rows"*.
* **Column Letters (A, B, C, ..., AA, AB, ...)**:
  * Displayed directly below the axis selection checkboxes in the axis check bar.
  * Also displayed in the column table headers (e.g. `A  (Time)`, `B  (Voltage)`).
  * **Clicking a letter selects that whole column**, exactly the way clicking
    a row number selects the whole row - see below.
* **Row Line Numbers (1, 2, 3, ...)**:
  * Displayed in a fixed left-side header column, painted with the very
    background of the table itself, so the strip of numbers never stands
    out against the cells (the themes of the systems differ - the one of
    macOS is a dark grey).
  * Stays pinned on the left when scrolling horizontally, while scrolling vertically in lockstep with the spreadsheet table data.
  * Clicking or dragging along row numbers selects full rows.
  * Clicking the top-left corner indicator (`◢`) selects all cells in the spreadsheet.

#### Selecting a whole column or a whole row from its heading

The letters above the columns and the numbers beside the rows work the same
way, so a whole line of the table is always one click away:

| Click | What is selected |
| --- | --- |
| a column letter (`A`, `B`, `C`, ...) | that **whole column**, from the first row to the last |
| a row number (`1`, `2`, `3`, ...) | that **whole row**, from the first column to the last |
| the corner (`◢`) | the **whole table** |

* **Dragging** along the letters (or along the numbers) takes a **range** of
  columns (or rows), and it may be dragged in either direction.
* **`Shift`+clicking** another letter stretches the block from the one that
  was clicked first to that one.
* The letter of every column the block touches is **tinted**, just as the
  numbers of the rows it touches are - so it is always visible what the
  block covers, even where it has scrolled out of sight.
* What is selected is an ordinary block, so everything works on it:
  `Ctrl/Cmd+C` copies the column, `Delete` empties it, `Ctrl/Cmd+D` fills it
  down, and the arrow keys walk on from the cell the click left the cursor
  in.  `Ctrl/Cmd+Space` does the same thing from the keyboard.
* **Right clicking** a letter opens the menu of that column -
  `Calculate Column...`, `Sort`, `Insert Column Before / After...`,
  `Rename...`, `Delete Column` - the same menu as a right click on the
  column heading itself.

#### Formula syntax and functions

Formulas begin with an equals sign (`=`). Standard Excel cell coordinates (e.g.
`A1`, `B2`), absolute coordinates (`$A$1`, `A$1`, `$A1`), and ranges (`A1:A10`,
`B2:D10`) are fully supported:

* **Arithmetic**: `+`, `-`, `*`, `/`, `^` (exponentiation), `%`.
* **Comparisons**: `=`, `<>`, `<`, `<=`, `>`, `>=`.
* **Math & Statistics**: `SUM(range)`, `AVERAGE(range)` / `AVG(range)`,
  `COUNT(range)`, `MIN(...)`, `MAX(...)`, `ABS(x)`, `ROUND(x, decimals)`,
  `INT(x)`, `SQRT(x)`, `POWER(base, exp)`, `EXP(x)`, `LN(x)` / `LOG(x)`,
  `LOG10(x)`, `LOG2(x)`, `MOD(n, d)`.  A function whose name ends in digits
  is read as a function, never as a cell (`LOG10(A1)` is the base-10
  logarithm of `A1`, not the cell `LOG10`).
* **Trigonometry**: `SIN(x)`, `COS(x)`, `TAN(x)`, `ASIN(x)`, `ACOS(x)`,
  `ATAN(x)`, `DEGREES(rad)`, `RADIANS(deg)`, `PI()`.
* **Constants**: `pi`, `e` and `tau` are numbers on their own, so they can be
  written straight into an expression - `=sin((B1+C1)+pi/6)`, `=2*pi*A1`,
  `=B1/e`. `PI()` and `E()` still work as functions as well. A column that
  really carries one of these names (or, for `e`, a sheet wide enough for a
  column `E`) keeps its own meaning: the column always wins over the constant.
* **Logic**: `IF(condition, value_if_true, value_if_false)`, `AND(c1, c2)`,
  `OR(c1, c2)`, `NOT(c)`.

#### Error reporting and safety

Formulas are evaluated using an AST-based calculation engine with cycle
detection. When an invalid expression or calculation issue occurs, Excel-style
error codes are displayed:

* `#DIV/0!`: Division by zero.
* `#NAME?`: Unrecognized function or variable name.
* `#CYCLE!`: Circular dependency detected between cells (e.g., `A1` depends on
  `B1` which depends back on `A1`).
* `#REF!`: A cell reference outside the table - or one whose row or column
  has been deleted.
* `#VALUE!`: Incompatible operand types.

#### The formulas follow the rows and columns that move

A formula does not only live in a cell, it also **points** at cells, and
inserting or deleting rows and columns moves both.  Every stored formula of
the sheet is rewritten so that it goes on saying what it said before:

* **Inserting a row** above row 14 turns `=log(A14)/log(10)` into
  `=log(A15)/log(10)` - in the formula that moved down with that row and in
  every other formula that referred to it.  A reference to a row **above**
  the new one is left alone.
* **Deleting rows** moves the references of the rows below them **up** by as
  many rows as were removed; a reference to a row that is **gone** becomes
  `#REF!`, so a broken calculation says so instead of quietly reading the
  wrong cell.
* **Inserting a column** in front of another shifts the letters: `=A1*100`
  becomes `=B1*100`.  **Deleting** one shifts them back, and a reference to
  the deleted column becomes `#REF!` as well.
* Ranges move with everything else, so a new row inside `=SUM(A1:A5)` makes
  it `=SUM(A1:A6)`.
* This is what a spreadsheet does, and unlike **pulling a formula down**
  (where `$A$1` stays put on purpose), a **fixed** reference moves here too:
  `$A$14` becomes `$A$15`, because it is the values themselves that moved.
* Whole columns of calculated cells therefore survive editing: pull
  `=log(A1)/log(10)` down over a thousand rows, insert or delete rows
  anywhere, and every cell still reads the value beside it.

#### Status bar summary

Whenever a block of cells is selected in the table, the status bar at the bottom
of the window immediately shows a live statistical summary of the numeric
cells:

> `Average: 24.50   Count: 12   Sum: 294.00   Min: 10.00   Max: 45.00`

#### Right-click context menus

Right-clicking inside the table opens a context menu:
* On any **cell**: `Cut`, `Copy`, `Paste`, `Clear Cells`, `Fill Down`,
  `Column Math...`, `Insert Row Above`, `Insert Row Below`, `Delete Row(s)`.
* On any **column header**: `Calculate Column '<name>'...`, `Sort Ascending`,
  `Sort Descending`, `Fill Down`, `Insert Column Before...`,
  `Insert Column After...`, `Rename '<name>'...`, `Delete Column '<name>'`.

### Column Math dialog

The **Column Math** dialog (`Column Math...` in the right click menu of a
cell, or `Calculate Column '<name>'...` on a column heading) lets you
compute entire columns quickly without
having to drag formulas across every row:

* **Target column**: Choose an existing column to overwrite, or select `[New Column]`
  to create a new one automatically.
* **Presets**:
  * **Scale and Offset**: `a * x + b` (e.g., multiply by a gain factor and add a bias).
  * **Normalize**: Rescales values linearly into the range `[0, 1]`.
  * **Standardize (z-score)**: Subtracts the mean and divides by standard deviation:
    `(x - mean) / std`.
  * **Subtract Mean**: Centers the column around zero: `x - mean(x)`.
  * **Cumulative Sum**: Running sum down the column: `cumsum(x)`.
  * **Difference / Gradient**: Numerical derivative: `diff(x)`.
  * **Moving Average / Smooth**: Rolling window mean: `smooth(x, window=5)`.
  * **Linspace / Index**: Evenly spaced numbers or row index sequence:
    `linspace(0, 100)`.
* **Custom Expressions**: Write any algebraic expression referencing column
  names or letters directly (e.g., `A * 2 + B` or `col('Y1') / 1000`).

### What the columns mean

**Every** diagram reads the table the same way: the **first column is the X
axis** and the **second one is the value** of the first curve.  What follows
depends on the kind of diagram:

| Diagram | The columns |
| --- | --- |
| Line + Symbol, Line, Scatter, Bar Chart | `x`, `y1`, `y2`, `y3`, ... - one curve per column |
| Error Bar | `x`, `mean1`, `std1`, `mean2`, `std2`, ... - **in pairs** |
| Histogram | **every** column on its own: a sample of raw values that the diagram counts itself |
| Only the first column filled | that column is the **curve** and the X axis is the **row number** |

An **error bar** diagram therefore reads the columns two by two: the third
column is the length of the error bar of the second one, the fifth belongs
to the fourth, and so on.  Five columns give **two** curves with their own
error bars, seven columns give three, and so on.  The `std` columns are used
up as the errors and are not drawn as curves of their own, so every one of
them has to stay ticked in the strip above the table.  A last `mean` column
with no `std` beside it still gets a curve (with a 5 % error, which can be
changed in `Curve properties`).

A **histogram** is the one diagram that does not read the first column as an
X axis, because it does not need one.  Each column is a **sample of raw
measurements** and the diagram makes the statistics itself, exactly as
`ax.hist` does: the range the values of that column cover is cut into
**bins** of equal width and the values are counted.  The X axis is then the
value of the measurement and the Y axis is how many of them fell into each
bin.

* **One column is enough.**  A thousand numbers in the first column alone
  give a histogram straight away - no second column, no counting by hand.
* **Every filled column gets its own histogram**, the first one included,
  and each of them is counted separately over its own range.  A column that
  is empty (or ticked off in the strip above the table) is simply left out.
* **The number of bins is 20 by default** and belongs to the curve: open
  `Curve properties` (double click the bars) and set `Bins` in the
  **Histogram properties** section.  The sample is counted again at once and
  the range follows.  Every histogram can have a different number of bins.
* Empty cells and text are not measurements, so they are left out of the
  counting: only the numbers are counted.
* The bars are exactly as wide as a bin, so they stand side by side with no
  gap, and the counts start at zero.

Bins that are already counted in the table (one row per bar, `x` = the
position of the bar and `y` = its height) are a **bar chart**, not a
histogram - that is what the `Bar Chart` style is for.

### One single column: the row number is the X axis

A column of numbers on its own is a **series of measurements**, not an X
axis, so it does not need a second column to be plotted:

* Type (or load) values into the **first column only** and press `Plot`:
  that column becomes the curve and the X axis becomes the **row number of
  the table** - `1` for the first row, `2` for the second, exactly the
  numbers standing beside the cells.  The X axis is called `Row`.
* It works for **every style**: line, line with symbols, scatter, bar chart
  and error bar all draw the values against the row numbers.  (A histogram
  needs no X axis at all: it counts that column, see above.)
* The other columns of the sheet may be there as long as they are **empty** -
  the blank columns a fresh sheet fills the window with change nothing.
* As soon as a **second column is filled**, the first one goes back to being
  the X axis and the diagram is drawn against it - and the label of the X
  axis follows, unless a text was written into it by hand.
* Empty cells stay **gaps**: the row numbering keeps counting, and the curve
  is simply broken at the missing point.
* This is a fallback for a sheet that has nothing else, not a way around the
  check buttons: if a filled column was **switched off** on purpose, the
  program asks for a tick instead of quietly drawing the first column alone.

### Which columns are plotted, and against which axis

Above the column headings there is a strip with **two check buttons for
every column**, side by side:

| Above | The two boxes | What they mean |
| --- | --- | --- |
| the first column | `x_B` and `x_T` | the **bottom** and the **top** X axis |
| every other column | `y_L` and `y_R` | the **left** and the **right** Y axis |

Resting the pointer on any of them pops up its full name - `Bottom x-axis`,
`Top x-axis`, `Left y-axis`, `Right y-axis` - so the short labels never have
to be guessed.  A column is never made **narrower than its two check
buttons**: pulling the window in stops there and the horizontal scroll bar
takes over, so neither the switches nor the numbers under them can be
squeezed out of sight.  `Settings > Spreadsheet > Column width` sets the
starting width; anything smaller than that minimum is raised to it.

The rules are simple:

* **one axis per column.**  Ticking one of the two boxes clears the other
  one, so a column is never drawn against both axes at once.
* the **first column** always feeds one of the two X axes: `x_B` is ticked
  when the data arrives, and clicking `x_T` moves the whole X scale - its
  numbers and its label - **above** the plot area.  Clicking the ticked box
  does not switch it off; the data has to have an X axis.  In a
  **histogram** that column is a sample like any other and is counted as
  well, while its `x_B` / `x_T` tick still decides whether the value scale
  is drawn below or above the bars.
* every **other column** may have **both boxes empty**: then that column is
  simply not plotted.  The data stays in the table, it is only left out of
  the diagram.
* ticking `y_R` gives that curve **its own scale on the right**, with its
  own range, its own numbers and its own label.  This is what makes two
  quantities of completely different size - per cent and counts, degrees and
  volts - readable in one diagram.
* `Plot` opens a diagram of the ticked columns, and `Update plot` follows
  every change: a column that was unticked disappears, one that is ticked
  again comes back, and moving a tick from `y_L` to `y_R` **moves that curve
  to the other scale** while it keeps its colour, its line style and its
  legend box.
* with nothing ticked the program says so instead of drawing an empty
  diagram - as long as there really is a filled column that was switched
  off.  **One single filled column** needs no tick of its own: it is drawn
  against the row numbers (or counted, in a histogram).
* the ticks are kept while the table is edited (adding rows, renaming a
  column, adding a column - a new column starts on `y_L`) and are reset to
  the first axis of every column whenever new data is loaded.

The colours are handed out per curve, not per axis, so the first curve on
the right is **not** painted in the same colour as the first one on the
left.

A saved `.aplt` file always contains the **whole** table, and the diagrams
in it keep exactly the curves they had when they were saved, each one on
the axis it was drawn against.

### How many columns there are

The **blank sheet the program starts with** is filled with as many columns
as the window can show: the names from
`Settings > Spreadsheet > Column names` come first (`X`, `Y1`, ...) and the
rest are added as `Y2`, `Y3`, ... until the width of the window is used up.

* **Widening the window brings more columns**, one for every column width
  that fits.
* **Narrowing it keeps every column** that is there and lets the horizontal
  scroll bar take over, so nothing can be lost by making the window small.
* As soon as **one value is typed** into the sheet - or a data file is
  loaded - the columns stop appearing by themselves: from then on the table
  is your data and only `Add column` changes its shape.
* A sheet that is emptied again (a fresh start) fills the window again.

`Add column` and `Delete column` work at any time, and a column that is
empty from top to bottom is simply not plotted, so a few spare columns cost
nothing.

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
* Text can be selected **with the pointer**: press in the cell and drag
  across the characters - the editor opens with the press, so the drag
  highlights exactly the part you sweep over (leaving the cell during the
  drag selects a block of cells instead).  A plain click selects the whole
  text, a double click a word.
* While a block is dragged out, holding the pointer at the bottom (or the
  top, or a side) of the table keeps scrolling it row by row, and the block
  follows - the selection is not limited to what is on the screen.
* `Shift+Left/Right` extend the selection inside the cell, `Ctrl+A`
  (`Cmd+A` on macOS) selects the whole text of the cell and `Ctrl+C`
  (`Cmd+C`) copies it.
* `Esc` closes the editor and leaves the keyboard on the table itself,
  where the arrow keys walk from cell to cell.

Values that look like numbers are stored as numbers; everything else is
kept as text and is ignored when plotting.

### Selecting several rows and columns

The table always has a **highlighted block** of cells, marked by a blue
rectangle around it.  It can be one cell or a whole rectangle of rows and
columns.  Rows are **tinted** light blue only when the block covers every
column of them - that is, when whole rows were selected on purpose (with
`Shift+Space`, `Ctrl/Cmd+A`, or by taking the selection across all the
columns).  Clicking or editing a single cell marks that cell alone and
leaves its row quiet.

| Action | What happens |
| --- | --- |
| Click a cell | That cell alone is the block, and it is opened for editing. |
| Drag with the pointer | Inside the pressed cell it highlights its text; leaving that cell it selects the block between the pressed and the released cell.  Dragging to the edge of the table **scrolls it on** as long as the pointer stays there, so rows and columns below or beside the window can be selected as well. |
| `Shift`+click a cell | Stretches the block from where it started to that cell. |
| Click a column letter (`A`, `B`, ...) | Selects that **whole column**; dragging along the letters takes a range of them, and `Shift`+click stretches the block. |
| Click a row number (`1`, `2`, ...) | Selects that **whole row**; dragging along the numbers takes a range of them. |
| Click the corner (`◢`) | The whole table. |
| `Shift`+click a heading | Selects that whole column. |
| `Shift`+arrow keys | One row or column more (or less) in the block - this also works while a cell is being edited, where `Shift+Up/Down` leaves the editor at once and `Shift+Left/Right` first select the text of the cell. |
| Arrow keys (no Shift) | Walk from cell to cell; the block collapses to that one cell. |
| `Shift+Space` | The whole rows the block touches (they become tinted). |
| `Ctrl/Cmd+Space` | The whole columns the block touches. |
| `Ctrl/Cmd+A` | The whole table. |
| `Enter` or `F2` | Opens the cell under the cursor for editing. |

The open cell always carries a **blinking blue cursor** and always has the
keyboard, even when a diagram window was the one in front a moment before
(after a graph was opened, for instance): the cell takes the keyboard back
for itself, and a diagram window never takes it away from a cell that is
being edited.  Clicking in the diagram, as always, gives the keyboard back
to the diagram.

The block is what the data operations work on:

| Keys | What happens |
| --- | --- |
| `Ctrl/Cmd+C` | Copies the block as tab separated text - several rows and columns at once, ready for a spreadsheet program. |
| `Ctrl/Cmd+V` | Writes tab separated text (from this program or another one) into the table, starting at the **top left cell of the block**; the shape of the text decides the shape of what is written, so a block of two columns fills two columns even when only one cell is selected.  The table grows if the text has more rows.  This also works while a cell is being edited - only a single value (no tabs, no line breaks) is pasted into the text of that cell. |
| `Ctrl/Cmd+X` | Copies the block and empties it (inside a cell editor it cuts the selected text instead). |
| `Delete` or `Backspace` | Empties the cells of the block. |
| `Delete row` button | Removes every row of the block. |

**Copying carries the values, not the formulas.**  What goes on the
clipboard is what the cells **show**: copying a calculated column and
pasting it somewhere else gives the numbers there, not the expressions
behind them.  That is what makes it possible to hand a result to another
program, or to freeze a calculated column into plain data.

**An emptied cell is really empty.**  A cell that is **cut**, **cleared**
(`Delete`) or **written over** with a pasted value loses the formula that
stood in it, together with its value: it is not a calculated cell any more.
Every other formula of the sheet is then worked out again at once, so a
formula that read one of those cells shows its new result immediately.

### Leaving a gap in a curve

An **empty cell is a gap, not a zero**: the curve is cut there instead of
being drawn straight across the missing point.  So a range of data can be
plotted in pieces:

1. select the cells that should not be plotted - a block, a whole row, or
   parts of a few columns,
2. press `Delete` (or `Clear cells` in the toolbar),
3. press `Update plot`.

Every curve whose cells were emptied is now drawn in two (or more) separate
pieces, with the markers of the remaining points where they belong.  Filling
the cells again joins the curve back together.

Nothing is thrown away and nothing is bridged: an empty cell in the Y
column, an empty cell in the X column and a **completely empty row** all
break the curve at that place.  So simply leaving a row empty in the middle
of the data is enough to cut the curve in two.

The only case with no curve at all is a column that is empty from top to
bottom.

### Column names

Click a column heading to edit its name.  The name is used

* as the legend text of that curve, and
* for the first column, as the label of the X axis.

Renaming a column later also renames the legend entry and the X axis label
of every open diagram - unless you gave them your own text, which is never
overwritten.  When the first column is drawn as a curve of its own (a
histogram, or a single filled column against the row numbers), renaming it
renames that curve and its legend box as well.


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
| Drag a control point | Resizes a drawing, moves the tip or the tail of an arrow or of a line, or makes an axis longer or shorter. |
| Drag the round control point above a drawing or a text box | Turns it around its centre (a text box around its own anchor); `Shift` keeps 15 degree steps.  A line has no such point: its two ends give the direction. |
| Arrow keys | Move the selected object by one pixel, with `Shift` by ten. |
| `Ctrl/Cmd+C`, `Ctrl/Cmd+V` | Copies the selected text box, drawing or arrow with all of its properties and pastes another copy of it. |
| `Delete` / `Backspace` | Removes the selected text box, drawing or arrow. |
| Click an axis line (the frame) | Selects that axis: a control point appears on each of its two ends. |
| Drag one of those two points | Makes that axis longer or shorter - the other end stays where it is. |
| Click the selected axis line again | Frame and origin settings. |
| Click twice beside an axis (on the numbers or the label) | Axes properties, opened on the tab of that axis. |
| Hold Shift while drawing or resizing an arrow or a line | Keeps it horizontal, vertical or at 45, 135, 225, 315 degrees. |
| Plot menu | The axes dialog (axes, frame and origin), the title/fonts dialog, copy, paste and delete of the selected object, plus closing this diagram. |
| Toolbar | The standard Matplotlib toolbar (pan, zoom, saving the figure as an image), the **T** button that adds a text box, the drawing tool and the arrow tool. |

The blue veil and the control points are only on the screen: they are left
out of the image that the save button of the toolbar writes.

### Drawing rectangles, triangles, circles, ellipses and lines

The button next to **T** is the drawing tool.  Its icon shows the shape
that will be drawn, with a small arrow in its lower right corner:

* clicking the **icon** starts drawing with the shape that is shown (a
  rectangle at the first start, later whatever was used last),
* clicking the **arrow** opens the list `Rectangle`, `Triangle`, `Circle`,
  `Ellipse`, `Line`; after choosing one the tool is armed with it and the
  icon changes to that shape.

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
* a **second click** opens its **properties**, where the name of the `Line`
  and of the `Fill` section is its own **check button**: switched off, that
  part of the object is simply not drawn (so the style lists have no "None"
  entry, and the settings are remembered while a section is off).  The
  sections hold the line style (solid, dashed, dash-dot, dotted), the line
  thickness and colour, the fill colour with an opacity, the rotation, and
  a `Delete` button,
* clicking an empty part of the diagram deselects it,
* a circle keeps its round shape: its height follows its width and the
  proportions of the plot area,
* a **line** is drawn between the two points of the drag and is clicked on
  the stroke itself, not anywhere in its bounding box.  It behaves like an
  arrow: it has **two control points**, one on each end, dragging either of
  them changes the length and the direction, and holding **Shift** while
  drawing it or while dragging an end keeps it at 45 degree steps (exactly
  horizontal, vertical or diagonal).  It has no fill and no rotation of its
  own, so its property window has only the `Line` section,
* it can be **turned** to any angle: see below.

The positions and sizes are kept in the coordinates of the plot area, so
the objects follow the diagram when the window is resized, and they are
stored in `.aplt` files.  The starting line and fill of new objects come
from the `Drawings` tab of the settings.

### The second Y axis and the top X axis

The `y_R` and `x_T` check buttons of the spreadsheet (see `Which columns are
plotted, and against which axis`) give the diagram two more axes:

* the **right hand Y axis** is a scale of its own.  It appears as soon as a
  curve is drawn against it and goes away again when the last such curve is
  unticked.  It has its own range, its own numbers, its own label and its
  own automatic scaling, so a curve of a few tenths and one of tens of
  thousands can share a diagram and both be readable.
* the **top X axis** is the same X scale drawn above the plot area instead
  of below it: the numbers and the axis label move up together, and with
  `No frame` the line above the plot area is the one that is drawn while
  the one below it stays away.

Everything else works exactly as on the two original axes:

* `Axes properties` grows a **`Right Y axis`** page next to `X axis` and
  `Y axis` whenever the right axis is in use - range, step, minor ticks,
  label, fonts, colours and distances, all of it separately from the left
  axis.  Its grid is left to the main axes, so no line is drawn twice.
* a **double click** next to the right hand numbers opens that page, just
  as a double click under the X numbers opens the `X axis` page; with `x_T`
  the X region is above the plot area instead of below it.
* the **right axis label** is a text like any other: one click selects it
  (blue veil), a slow second click rewrites it in place, a double click
  opens its dialog, and the arrow keys move it.
* a **filled area** under a curve on the right is filled on the right hand
  scale, and `Fill down to the bottom of the axes` means the bottom of that
  scale.
* both new lines are **resized by the pointer** exactly like the two
  original ones: click the line, drag one of its two ends (see `Resizing
  the axes with the pointer`).
* the whole arrangement - which side the X axis is on and which curve
  belongs to which Y axis - is stored in `.aplt` files.  Files written by
  an older version load with everything on the bottom and the left, as
  before.

### Resizing the axes with the pointer

The plot area does not have to be sized in a dialog: **click any axis
line** and a small square control point appears on each of its two ends.
All four sides work, each with the points on its own line:

| Clicked line | Its two points | Dragging them |
| --- | --- | --- |
| bottom X axis | the lower two corners | the width |
| top X axis | the upper two corners | the width |
| left Y axis | the left two corners | the height |
| right Y axis | the right two corners | the height |

* The **horizontal** lines carry the width of the diagram: dragging the
  right point makes it wider or narrower and leaves the origin where it is,
  dragging the left one moves the origin and keeps the right end in place.
  The **vertical** lines work the same way upwards, with the height.
* So a diagram drawn against the **top X axis** and the **right Y axis** is
  sized exactly like any other one - by the two lines that are actually
  there.
* Only a line that is really **drawn** can be clicked, and a line that
  disappears (because the X axis moved to the other side, or the last curve
  of one Y axis was unticked) drops out of the selection by itself.
* The arrow keys move the **whole plot area** while an axis is selected
  (`Shift`: ten pixels), keeping its size.
* Everything in the diagram - the curves, the legend boxes, the text
  boxes, the drawings and the arrows - keeps its place inside the plot
  area and follows it.
* **Double clicking** an axis line opens `Frame and origin`, where the same
  numbers can be typed in fractions, centimetres or inches; the dialog
  always shows what the pointer has made.
* The size is kept in fractions of the window, so it survives a resize of
  the diagram window, and it is stored in `.aplt` files.

### Which frame lines are drawn

`Frame and origin` offers four frame styles.  `Full frame` and the two
`Frame with ticks` styles always draw **all four** lines, as before.
`No frame (X and Y only)` draws exactly the axes that are **in use**:

| In use | `No frame` draws |
| --- | --- |
| `x_B` + `y_L` | the bottom and the left line (the classical pair) |
| `x_T` + `y_R` | the top and the right line - and nothing else |
| `x_B` + `y_R` | the bottom and the right line; the left and the top stay away |
| `x_B` + `y_L` + `y_R` | the bottom line and **both** vertical lines |

An axis that carries no curve is not only left without a frame line: its
**numbers, tick marks and label disappear** as well, so a diagram whose
every curve is on the right hand scale has no empty left axis standing
next to it.  The Y **grid** follows the Y axis whose numbers are shown, so
it is drawn once, on the scale it belongs to.

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
  keeps the opposite corner exactly where it is (a line has two control
  points instead, one on each end),
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
| `Ctrl+C` / `Cmd+C` | The selected object goes to the clipboard with every one of its properties - and with **nothing** selected, a picture of the whole diagram. |
| `Ctrl+V` / `Cmd+V` | Another copy appears a little to the lower right of the original and is selected; each further paste steps further, so a series of copies does not pile up. |
| Left / Right / Up / Down | Moves the selected object by one pixel. |
| `Shift` + an arrow key | Moves it by ten pixels. |
| `Delete` or `Backspace` | Removes it. |

The same commands are in the `Plot` menu as `Copy object`, `Paste object`
and `Delete object`.

A text that is selected can also be **rewritten on the spot** with a slow
second click - see `Writing a text in place` below.

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

### Writing a text in place

The title, both axis labels, the legend boxes and the text boxes can be
rewritten **on the diagram itself**, without opening any dialog.  It works
exactly like renaming a file in the Finder of macOS or in a file manager:

1. **click** the text once - it is selected and turns blue,
2. **click it a second time**, slowly - about half a second to one and a
   half seconds after the first click, clearly slower than a double click,
3. a small white box appears over the text with a **blinking blue cursor
   where the pointer was**, and the text can be edited there,
4. `Enter` keeps the new text, `Esc` keeps the old one; clicking anywhere
   else also keeps what was written.

| Click | What happens |
| --- | --- |
| one click | selects the text (blue veil) |
| a second click within 1.5 seconds | writes the text in place |
| a double click (two fast clicks) | opens the property window |

So nothing is lost: the property window - with the font size, the colour,
the distance, the frame and the background - is still one double click
away, and the fast way of fixing a typo or a unit is the slow second click.

The cursor is a vertical line in the colour of the selection, as thick as
the text is big, and it blinks - so it can be found at a glance even in a
large title.  It is drawn by the program itself and not by the operating
system, so it stays visible in a dark desktop theme as well.

Moving the text is not disturbed either: the editor waits for the button to
be **released** on the same spot, so pressing on a selected text and
**dragging** it moves it, exactly as before.

While the little editor is open the arrow keys, `Delete`, `Ctrl/Cmd+C` and
`Ctrl/Cmd+V` belong to the **text**, not to the selected object, so the
text is edited the way any text field is edited.  `Shift+Enter` starts a
new line inside a text box.  Only the text is changed; the font size, the
colour, the position, the distance from the axis, the frame and the
background all stay as they were.

Two texts are special, in the same way as in their dialogs:

* writing **nothing** into a text box deletes that box,
* writing **nothing** into a legend box hides that legend, exactly as an
  empty text does in the legend dialog.

Drawings and arrows hold no text, so a second click on them does nothing -
they are simply selected.

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
* **click it a second time, slowly** to rewrite the text right there (see
  `Writing a text in place`), or **double click** it to open its dialog:
  text, font size, font colour, and the `Surrounding box` section - the name
  of that section is a **check button**, so switching it off leaves the
  frame away, while its colour and the background (a colour, or fully
  transparent) stay inside it,
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
click, so it only selects the text (it turns blue); a slow second click
writes the text in place (see `Writing a text in place`) and a double click
opens its dialog.  A selected label also moves with the arrow keys, one
pixel at a time, or ten with `Shift` - handy for the last bit of fine
tuning.

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
* Click the selected box a second time, slowly, to rewrite its text on the
  diagram itself (see `Writing a text in place`).
* **Double click** it to open its own dialog: the text, the font size and
  the font colour, the **frame** around the box (its colour, or no frame at
  all) and the **background** (its colour, or fully transparent).  An empty
  text hides the box.
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

At the top of the dialog, a **Plot Style** dropdown selector allows switching the
representation of any individual curve between all 9 styles: **Line + Symbol**,
**Line**, **Scatter**, **Bar Chart**, **Error Bar**, **Histogram**,
**Stairs**, **2D Histogram** and **Pie Chart**.  The dialog shows exactly
the sections that style can use, and nothing else:

| Style | Sections |
| --- | --- |
| Line + Symbol | Legend, Line, Marker, Fill under the curve |
| Line | Legend, Line, Fill under the curve |
| Scatter | Legend, Marker, Fill under the curve |
| Bar Chart | Legend, Bar properties |
| Error Bar | Legend, Marker, Line, Error bar properties |
| Histogram | Legend, Histogram properties |
| Stairs | Legend, Stairs properties |
| 2D Histogram | Legend, 2D histogram properties |
| Pie Chart | Legend, Pie properties |

The dialog sections each have **their own check button as the title**: switched
off, that part of the curve is simply not drawn.  The settings that belong
together share a line, and the sections share their column widths so everything
lines up cleanly.

* **Legend**: the `Text` of this curve's legend box, then its `Font size`
  with the `Colour` of the text next to it.  An empty text removes the box.
* **Line**: `Style` (solid, dashed, dash-dot, dotted), then `Width` with
  the `Colour` of the line next to it.
* **Marker**: `Hollow (no fill)` at the top of the section - an outlined
  marker has no fill colour at all - then `Style` (12 shapes), `Size` with
  `Fill colour` next to it, and `Edge width` with `Edge colour` next to it.
The **legend** of every kind of diagram shows what that diagram really
looks like in front of the text: a line with its marker for a curve, a
**coloured bar** for a bar chart and a histogram, a marker with an
**error bar** through it for an error bar plot, the **staircase** itself for
a stairs plot, one **slice** for a pie and a patch of the **colour scale**
for a 2D histogram.

* **Bar properties** (visible for Bar Charts):
  * `Width`: the width of the bars in X-axis data units.
  * `Opacity (0-1)`: transparency of the bar fill (0.0 transparent, 1.0 opaque).
  * `Edge width`: thickness of the bar outline.
  * `Bar colour` and `Edge colour`: independently selectable colours for the
    bar body and border.
  * `Pattern`: a hatching over the colour - the same choice a filled area
    has, which is what makes bars tell each other apart in a black and
    white print.
  * *Tip:* Clicking any bar directly inside the diagram window opens this dialog.
* **Histogram properties** (the same section, for Histograms): the bars of a
  histogram touch, so there is no width to set - the **number of bins** takes
  its place.
  * `Bins`: how many equal parts the range of the sample is cut into, `20`
    to begin with and anything from 1 to 1000.  Changing it counts the
    column again at once and the range follows the new counts.  Every
    histogram carries its own number of bins, and it is written into the
    `.aplt` file with the rest of the curve.
  * `Opacity (0-1)`, `Edge width`, `Bar colour`, `Edge colour` and
    `Pattern` work exactly as they do for a bar chart (the edges start out
    white, which is what separates bars that touch).
* **Error Bar properties** (visible for Error Bars):
  * `Source`: determines how error bars are calculated:
    * `Next column (x, mean, std)` **(default)**: the column standing right
      after this one holds the length of the error bars - see
      `What the columns mean` above.
    * `Percentage`: symmetric error computed as a percentage of the Y value (e.g. ±5%).
    * `Fixed value`: constant symmetric error across all points (e.g. ±0.5).
    * `Standard deviation`: column standard deviation used as uniform error bounds.
    * `From column`: select any other column from the table to specify individual error values for each row.
  * `Value / Column`: sets the percentage or fixed value, or selects the error column.
  * `Cap width`: width of the horizontal end caps.
  * `Line width`: thickness of the error bar stems.
  * `Cap thickness`: how thick the end caps themselves are drawn.
  * `Colour`: colour of the error bars.
  * *Tip:* Clicking on any error bar stem or horizontal cap directly opens this dialog.
* **Stairs properties** (visible for Stairs):
  * The **place of the step** (a list at the top): midway between two X
    values - every value is valid around its own X - or at the X value
    itself, with the step after it or before it.
  * `Line width` with the `Colour` of the staircase next to it.
  * `Fill it` with `Opacity (0-1)` next to it: a filled staircase keeps a
    crisp outline over a see-through face.
  * `Pattern`: the same choice of hatchings a filled area has.
  * `Close it down to the zero line`: an open staircase is a line and may
    hang in the air; closed, it stands on zero like a bar chart.
* **2D histogram properties** (visible for 2D Histograms):
  * `Bins across X` and `Bins up Y`: the grid the pairs are counted into
    (20 x 20 to begin with, up to 500 either way).
  * `Colour scale`: 21 colour maps, from `Viridis` to `Greys`.
  * `Opacity (0-1)` with a `Colour bar` switch next to it.  The colour bar
    is drawn **beside the plot area, in axes of its own**, so it follows the
    frame wherever it is dragged and never takes room away from the diagram.
  * `Leave the empty cells white`: on (the default) a cell with nothing in
    it is not painted at all, so the background stays visible; off, it is
    painted with the lowest colour of the scale.
* **Pie properties** (visible for Pie Charts):
  * `Slice colours`: the colour map the slices are taken from - `Tab10` and
    `Tab20` give distinct colours, the others a smooth scale.
  * The **names of the slices** (a list): the text of the first column, the
    row number, or nothing at all.
  * `Start angle` (90 degrees is the top) with the `Edge colour` beside it.
  * `Per cent` with `Decimals` beside it: the share written on every slice.
  * `Hole (0-0.9)` turns the pie into a **doughnut**, `Text size` sets the
    font of the names and the percentages.
  * `Pull out the first` moves the first slice out of the circle, and
    `Edge width` sets the line between the slices.
  * `Go round anticlockwise` reverses the direction.
  * Only **one** column can be a pie, and one pie fills the whole plot
    area: the first ticked column with numbers in it is the one that is
    drawn.  Empty cells and zeros are not slices, and a negative number is
    taken by its size.  A pie has no axes at all - no numbers, no labels,
    no frame lines - and it stays round whatever the shape of the window.
* **Fill under the curve**: `Same colour as the curve` at the top, then
  `Fill colour` with `Opacity (0-1)` next to it, a **pattern** (diagonal,
  vertical, horizontal, crossed, circles, dots, stars and their dense
  variants), and finally `Fill down to zero line`.
  * That last check button is **off** to begin with: the area is then
    filled all the way down to the axis, and it follows the axis when the
    range is changed.
  * Switched **on**, the area is filled between the curve and the **zero
    line** instead, so positive and negative parts are shown separately.
  * The pattern is drawn in the full colour over the semi-transparent area,
    so both stay visible.  The filled area never changes the automatic
    range of the axis: it is a picture of the curve, not data of its own.
* **Marker colour = line colour** copies the line colour into both marker
  colours.

The line and the marker are independent: a red line with green markers is
perfectly possible.  The legend always mirrors what the curve looks like.

### Axes properties

One window with an **X axis** tab, a **Y axis** tab, a **Right Y axis** tab
(whenever a curve is drawn there) and a **Frame and origin** tab.  Every
axis tab has the same three sections, and **the name of each section is its
own check button**:

The three sections share their column widths - the labels **and** the
boxes behind them - so every second setting of a shared line (`To`,
`Minor ticks`, and all three `Colour` boxes) starts at exactly the same
place on the page.

**Axis label and fonts** (switched on)

* the label **text**, then its **font size** with the **Colour** of the
  label next to it on the same line, and `Label offset [px]` - the distance
  from the axis: larger values push the label away from the diagram,
  negative values pull it inwards.
* Switching the section **off** makes the label disappear; the text is
  remembered, so switching it on again brings it back unchanged.

**Tick range, labels and fonts** (switched on)

* the **font size** of the numbers with their **Colour** next to it, and
  `Number offset [px]` (measured from the end of the tick marks),
* **Automatic range and ticks**, or an explicit range - `From` and `To`
  side by side on one line - and `Step (major ticks)` with `Minor ticks`
  (how many minor ones sit between two major ones) on the next line,
* **Axis colour** at the end of the section: the colour of *this* axis line
  and of *its* tick marks.  Each of the three axes has its own, so a black
  bottom axis and a red right axis - matching a red curve - are one click
  apart.  It is deliberately not the colour of the numbers: the number
  colour is the row above it, so a black axis can carry grey numbers.
* Switching the section **off** removes the **numbers and both the major
  and the minor tick marks** of that axis.  The axis line itself and the
  label stay.

**Grid of this axis** (switched off)

* the section title itself draws the **major grid lines**; inside it,
  **Minor grid lines** adds the finer ones,
* **Style** with its **Colour** next to it, and the **Width** of the lines.
* The Y grid is drawn by the Y axis whose numbers are shown, so it appears
  once even when both Y axes are in use.

### Frame and origin

The third tab of the axes dialog, also reachable with
`Plot > Frame and origin...`.

**Frame**

* **Style**:
  * `No frame (X and Y only) (default)` - only the sides that carry an axis
    in use are drawn (see `Which frame lines are drawn`),
  * `Full frame` - all four sides, ticks on the bottom and on the left, as
    matplotlib draws it by default,
  * `Frame with ticks (inward)` - all four sides with ticks on every side,
    pointing into the diagram,
  * `Frame with ticks (outward)` - all four sides with ticks on every side,
    pointing outwards.
* **Thickness** of the frame lines; the tick marks follow it.
* The **colour** is not here: every axis paints its own line and its own
  tick marks with the `Axis colour` of its page (see `Axes properties`).
  In a full frame the two horizontal sides take the colour of the X axis,
  the left side that of the left Y axis and the right side that of the
  right Y axis.
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

| Menu item | Key | What it does |
| --- | --- | --- |
| Open data file (CSV, TXT, DAT) | `Cmd/Ctrl+Alt+O` | Reads a text data file into the table; the separator is recognised automatically. |
| Save data file | `Cmd/Ctrl+Alt+S` | Writes the table into a text data file (`.csv`, `.txt`, `.dat`). |
| Open graph (.aplt) | `Cmd/Ctrl+O` | Loads a complete APlot document: the data and the diagrams. |
| Save graph (.aplt) | `Cmd/Ctrl+S` | Saves the data together with every diagram that is open. |
| Save graph as... | | The same, always asking for a new name. |
| Export figure (image)... | `Cmd/Ctrl+E` | Writes the diagram as a picture (PNG, PDF, SVG, ...). |
| Export as matplotlib script... | `Cmd/Ctrl+Alt+E` | Writes the diagram as a Python program. |
| Copy figure to the clipboard | `Cmd/Ctrl+C` | Puts a picture of the diagram on the clipboard. |

**Saving with one key.**  `Cmd/Ctrl+S` asks for a name only the **first**
time.  From then on the graph belongs to that file: every further
`Cmd/Ctrl+S` simply brings it up to date, with no dialog and no message,
and the name of the file is shown in the title bar of the table window.
`Save graph as...` asks for a new name whenever it is needed.

**Nothing is lost by accident.**  The program knows whether anything has
been changed since the last save (moving or resizing a window does not
count).  If it has, then closing the diagram or leaving the program asks
first:

> This graph has been edited and not saved.  Save it now?

`Yes` saves it (asking for a name if the graph is new), `No` throws the
changes away, `Cancel` leaves everything as it is.  With several diagrams
open, closing one of them does not ask - only the **last** one carries the
whole graph.

**Opening a file never asks.**  `Open graph`, `Open data file` and the
random data of the `Data` menu simply replace what is on the screen: the
question about unsaved work belongs to **leaving** the program (and to
closing the last diagram), where something really can be lost.

**Closing a window is not an edit.**  A graph that is in step with its file
stays in step when its diagram window is closed, so closing the diagram and
then the spreadsheet does not ask twice - and does not ask at all when
nothing was changed since the last save.

### Exporting the diagram

* **Export figure (image)...** (`Cmd/Ctrl+E`) is the same as the save
  button of the toolbar: a picture in any format matplotlib can write, and
  the control points of a selected object are never on it.
* **Copy figure to the clipboard** (`Cmd/Ctrl+C` in the diagram window,
  with nothing selected) puts a 200 dpi picture on the clipboard, ready to
  be pasted into a text editor, a presentation or an e-mail.  With an
  object **selected**, the same key copies that object instead, as before -
  so both uses of `Cmd/Ctrl+C` live side by side.  If the system has no
  tool for pictures on the clipboard, the program says where it wrote the
  file instead.
* **Export as matplotlib script...** (`Cmd/Ctrl+Alt+E`) writes a
  **stand-alone Python program** that draws the very same diagram.  It
  needs nothing but numpy and matplotlib: the data is written into the file
  as plain lists, and so is everything else - the two or three axes with
  their ranges, ticks, colours and grids, the frame, every curve with its
  style and its filled area, the legend boxes at their places, the title
  with its dragged position, the text boxes, the drawings and the arrows.
  Run it with `python3 diagram.py`, change a number, and it is a diagram of
  your own; the last line is a commented-out `savefig` for a batch run.

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

1. `Random data` (File menu), `Open data file` or type the numbers by hand.
   Untick the columns that should not be drawn.
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
   diagram keeps its appearance and only the values change.  Emptying a
   block of cells (select it, `Delete`) breaks the curves there, so a
   measurement can be shown in separate pieces.
6. `Save graph (.aplt)` to be able to continue later, or the save button of
   the Matplotlib toolbar to export a PNG/PDF image.


## 6. Notes

* On macOS the first (bold) menu is named after the running program.  APlot
  renames it to "APlot" through the Cocoa bundle information, which needs
  pyobjc: `pip install pyobjc-framework-Cocoa`.  Without it the menu keeps
  the name of the Python interpreter; everything else works the same way.
* Every empty cell (or a cell that is not a number) breaks the curve at
  that point - an empty Y cell, an empty X cell and an empty row alike.
  The points on the two sides of the gap are never connected.
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
        # the .aplt file this graph belongs to, and how it looked when it was
        # last written: everything else is "edited but not saved"
        self.project_path = None
        self._saved_signature = None
        self._just_saved = False        # the last question ended in a save
        self._was_saved = False         # ... or nothing had been edited at all

        self._build_toolbar()
        self.table = DataTable(self.root, self.settings,
                               on_rename=self._column_renamed,
                               on_add_column=self.add_column,
                               on_delete_column=self.delete_column)
        self.table.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        # the starting sheet is blank: it fills the window with columns
        self.table.set_dataframe(self._empty_frame(), check_all=True,
                                 blank=True)

        self._build_menu()
        self.root.protocol("WM_DELETE_WINDOW", self.quit_app)
        self._saved_signature = self.project_signature()
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
        self.current_plot_style = "line_symbol"
        # where a new row / column goes: remembered from the split buttons
        self.row_place = getattr(self, "row_place", "below")
        self.column_place = getattr(self, "column_place", "after")
        self.plot_split_btn = PlotSplitButton(
            bar, style=self.current_plot_style,
            on_plot=lambda: self.open_plot(self.current_plot_style),
            on_menu=self._show_plot_style_menu
        )
        self.plot_split_btn.pack(side="left")
        ttk.Button(bar, text="Update plot", command=self.update_plot).pack(
            side="left", padx=(6, 0))
        ttk.Separator(bar, orient="vertical").pack(side="left", fill="y", padx=8)
        # the four row / column tools: blue icons add, red ones delete
        self.add_row_btn = TableToolButton(
            bar, kind="row", action="add", where=self.row_place,
            command=self.add_row, on_menu=self._show_row_place_menu)
        self.add_row_btn.pack(side="left")
        self.delete_row_btn = TableToolButton(
            bar, kind="row", action="delete", command=self.delete_row)
        self.delete_row_btn.pack(side="left", padx=(6, 0))
        self.add_column_btn = TableToolButton(
            bar, kind="column", action="add", where=self.column_place,
            command=self.add_column, on_menu=self._show_column_place_menu)
        self.add_column_btn.pack(side="left", padx=(10, 0))
        self.delete_column_btn = TableToolButton(
            bar, kind="column", action="delete", command=self.delete_column)
        self.delete_column_btn.pack(side="left", padx=(6, 0))
        ttk.Button(bar, text="Settings...", command=self.open_settings).pack(side="right")

    # -- where a new row or column goes -------------------------------------
    ROW_PLACES = (("Add row above the selected cell", "above"),
                  ("Add row below the selected cell", "below"),
                  ("Add row at the end of the sheet", "end"))
    COLUMN_PLACES = (("Add column before (left of) the selected cell", "before"),
                     ("Add column after (right of) the selected cell", "after"),
                     ("Add column at the right end of the sheet", "end"))

    def _place_menu(self, button, places, attribute, action):
        """The list of the places under a split button; the choice is kept."""
        menu = tk.Menu(self.root, tearoff=0)
        for label, code in places:
            def _choose(place=code):
                setattr(self, attribute, place)
                button.set_where(place)
                action(place)
            menu.add_command(label=label, command=_choose)
        try:
            menu.tk_popup(button.winfo_rootx(),
                          button.winfo_rooty() + button.winfo_height())
        finally:
            menu.grab_release()

    def _show_row_place_menu(self, _event=None):
        self._place_menu(self.add_row_btn, self.ROW_PLACES, "row_place",
                         self.add_row)

    def _show_column_place_menu(self, _event=None):
        self._place_menu(self.add_column_btn, self.COLUMN_PLACES,
                         "column_place", self.add_column)

    def _show_plot_style_menu(self, _event=None):
        menu = tk.Menu(self.root, tearoff=0)
        for label, code, _desc in PLOT_STYLES:
            def _choose(style=code):
                self.set_plot_style(style)
                self.open_plot(style)
            menu.add_command(label=label, command=_choose)
        try:
            x = self.plot_split_btn.winfo_rootx()
            y = self.plot_split_btn.winfo_rooty() + self.plot_split_btn.winfo_height()
            menu.tk_popup(x, y)
        finally:
            menu.grab_release()

    def set_plot_style(self, style):
        self.current_plot_style = style
        if hasattr(self, "plot_split_btn"):
            self.plot_split_btn.set_style(style)

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

        alt = "Opt" if sys.platform == "darwin" else "Alt"
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Open data file (CSV, TXT, DAT)",
                              accelerator=f"{ACCEL_NAME}+{alt}+O",
                              command=self.load_csv)
        file_menu.add_command(label="Save data file",
                              accelerator=f"{ACCEL_NAME}+{alt}+S",
                              command=self.save_csv)
        file_menu.add_separator()
        file_menu.add_command(label=f"Open graph ({PROJECT_SUFFIX})",
                              accelerator=f"{ACCEL_NAME}+O",
                              command=self.open_graph)
        file_menu.add_command(label=f"Save graph ({PROJECT_SUFFIX})",
                              accelerator=f"{ACCEL_NAME}+S",
                              command=self.save_graph)
        file_menu.add_command(label="Save graph as...",
                              command=self.save_graph_as)
        file_menu.add_separator()
        file_menu.add_command(label="Export figure (image)...",
                              accelerator=f"{ACCEL_NAME}+E",
                              command=lambda: self.export_figure(plot))
        file_menu.add_command(label="Export as matplotlib script...",
                              accelerator=f"{ACCEL_NAME}+{alt}+E",
                              command=lambda: self.export_script(plot))
        file_menu.add_command(label="Copy figure to the clipboard",
                              command=lambda: self.copy_figure(plot))
        file_menu.add_separator()
        file_menu.add_command(label="Random data", command=self.random_csv)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.quit_app)
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
            plot_menu.add_command(label="Copy object (or the whole figure)",
                                  accelerator=f"{ACCEL_NAME}+C",
                                  command=plot.copy_shortcut)
            plot_menu.add_command(label="Paste object",
                                  accelerator=f"{ACCEL_NAME}+V",
                                  command=plot.paste_clipboard)
            plot_menu.add_command(label="Delete object", accelerator="Del",
                                  command=plot.delete_selection)
            plot_menu.add_separator()
            plot_menu.add_command(label="Close this diagram",
                                  command=plot.close_window)
        menubar.add_cascade(label="Plot", menu=plot_menu)

        help_menu = tk.Menu(menubar, tearoff=0, name="help")
        help_menu.add_command(label="Documentation", command=self.show_documentation)
        help_menu.add_command(label=f"About {APP_NAME}", command=self.show_about)
        menubar.add_cascade(label="Help", menu=help_menu)
        self.bind_shortcuts(window, plot)

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

        self.table.set_dataframe(frame, check_all=True)
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
    def project_signature(self):
        """A fingerprint of the whole graph, the window places left out."""
        try:
            document = self.project_document()
        except Exception:
            return None
        for state in document.get("plots") or []:
            # moving or resizing a window is not an edit of the graph
            state.pop("geometry", None)
            state.pop("figure", None)
        try:
            return json.dumps(document, sort_keys=True, default=json_default)
        except (TypeError, ValueError):
            return None

    def is_modified(self):
        """True while something was changed since the last save or load."""
        signature = self.project_signature()
        return signature is not None and signature != self._saved_signature

    def _remember_saved(self, path=None):
        if path is not None:
            self.project_path = str(path)
        self._saved_signature = self.project_signature()
        self._show_project_title()

    def _show_project_title(self):
        """The name of the graph file in the title bar of the main window."""
        if not self.project_path:
            return
        name = Path(self.project_path).name
        try:
            self.root.title(f"{APP_NAME} - {name}")
        except tk.TclError:
            pass

    # -- opening and saving with the keyboard ------------------------------
    def open_graph(self, *_args):
        """Cmd/Ctrl+O: open a graph saved before.

        Opening a file never asks about unsaved work: the question belongs
        to leaving the program (and to closing the last diagram), where
        something really can be lost.
        """
        return self.load_project()

    def save_graph(self, *_args):
        """Cmd/Ctrl+S: save the graph, asking for a name only the first time."""
        if self.project_path:
            return self.save_project(self.project_path, quiet=True)
        return self.save_graph_as()

    def save_graph_as(self, *_args):
        """Always ask where the graph should be written."""
        return self.save_project()

    def _may_discard(self, what="Close"):
        """Ask about unsaved work; False means "do not go on"."""
        self._just_saved = False
        if not self.is_modified():
            return True
        answer = messagebox.askyesnocancel(
            what,
            "This graph has been edited and not saved.\n\n"
            "Save it now?", parent=self.root)
        if answer is None:              # Cancel: stay where we are
            return False
        if answer:                      # Save (asks for a name if it is new)
            self._just_saved = bool(self.save_graph())
            return self._just_saved
        return True                     # close it without saving

    def quit_app(self, *_args):
        """Leaving the program: never lose an edited graph by accident."""
        if not self._may_discard("Quit"):
            return False
        self.root.destroy()
        return True

    def plot_closing(self, window):
        """A diagram window is being closed: the last one takes the graph."""
        # whether the graph was already in step with its file is decided
        # here, before the window disappears from the document
        self._was_saved = not self.is_modified()
        others = [one for one in self.open_windows() if one is not window]
        if others:
            return True
        return bool(self._may_discard("Close the diagram"))

    def plot_closed(self, window):
        """The diagram is gone; a graph in step with its file stays in step.

        Closing a window is not an edit of the graph: a saved diagram that
        is simply closed must not make the program ask about unsaved work
        when the spreadsheet window is closed afterwards.
        """
        self.plot_windows = [one for one in self.plot_windows
                             if one is not window and one.winfo_exists()]
        if self._just_saved or self._was_saved:
            self._just_saved = False
            self._was_saved = False
            self._saved_signature = self.project_signature()
        return None

    # -- exporting ---------------------------------------------------------
    def active_plot(self, plot=None):
        """The diagram the export commands work on."""
        if plot is not None and plot.winfo_exists():
            return plot
        windows = self.open_windows()
        return windows[-1] if windows else None

    def export_figure(self, plot=None, *_args):
        """Cmd/Ctrl+E: write the diagram as an image file."""
        window = self.active_plot(plot)
        if window is None:
            messagebox.showinfo("Information",
                                "There is no diagram to export yet.")
            return None
        window.lift()
        return window.export_figure()

    def export_script(self, plot=None, *_args):
        """Cmd/Ctrl+Alt+E: the diagram as a matplotlib program."""
        window = self.active_plot(plot)
        if window is None:
            messagebox.showinfo("Information",
                                "There is no diagram to export yet.")
            return None
        start = "diagram"
        if self.project_path:
            start = Path(self.project_path).stem
        path = filedialog.asksaveasfilename(
            defaultextension=SCRIPT_SUFFIX, initialfile=start + SCRIPT_SUFFIX,
            filetypes=[("Python program", f"*{SCRIPT_SUFFIX}"),
                       ("All files", "*.*")])
        if not path:
            return None
        try:
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(window.to_script())
        except OSError as error:
            messagebox.showerror("Error", f"Could not save the file: {error}")
            return None
        messagebox.showinfo(
            "Successful",
            "The diagram was written as a matplotlib program.\n"
            "Run it with:  python3 " + Path(path).name)
        return path

    def copy_figure(self, plot=None, *_args):
        """The diagram as a picture on the clipboard."""
        window = self.active_plot(plot)
        if window is None:
            messagebox.showinfo("Information", "There is no diagram yet.")
            return False
        return window.copy_figure_to_clipboard()

    def keyboard_busy(self, widget):
        """True when `widget` is a field that must not lose the keyboard.

        A cell (or a column heading) of the spreadsheet that is open for
        editing keeps the keyboard even when a diagram window becomes the
        active one - otherwise the blinking cursor disappears and nothing
        typed into the cell arrives.
        """
        fields = []
        table = getattr(self, "table", None)
        for holder in (getattr(table, "_editor", None),
                       getattr(table, "_heading_editor", None)):
            if holder:
                fields.append(holder[0])
        for field in fields:
            try:
                if not field.winfo_exists():
                    continue
                if widget is field or str(widget).startswith(str(field) + "."):
                    return True
            except tk.TclError:
                continue
        return False

    def bind_shortcuts(self, window, plot=None):
        """The keyboard commands of the File menu, on every window."""
        def wrap(function, *args):
            def handler(_event=None):
                function(*args)
                return "break"
            return handler

        commands = {
            "o": wrap(self.open_graph),
            "s": wrap(self.save_graph),
            "e": wrap(self.export_figure, plot),
        }
        with_alt = {
            "o": wrap(self.load_csv),
            "s": wrap(self.save_csv),
            "e": wrap(self.export_script, plot),
        }
        for modifier in ("Control", "Command"):
            for letter, handler in commands.items():
                for name in (letter, letter.upper()):
                    try:
                        window.bind(f"<{modifier}-{name}>", handler)
                    except tk.TclError:
                        pass
            for letter, handler in with_alt.items():
                for extra in ("Alt", "Option", "Mod2"):
                    for name in (letter, letter.upper()):
                        try:
                            window.bind(f"<{modifier}-{extra}-{name}>", handler)
                        except tk.TclError:
                            pass

    def project_document(self):
        """Data plus the full state of every open diagram."""
        rows = [[value for value in row]
                for row in self.df.itertuples(index=False, name=None)]
        formulas = {f"{r},{c}": formula
                    for (r, c), formula in getattr(self.table, "cell_formulas", {}).items()}
        return {
            "format": "aplot", "version": 1, "application": APP_NAME,
            "data": {"columns": [str(name) for name in self.df.columns],
                     "rows": rows,
                     "formulas": formulas},
            "plots": [window.to_state() for window in self.open_windows()],
        }

    def save_project(self, path=None, quiet=False):
        """Write the data and every diagram into one `.aplt` file.

        `quiet` is the Cmd/Ctrl+S of a graph that already has a file: it is
        simply brought up to date, without a dialog of any kind.
        """
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
        self._remember_saved(path)
        if not quiet:
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
        self.table.set_dataframe(frame, check_all=True)

        raw_formulas = data.get("formulas") or {}
        loaded_formulas = {}
        for k, v in raw_formulas.items():
            try:
                parts = k.split(",")
                loaded_formulas[(int(parts[0]), int(parts[1]))] = str(v)
            except (ValueError, IndexError):
                pass
        self.table.cell_formulas = loaded_formulas

        for window in self.open_windows():   # replace the current diagrams
            window.destroy()
        self.plot_windows = []
        for state in document.get("plots") or []:
            # a saved project brings its own curves: the whole table is used,
            # and its own style - a histogram reads the columns differently
            window = PlotWindow(
                self.root, self.df.copy(), self.settings, app=self,
                plot_style=str(state.get("plot_style") or "line_symbol"))
            if not window.winfo_exists():
                continue
            window.apply_state(state)
            self.plot_windows.append(window)
        self._remember_saved(path)
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
        self.table.set_dataframe(pd.DataFrame(data), check_all=True)

    # -- table operations --------------------------------------------------
    def add_row(self, where=None):
        """One empty row around the selected cell (or at the end).

        `where` is `"above"`, `"below"` or `"end"`; without it the place
        the split button shows is used.
        """
        where = where or self.row_place
        rows = self.table.selected_rows()
        row = (min(rows) if where == "above" else max(rows)) if rows \
            else (self.table.cursor[0] if self.table.cursor else 0)
        if where == "end":
            at = None
        elif where == "above":
            at = row
        else:
            at = row + 1
        return self.table.insert_row(at)

    def delete_row(self):
        """Delete every row the highlighted block touches."""
        rows = self.table.selected_rows()
        if not rows:
            messagebox.showinfo("Information", "Select a cell or a block first.")
            return
        if len(rows) > 1 and not messagebox.askyesno(
                "Delete rows", f"Delete {len(rows)} rows with their data?",
                parent=self.root):
            return
        self.table.delete_selected_rows()

    def clear_cells(self):
        """Empty the highlighted cells: the curves break at those points."""
        cells, rows, columns = self.table.block_cells()
        if not cells:
            messagebox.showinfo("Information", "Select a cell or a block first.")
            return
        if cells > 1 and not messagebox.askyesno(
                "Clear cells",
                f"Empty {cells} cells ({rows} rows x {columns} columns)?\n"
                "The curves will be broken at the empty cells.",
                parent=self.root):
            return
        self.table.clear_block()

    def copy_cells(self):
        if not self.table.copy_block():
            messagebox.showinfo("Information", "Select a cell or a block first.")

    def paste_cells(self):
        if not self.table.paste_block():
            messagebox.showinfo("Information", "There is nothing to paste.")

    def add_column(self, where=None, at_column=None):
        """One empty column around the selected cell (or at the right end).

        `where` is `"before"`, `"after"` or `"end"`; `at_column` is the
        column it is measured from, the selected one by default.
        """
        where = where or self.column_place
        name = simpledialog.askstring(
            "Add column", "Name of the new column:", parent=self.root,
            initialvalue=self.table.next_column_name())
        if not name:
            return False
        if at_column is None:
            bounds = self.table.block_bounds()
            if bounds is None:
                at_column = self.table.cursor[1] if self.table.cursor else 0
            else:
                at_column = bounds[1] if where == "before" else bounds[3]
        if where == "end":
            at = None
        elif where == "before":
            at = at_column
        else:
            at = at_column + 1
        if not self.table.insert_column(name, at):
            messagebox.showerror("Error", "This column already exists.")
            return False
        return True

    def _column_renamed(self, old, new, index):
        """A heading was edited: follow it in the open diagrams."""
        for window in self.open_windows():
            window.rename_series(old, new, is_x_column=(index == 0))

    def delete_column(self, name=None):
        """Delete the column of the selected cell, with its data."""
        columns = [str(one) for one in self.df.columns]
        if name is None:
            cursor = self.table.cursor[1] if self.table.cursor else None
            if cursor is not None and 0 <= cursor < len(columns):
                name = columns[cursor]
            else:
                name = self.table.current_column
        if name not in columns:
            name = self._ask_column("Delete column")
        if name is None:
            return False
        if len(columns) <= 1:
            messagebox.showinfo("Information", "The last column cannot be deleted.")
            return False
        if not messagebox.askyesno("Delete column",
                                   f"Delete the column '{name}' with its data?",
                                   parent=self.root):
            return False
        return self.table.remove_column(name)

    # -- plotting ----------------------------------------------------------
    def _plottable(self, style=None):
        """Is there anything to draw?

        **One column of numbers is enough** for every kind of diagram: a
        histogram counts it, and every other style draws it against the row
        numbers of the table.  So the question is not how many columns
        there are, but whether the ticked ones hold numbers at all.

        Columns that were switched **off** are still respected: when the
        only thing left is the X column while other columns do carry data,
        the ticks are what the program talks about instead of quietly
        drawing that one column.
        """
        self.table._commit_edit()  # do not lose the cell being edited
        style = style or getattr(self, "current_plot_style", "line_symbol")
        if self.df is None or self.df.empty or not len(self.df.columns):
            messagebox.showerror("Error", "There is no data to plot yet.")
            return False
        columns = self.table.plot_columns()
        if not any(PlotWindow.has_numbers(self.df, name) for name in columns):
            messagebox.showerror(
                "Error",
                "The ticked columns hold no numbers to plot.\n"
                "Type some values into the table first.")
            return False
        if style not in ("histogram", "pie") and len(columns) < 2:
            switched_off = [name for name in list(self.df.columns)[1:]
                            if PlotWindow.has_numbers(self.df, name)]
            if switched_off:
                messagebox.showinfo(
                    "Information",
                    "No column is ticked for plotting.\n"
                    "Tick 'y_L' or 'y_R' above at least one column.")
                return False
        return True

    def plot_data(self, _style=None):
        """The data that goes to the diagrams: the ticked columns only."""
        return self.table.plot_dataframe(1)

    def plot_layout(self):
        """Which axis every ticked column belongs to."""
        return self.table.plot_layout()

    def open_windows(self):
        """The diagrams that are still open."""
        self.plot_windows = [window for window in self.plot_windows
                             if window.winfo_exists()]
        return self.plot_windows

    def open_plot(self, plot_style=None):
        """Open a new diagram of the ticked columns, with the specified or default style."""
        style = plot_style or getattr(self, "current_plot_style", "line_symbol")
        if not self._plottable(style):
            return None
        window = PlotWindow(self.root, self.plot_data(), self.settings,
                            app=self, layout=self.plot_layout(),
                            plot_style=style)
        if window.winfo_exists():
            self.plot_windows.append(window)
            return window
        return None

    def update_plot(self):
        """Send the edited data to the open diagrams without touching style."""
        windows = self.open_windows()
        styles = {window.plot_style for window in windows}
        # while every open diagram counts its own columns, no Y tick is needed
        if not self._plottable("histogram" if styles == {"histogram"} else None):
            return
        if not windows:
            self.open_plot()  # nothing to update yet: open the first diagram
            return
        data = self.plot_data()
        layout = self.plot_layout()
        for window in windows:
            window.update_data(data.copy(), layout=layout)
            window.lift()


def main():
    set_macos_app_name(APP_NAME)  # must run before the first Tk window
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
