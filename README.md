# APlot - Data Visualizer

APlot is a small desktop program for typing or loading tabular data and
turning it into a Matplotlib diagram whose every detail can be changed by
clicking on it.  It is a single Python file and needs only `tkinter`,
`pandas`, `numpy` and `matplotlib`.

Start it with:

    python3 aplot.py


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
* `Left` and `Right` move the text cursor inside the cell.
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
| Click the title | Its text and its font size. |
| Click an axis label | Its text and its font size. |
| Click the text of a legend box | Its text and its font size (an empty text hides that box). |
| Drag the frame of a legend box | Moves that legend box anywhere on the diagram. |
| Double-click beside an axis (on the numbers or the label) | Axes properties, opened on the tab of that axis. |
| Plot menu | The axes dialog (axes, frame and origin) and the title/fonts dialog, plus closing the window. |
| Toolbar | The standard Matplotlib toolbar: pan, zoom, and saving the figure as an image. |

### Legend boxes

Every curve has its **own** legend box, so they can be placed
independently.

* Grab a box anywhere on its frame - that is, next to the sample line, not
  on the text - and drag it to a new place.  The pointer turns into a move
  cross over the frame and into a text cursor over the text.
* Click the text of a box to change the text and the font size of that box
  alone.  An empty text hides the box.
* The boxes keep their position when the data is updated, when the curve
  style changes and when a column is renamed, and they are stored in
  `.aplt` files.
* `Plot > Title and fonts...` sets one font size for every box, the corner
  where new boxes start, and can stack all boxes again with
  `Reset positions`.

### Curve properties

* **Legend**: the text of this curve's legend box and its font size.  An
  empty text removes the box.
* **Line**: style (solid, dashed, dash-dot, dotted, none), width, colour.
* **Marker**: style (13 shapes plus "None"), size, fill colour, "Hollow"
  (unfilled marker), edge colour, edge width.
* **Marker colour = line colour** copies the line colour into both marker
  colours.

The line and the marker are independent: a red line with green markers is
perfectly possible.  The legend always mirrors what the curve looks like.

### Axes properties

One window with an **X axis**, a **Y axis** and a **Frame and origin** tab.
The two axis tabs have:

* **Axis label and fonts**: the label text, the font size of the label and
  the font size of the numbers (ticks).
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
  * `No frame (X and Y axes only)` - only the left and the bottom side are
    drawn, there is no top X axis and no right Y axis,
  * `Full frame (default)` - all four sides, ticks on the bottom and on the
    left, as matplotlib draws it by default,
  * `Frame with ticks (inward)` - all four sides with ticks on every side,
    pointing into the diagram,
  * `Frame with ticks (outward)` - all four sides with ticks on every side,
    pointing outwards.
* **Thickness** and **Colour** of the frame; the tick marks follow them, so
  the whole frame stays consistent.

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

Font sizes can be set in three places:

* the **title**: click it on the diagram, or use
  `Plot > Title and fonts...`,
* the **axis labels** and the **axis numbers**: click the label, or use the
  matching tab of the axes dialog,
* the **legend boxes**: click the text of a box for that box alone, the
  curve properties dialog for the same box, or
  `Plot > Title and fonts...` for all of them at once.

`Plot > Title and fonts...` also switches the legend boxes on and off,
chooses the corner where they start, and puts them back into a stack.


## 3. Files

| Menu item | Format |
| --- | --- |
| Open CSV | Reads a comma separated file into the table. |
| Save CSV | Writes the table into a comma separated file. |
| Open graph (.aplt) | Loads a complete APlot document: the data and the diagrams. |
| Save graph (.aplt) | Saves the data together with every diagram that is open. |

An `.aplt` file is a readable JSON document.  Besides the table it stores,
for each open diagram:

* the curves with their colour, line style and width, marker type, size,
  fill and edge colour, edge width, visibility, legend text, and the
  position, corner and font size of their own legend box,
* the title and its font size, the visibility, starting corner and default
  font size of the legend boxes,
* both axes: label, label and tick font size, automatic or fixed range,
  step, number of minor ticks, and the grid settings of the axis,
* the frame: style, thickness, colour, and the size and origin of the axes
  inside the window,
* the figure size, resolution and the window geometry.

Loading an `.aplt` file replaces the table and closes the diagrams that are
open, then reopens the saved ones exactly as they were saved.

The separator and the decimal sign used for CSV files can be changed in the
settings.


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
| Plot | Figure size and resolution, the title pattern (`{x}` is the name of the X column), default Y label, default line style and width, default marker, size and edge width, hollow markers, legend visibility and starting corner. |
| Font sizes | Title, axis labels, axis numbers, legend boxes. |
| Grid | Default grid: major and minor lines, colour, style, width, number of minor ticks. |
| Frame | Default frame style, thickness and colour, and the default size and origin of the axes (as fractions of the window). |
| CSV files | Field separator and decimal sign. |

Window sizes and plot defaults are used by windows opened after saving;
diagrams that are already open keep their settings.


## 5. Typical workflow

1. `Random data`, `Open CSV` or type the numbers by hand.
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
