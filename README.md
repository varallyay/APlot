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
    apart or opened into a doughnut.  The names and the percentages can be
    moved in or out, laid along their own slice and given their own font
    size and colour, and every name can be changed on its own.

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
| The first column holds **names** (no numbers at all) | every other column is a curve and the X axis is the **row number** |

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

**A first column of names counts the rows too.**  A table like
`Solar, Wind, Hydro | 24, 19, 15` is the natural shape of a pie or a bar
chart, but its first column holds not a single number, so it is no X axis
either.  Every column after it then becomes a curve drawn against the **row
number**, and the X axis is again called `Row`.  That is what makes a pie of
such a table switchable to a line or a bar chart and back without an empty
frame in between.  A number typed into the first column makes it the X axis
again at once.

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
lines up cleanly.  Whatever style is chosen, the **`Close` button stays at the
bottom** of the window, under the sections that come and go with the style.

Changing the style also gives the **axes** to whatever is drawn on them.  A
pie needs no axes, so switching a curve to `Pie Chart` takes the axis labels,
the numbers **and the axis lines** away and keeps the square the circle
needs; switching it back to any other style gives the labels, the numbers,
the frame (whatever style it had - two lines or a closed box) and the
automatic range straight back, so the curve appears again exactly where it
was.  The **values
of the curve are worked out again** at the same time, which matters for the
two styles that read the table differently: a histogram carries the counts of
its bins and a pie reads no X column at all, so a curve leaving either of
them is given its own points back.

* **Legend**: the `Text` of this curve's legend box, then its `Font size`
  with the `Colour` of the text next to it.  An empty text removes the box.
  A **pie** is the one exception: its box has one row per slice, so there is
  no single text to type and the `Text` field is switched off (see
  `Pie properties` below).
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
  * **Empty cells.**  A step needs a place to stand, so a point whose cell
    in the **X column** is empty is left out and the treads beside it widen
    over it.  An empty cell in the **value** column stays a gap, exactly as
    it breaks any other curve: the staircase - filled or not - is cut there
    instead of dropping to zero.
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
  * `Hole (0-0.9)` turns the pie into a **doughnut**, `Edge width` sets the
    line between the slices.
  * `Pull out the first` moves the first slice out of the circle, and
    `Turn the names` lays every name along its own slice instead of
    standing it upright.
  * **The names of the slices** - the texts standing around the pie - have
    three settings of their own:
    * `Distance`: **where they stand**.  `1.0` is the rim of the circle,
      less puts the name on the slice, more beside the pie; they start at
      `1.1`, just outside.
    * `Font size` and `Colour`: their own font, independent of the numbers.
  * **The numbers on the slices** have the same three, plus two of their
    own:
    * `Distance` (they start at `0.6`, inside the slice), `Font size` and
      `Colour` - white numbers on strong slice colours read best.
    * `Turn them` lays each number along its own slice, which is what makes
      many thin slices readable at all.
    * `Write them` switches the percentages off altogether, and `Decimals`
      says how precisely they are written.
  * `Go round anticlockwise` reverses the direction.  Changing the
    direction - or any other setting here - never touches the **names typed
    into the legend rows**; they belong to their slices and stay there.
  * Only **one** column can be a pie, and one pie fills the whole plot
    area: the first ticked column with numbers in it is the one that is
    drawn.  (A pie that stands **beside an ordinary curve** - one curve
    switched to `Pie Chart` while another stays a line - leaves the axes to
    that curve and is drawn as a small circle around the origin instead.)  Empty cells and zeros are not slices, and a negative number is
    taken by its size.  A pie has no axes at all - no numbers, no labels,
    no frame lines - and it stays round whatever the shape of the window.
  * **The circle is as big as the plot area.**  The range of the axes is
    the square the pie needs, so it is drawn as large as any other diagram
    and grows when a slice is pulled out.  A range typed into `Axes
    properties` by hand is never overruled, so the pie can be made smaller
    (or bigger) there if that is wanted.
  * **The legend box starts switched off.**  A pie of five slices in one
    colour with one name says nothing, so there is no box to begin with -
    the names stand beside the slices instead.  Switching `Legend` on gives
    a box that lists **every slice** with its own colour and its own name,
    which is the useful form of a legend for a pie.
  * **Every row of that box is a name of its own.**  Because a pie has no
    single legend text, the `Text` field of the `Legend` section is switched
    off for it.  To rename one slice, click its row in the box, wait a
    moment and click it again: a little editor opens **on that row alone**,
    and what is typed there belongs to that slice - beside the pie and in
    the box.  An empty text gives the slice the name the table gives it
    back.  The names that were typed in are written into the `.aplt` file
    and into the exported program with the rest of the curve, and **no other
    setting of the dialog takes them away** - not the direction of the
    slices, not the colour map, nothing.
  * The `Font size` and the `Colour` of the `Legend` section belong to the
    **box**; the font and the colour of the texts standing around the pie
    are set in `Pie properties`, under `The names of the slices`.
  * **A pie is clicked like any other curve.**  It has no line to hit, so
    the slices *and* the names and percentages written on them all open
    `Curve properties` with a single click - which is where their font,
    their colour and their distance are.
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
