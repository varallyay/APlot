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
| Delete row | Deletes every row the highlighted block touches. |
| Add column | Asks for a name and appends an empty column. |
| Delete column | Deletes the column you last clicked in (after a confirmation). |
| Clear cells | Empties the highlighted cells; the curves break at the empty cells. |
| Copy / Paste | The highlighted block to and from the clipboard, tab separated. |
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
| `Shift`+click a heading | Selects that whole column. |
| `Shift`+arrow keys | One row or column more (or less) in the block - this also works while a cell is being edited, where `Shift+Up/Down` leaves the editor at once and `Shift+Left/Right` first select the text of the cell. |
| Arrow keys (no Shift) | Walk from cell to cell; the block collapses to that one cell. |
| `Shift+Space` | The whole rows the block touches (they become tinted). |
| `Ctrl/Cmd+Space` | The whole columns the block touches. |
| `Ctrl/Cmd+A` | The whole table. |
| `Enter` or `F2` | Opens the cell under the cursor for editing. |

The block is what the data operations work on:

| Keys | What happens |
| --- | --- |
| `Ctrl/Cmd+C` | Copies the block as tab separated text - several rows and columns at once, ready for a spreadsheet program. |
| `Ctrl/Cmd+V` | Writes tab separated text (from this program or another one) into the table, starting at the **top left cell of the block**; the shape of the text decides the shape of what is written, so a block of two columns fills two columns even when only one cell is selected.  The table grows if the text has more rows.  This also works while a cell is being edited - only a single value (no tabs, no line breaks) is pasted into the text of that cell. |
| `Ctrl/Cmd+X` | Copies the block and empties it (inside a cell editor it cuts the selected text instead). |
| `Delete` or `Backspace` | Empties the cells of the block. |
| `Delete row` button | Removes every row of the block. |

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
