# APlot - Data Visualizer

APlot is a small desktop program for typing or loading tabular data and
turning it into a Matplotlib diagram whose every detail can be changed by
clicking on it.  It is a **single Python file**.

Start it with:

    python3 aplot.py

It also answers a few questions on the command line:

    python3 aplot.py --help          what these are
    python3 aplot.py --make-app      build APlot.app on macOS (see below)
    python3 aplot.py --icon FILE     write the icon into a PNG file


## What it needs

Four packages have to be there; everything else is part of Python itself.

| Package | Used for | Install |
| --- | --- | --- |
| `tkinter` | the whole user interface: windows, menus, the table | comes with Python (on some Linux systems as the separate `python3-tk` package) |
| `numpy` | every calculation: the curves, the histograms, the fitting | `pip install numpy` |
| `pandas` | the sheets themselves and the reading of data files | `pip install pandas` |
| `matplotlib` | the diagrams, and the pictures that are exported | `pip install matplotlib` |

All four at once:

    pip install numpy pandas matplotlib

### Optional packages

The program **starts and works without every one of these**.  Each of them
switches one convenience on, and when it is missing the program says so
quietly or simply leaves that one thing out.

| Package | What it adds when it is there | Without it |
| --- | --- | --- |
| **`tkinterdnd2`** | **dropping a picture** from the Finder onto a diagram (it brings the `tkdnd` extension of Tk, which Tk itself has no drop support without) | pictures still arrive by pasting (`Ctrl/Cmd+V`), through the picture button of the toolbar and through `Plot > Insert picture...` |
| `pillow` (`PIL`) | the drawn **toolbar icons**, reading a **picture** that is pasted or dropped, and the clipboard of the system | the buttons carry their names in words and pictures cannot be inserted |
| `openpyxl` | opening and saving **Excel** (`.xlsx`) files, one sheet per tab | CSV, TXT, DAT and the program's own `.aplt` files work as usual |
| `pyobjc-framework-Cocoa` | the bold application menu on **macOS** is called `APlot` | that menu keeps the name of the Python interpreter (the Dock label is settled by `--make-app` either way) |

    pip install tkinterdnd2 pillow openpyxl
    pip install pyobjc-framework-Cocoa        # macOS only

An optional package is always imported inside a `try`, so a missing one is
never an error.  An editor that checks the imports (VS Code with Pylance,
for instance) may still mark such a line as unresolved - that is the editor
saying the package is not installed in the interpreter **it** has selected,
not a fault in the program.

**Install into the interpreter that really runs APlot.**  A bare `pip` often
belongs to another Python than the `python3` that starts the program; this
always lands in the right place:

    python3 -m pip install tkinterdnd2

and `python3 -c "import sys; print(sys.executable)"` says which interpreter
that is.

### The one file

Beside `aplot.py` the program writes `~/.aplot/config.json` the first time
the settings are saved, and nothing else.  No `icons` folder, no data
directory: the toolbar icons are drawn by the program itself, and a graph
carries its data, its formulas and even its pictures inside its own `.aplt`
file.

### The icon, and the name in the Dock

The program **draws its own icon**: a spectrum, its blue body under an
orange outline, on a rounded square and nothing else on it.  It is drawn,
not carried as a picture file, so it is sharp at whatever size the system
asks for and the single file stays the only thing to copy.  Every window
wears it - on Linux and Windows in the task bar, on macOS in the Dock.

Three constants at the top of `aplot.py` decide how it is drawn:

| Constant | What it sets |
| --- | --- |
| `APP_ICON_SIZE` (512) | the number of pixels the icon is drawn at - how **sharp** it is, not how big it appears. |
| `APP_ICON_SIZES` | the sizes written into `APlot.app`'s `.icns`, each also at `@2x`. |
| `APP_ICON_MARGIN` (0.1) | the **free border** left around the rounded square, as a part of the whole picture. |

How large the icon *appears* in the Dock is not the program's to decide: it
is the size of the Dock tile, which is a setting of macOS itself.  What the
margin does is leave the same free border around the square that Apple's
own icons have, so APlot sits at the same size as its neighbours instead of
filling its tile edge to edge.  Setting it to `0.0` fills the tile
completely; the whole drawing - the square, its rounded corners and the
spectrum on it - scales with it.

`python3 aplot.py --icon aplot.png` writes it out, for a launcher, a
shortcut or a `.desktop` file of your own.

#### The name under the icon on macOS

The Dock shows the icon at once, but the **name above it** is a different
matter: a program started as `python3 aplot.py` *is* the Python interpreter
as far as macOS is concerned, so the label reads `python3.12`.  No setting
inside a running program changes that - the name comes from the application
the system thinks it launched.

The cure is a small **application bundle**, and APlot builds one for
itself.  The first time it is started on a Mac it offers to do so, and the
offer is made **once**, whatever the answer.  It can also be asked at any
time:

* the **`APlot > Install APlot in the Dock...`** menu item (it is there
  only while the name is still borrowed), or
* from a terminal:

        python3 aplot.py --make-app

Either way `~/Applications/APlot.app` is written.  It is a folder, not a
copy: it holds the icon, the name and a three-line launcher that starts
**this same `aplot.py`**, wherever it lies - nothing is compiled and
nothing is duplicated.  Start APlot from there (and keep it in the Dock)
and the label says `APlot`.  Give the command a folder of your own to put
the bundle somewhere else:

    python3 aplot.py --make-app /Applications

Run it again after moving `aplot.py`, so that the launcher points at the
new place.

With `pyobjc-framework-Cocoa` installed the program also tells macOS its
name and its bundle directly, which is what the **bold application menu**
reads; the Dock label, though, only the bundle settles for good.


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

The table is not one sheet but as many as are needed: the **tabs** along its
bottom edge each hold a table of their own (section 1.1).

### Toolbar

The toolbar has **two rows**.  The first one carries everything that acts on
the table, the second one the regression and the check button that draws two
sheets together:

| Button | Row | What it does |
| --- | --- | --- |
| Plot (split button) | first | The word `Plot` beside a picture of the style it will draw. Clicking it opens a NEW diagram with that style; clicking the arrow on its right opens the style menu to choose among 9 styles. |
| Update | first | Sends the current data to the diagrams that are already open, keeping every style setting. |
| Open graph (folder icon) | first | Opens a `.aplt` file: the data and every diagram in it.  `Cmd/Ctrl+O`. |
| Import data (arrow icon) | first | Reads a text data file (CSV, TXT, DAT) into the sheet.  `Cmd/Ctrl+I`. |
| Save graph (disc icon) | first | Writes the whole graph - the sheets and the diagrams - into the `.aplt` file.  `Cmd/Ctrl+S`. |
| (the Plot icon) | first | A picture of the style that will be drawn - it changes with the style chosen from the arrow. |
| Add row (icon, split button) | first | Inserts an empty row **around the selected cell** and starts editing it. The arrow chooses the place: above, below, or at the end of the sheet. |
| Delete row (icon) | first | Deletes every row the highlighted block touches. |
| Add column (icon, split button) | first | Asks for a name and inserts an empty column **around the selected cell**. The arrow chooses: before, after, or at the right end of the sheet. |
| Delete column (icon) | first | Deletes the column of the selected cell (after a confirmation). |
| Settings... | first | Opens the settings editor (see section 5). |
| **Regression** | second | Fits a curve to the columns of this sheet - see section 1.2.  `Ctrl/Cmd+R`, or `Plot > Regression...`. |
| **Plot with previous tab** | second | Glues this sheet to the one before it, so that they are drawn in the same diagram (see `Sheets that are drawn together`).  Ticking it redraws nothing by itself: the next `Update` or `Plot` uses it.  It stands beside `Regression` on every sheet; on the first one there is nothing before it, so it cannot be ticked. |

Clearing, copying and pasting cells are done with the keys (`Delete`,
`Ctrl/Cmd+C`, `Ctrl/Cmd+V`, `Ctrl/Cmd+X`) or with the `Edit` menu, which
also takes a change back (`Ctrl/Cmd+Z`, see section 3); `Random data` is in
the `File` menu.

### 1.1 Sheets (tabs)

Along the bottom of the table there is a **tab for every sheet** and a `+`
that makes a new one.  Each sheet is a full table of its own: its own
columns, its own values, its own formulas and its own check buttons.  The
sheet in front is the one every command of the toolbar and of the menus
works on.

* **A new sheet**: click `+`.  It opens empty and is called `Data 2`,
  `Data 3`, and so on.
* **Renaming**: click the tab of the sheet that is **already in front** a
  second time - exactly as a title or an axis label of a diagram is renamed
  - and the name can be written **on the tab itself**; `Enter` keeps it,
  `Esc` leaves it as it was.  A double click does the same, and
  `Rename tab` in the right click menu asks for the name in a little
  window.  The name of a sheet matters: it is what a curve of that sheet is
  called in a diagram that draws several sheets at once, and the diagrams
  follow the new name at once.
* **Colouring and deleting**: right click (or Ctrl-click) a tab.
  `Tab colour` paints a small square on it, which is useful for telling a
  fit, a measurement and a calculation apart at a glance.  The last sheet
  is never deleted.
* **Every sheet is written into the `.aplt` file** with its name, **its
  colour**, its data, its formulas, which of its columns are ticked, and
  whether it is drawn with the one before it.  A file written by an older
  version - one single table - opens as a single sheet.

**Sheets that are drawn together.**  Two data files loaded into two sheets
are often two measurements of the same thing.  Ticking **`Plot with
previous tab`** on the second sheet glues it to the first one, and the run
of sheets that are stuck together is a **group**: the X columns are matched
up and every curve of the group stands in the same diagram.

The X columns do not have to agree.  Whole numbers in one sheet and
fractions in the other are compared as fractions, X values that are words
are compared as words, and an X value that only one of the sheets has
simply carries **no point** for the other one - its curve is not broken
there.  An **empty cell inside** a sheet is a different matter: it stays a
real hole in that curve, exactly as it would be if the sheet were drawn on
its own.

The glue holds **in both directions**.  A diagram opened from **any** sheet
of a group draws the **whole** group, so it makes no difference whether the
box was ticked before or after the diagram was opened, or which sheet of
the group was in front at the time.

A sheet whose box is **not** ticked **begins a new group**.  With five
sheets and the box ticked on the second and on the fifth, the groups are
`1+2`, `3` alone and `4+5`: the fifth is drawn with the fourth, and not
with the first three.

Every curve keeps **its own column name**.  Only a name that is already
taken by an earlier sheet of the group gets the name of its own sheet after
it - `Signal` and `Signal (Tuesday)` - so that two curves never share one
name, and ticking the box does not rename (and so does not restyle) a
single curve that was already drawn.

**Ticking the box changes nothing on the screen.**  It says what the next
drawing will contain, and the diagrams that are open stay exactly as they
are until:

* **`Update`** brings every open diagram up to date - each of them from its
  own group; or
* **`Plot`** opens a **new** diagram of the group the sheet in front
  belongs to, as the boxes stand at that moment.

The one exception is a **regression**: the sheet it writes arrives with the
box already ticked, and the diagram of the measurements is refreshed at
once, so the fitted curve appears over the points without asking.

Every diagram remembers **which sheet it was opened from**, so `Update`
brings each of them up to date from its own group and one group never
overwrites the diagram of another.

### 1.2 Regression: fitting a curve to the data

The `Regression` button of the second toolbar row opens a window that fits a
curve to the columns of the sheet in front.  The **methods stand on the
left**; choosing one shows on the right exactly what it needs.

Eight methods are offered, and every one of them works out its own starting
values, so all of them fit **out of the box** - there is nothing to set up
before pressing `Fit`:

| Method | The curve | Its parameters |
| --- | --- | --- |
| Straight line | `y = a*x + b` | slope, intercept |
| Polynomial | `y = c0 + c1*x + c2*x^2 + ...` | the coefficients (the **order** is a setting) |
| Exponential growth | `y = Y0 * exp(k*x)` | Y0, rate (and the doubling time) |
| One phase decay | `y = (Y0 - Plateau)*exp(-K*x) + Plateau` | Y0, plateau, rate (and the half life) |
| Two phase decay | `y = Plateau + Fast*exp(-Kf*x) + Slow*exp(-Ks*x)` | plateau, two spans, two rates (and both half lives) |
| Logistic curve | `y = Bottom + (Top-Bottom)/(1 + exp(-k*(x-x50)))` | bottom, top, midpoint, steepness |
| Gaussian distribution | `y = Base + A*exp(-(x-Mean)^2/(2*SD^2))` | baseline, amplitude, mean, width (and the FWHM and the area) |
| Moving average | the running mean of n points | the window (a setting, not a fitted number) |

Everything but the moving average is fitted by **least squares**: the sum of
the squared distances between the data and the curve is made as small as it
goes.  The straight line and the polynomial are solved exactly; the four
curved ones are fitted with the **Levenberg-Marquardt** method, written into
the program itself, so nothing beyond numpy is needed.

**What the right hand side offers**

* **Settings** of the method that has them: the `Order` of a polynomial
  (1 to 10), the `Window` of a moving average.
* **Columns to fit**: every column after the first one.  The ones that are
  ticked for plotting are chosen to begin with; click, `Shift`-click or
  `Ctrl/Cmd`-click to choose others.  The **first column holds the X
  values** (a first column of names counts the rows instead).
* **Parameters**: one line for every parameter of the method.  Leaving the
  `Start value` empty lets the program work it out from the data, which is
  what usually happens.  Typing one in says where the fit should set out
  from - useful when a difficult fit runs away - and ticking `Hold` beside
  it **keeps that parameter fixed** at the value typed in while the others
  are fitted (a plateau that is known, a baseline that is zero).
* **The curve that is written**: how many `Points` it is drawn with (100)
  and how far `Past the data` it reaches (5 per cent of the range at both
  ends).  A moving average says nothing outside the measurements, so it is
  never drawn past them.

**What `Fit` does**

1. Every chosen column is fitted, and a **new sheet** appears right after
   the sheet that was fitted, called `Fit` (`Fit 2`, `Fit 3`, ...).
2. That sheet holds the **X values** of the curve in its first column and
   the fitted curve of every column beside it (`A fit`, `B fit`, ...) - 100
   points over the range of the data, widened by 5 per cent.
3. Then **one column is left empty**, and after it come the **parameters**:
   a column of names (`Parameter`) and one column of values for every curve
   that was fitted.  Under the parameters stand what follows from them (a
   half life, the FWHM...), then `R squared`, `RMSE`, the number of points
   fitted and the name of the method.
4. The parameter columns are **not data to draw**: their `y_L` / `y_R` check
   buttons are switched off, so they never become curves.
5. The new sheet has **`Plot with previous tab` ticked**, and the diagram is
   refreshed at once - the one place where a drawing is brought up to date
   without the `Update` button: the measurements keep their markers and the
   fitted curve is drawn over them as a **smooth line**.

Everything in the new sheet is an ordinary sheet: the numbers can be edited,
copied, saved with the graph and plotted in any style.

### The toolbar icons

Every icon of the toolbar is **drawn by the program itself** - there are no
picture files to carry around.  Each one is painted four times as large as
it is shown and then shrunk, which is what gives it smooth edges, and they
are all kept in the same **pastel and grey** shades so the toolbar stays
quiet beside the table.

The **Plot** button carries a little picture of the style it will draw, and
that picture **follows the style**: a line, a line with markers, scattered
points, bars, error bars, a histogram, a staircase, a grid of counts or a
pie.  Choosing another style from its arrow menu changes the icon at once,
so the button always shows what clicking it will open.

The four row and column tools are a tiny picture of a **sheet of three
bands** - lying down for the rows, standing up for the columns - with a
small badge in the corner:

* **Pastel blue and a `+` add.**  The blue band is the new row or column,
  and it is drawn **where it will appear**: at the near end for
  *above* / *before*, at the far end for *below* / *after*, and standing
  **apart** from the other two for *at the end of the sheet*.
* **Pastel rose and a `-` delete.**  The rose band in the middle is the row
  or column that goes away.

The three file tools beside them - an open folder, an arrow running into a
sheet and a disk - are drawn in the same shades.

**The diagram window uses the very same set.**  The buttons matplotlib
brings with it - `Home`, `Back`, `Forward`, `Pan`, `Zoom`, `Subplots` and
`Save` - carried small black pictures of their own; they are replaced, one
for one, with drawn pastel ones: a little house, two arrows, the four-way
arrow, a magnifier, the plot area with its two handles, and the same disk
as on the spreadsheet.  `Pan` and `Zoom` stay pressed while they are in
use, and then show their icon on a **pale blue plate**, so it is plain
which of them is waiting for a click in the diagram.  The `T` of the text
tool, the drawing tool, the arrow tool and the picture button are painted
in the same shades, and the two split buttons stand on the toolbar itself
instead of on a grey block.

Resting the pointer on any of them brings a **popup text** that spells the
operation out in words - *"Insert row below (click arrow for options)"*,
*"Delete column"*, and so on.  The text follows the place that is chosen, so
the button always says what it is about to do.

The icons are painted with **Pillow** (one of the optional packages, see
`What it needs`).  Without it every button simply carries its name in words
and everything else works exactly the same.

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
    switched off, moved in or out, laid along their own slice and given
    their own font size and colour, and every name can be changed on its
    own.

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

* **Fill down**: the black fill handle of the selection, or `Fill Down` in
  the right click menu of a cell or a heading (`Ctrl/Cmd+D` now belongs to
  `Edit > Duplicate`, see section 3).  It copies the
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
  `Ctrl/Cmd+C` copies the column, `Delete` empties it, `Ctrl/Cmd+D`
  duplicates it under itself, and the arrow keys walk on from the cell the
  click left the cursor in.  `Ctrl/Cmd+Space` does the same thing from the keyboard.
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
* On any **cell**: `Cut`, `Copy`, `Paste`, `Fill Down`, `Duplicate`,
  `Column Math...`, `Clear Cells`, `Insert Row Above`, `Insert Row Below`,
  `Delete Row(s)`.
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

* The sheet has the keyboard **as soon as the window opens**: cell `A1` is
  already marked, the arrow keys walk from cell to cell and typing starts
  writing - nothing has to be clicked first.  The sheet that is brought to
  the front, and the one left in front by an opened graph, take the
  keyboard the same way.
* **Just start typing**: the first character opens the cell under the
  cursor and is the first character in it, as in a spreadsheet.  `Enter`
  or `F2` opens it with the value that is there instead.
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
| Any letter, digit or sign | Opens the cell under the cursor and writes that character into it (what was there is replaced).  `Ctrl`, `Cmd` and `Alt` together with a key stay commands and never write. |

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
| `Ctrl/Cmd+D` | `Edit > Duplicate`: the block again, in the rows just under it.  (Filling down keeps the fill handle and the `Fill Down` line of the right click menu.) |
| `Ctrl/Cmd+Z` | Takes the last change back; `Shift+Ctrl/Cmd+Z` does it again (see section 3). |
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

### The page

A diagram is a **page**, like a slide: it has a size of its own - the
`Page width` and `Page height` of the settings - and it keeps that size
whatever happens to the window.  The window is only a view of the page:

* **Resizing the window never changes the diagram.**  The proportions, the
  lengths of the axes, the font sizes and everything else stay exactly as
  they are; only more or less of the desk around the page becomes visible.
* When the window is **larger** than the page, the page sits in the middle
  of the desk.
* When the window is **smaller**, scrollbars appear and the page can be
  moved about: with the **wheel** (`Shift`+wheel sideways), by dragging with
  the **middle button**, or with the scrollbars themselves.
* **Zooming** changes how large the page is drawn, not what is on it.
  There are three ways to it, and all three zoom around the **pointer** -
  the point under it stays under it:
  * `Ctrl/Cmd` held while the **wheel** turns, which is also what two
    fingers sliding on a trackpad send;
  * the **`-`**, the zoom and the **`+`** at the end of the toolbar, where
    the zoom also opens a little menu of the usual ones, `Fit the window`
    and `True size`;
  * `Ctrl/Cmd`+`+` and `Ctrl/Cmd`+`-` from the keyboard, with `Ctrl/Cmd+0`
    for the true size of the page.

  The zoom starts at 15%, and is written both on the toolbar button and in
  its message line.
* The zoom is a property of the **view**, so it changes nothing that is
  saved or exported: a picture, a copy on the clipboard and an exported
  matplotlib program are always of the page itself.

The size of the page is stored in the `.aplt` file together with the zoom,
so a graph opens looking exactly as it was left.

#### Zooming smoothly

The whole page is drawn again at every step of a zoom, and that drawing is
the slow part.  Three things keep it from stuttering:

* **Every push is worth a fraction of a notch.**  A mouse wheel clicks once
  and sends a big number; a trackpad sends a run of small pushes as the
  fingers slide.  Each push moves the zoom by its own small share, so two
  fingers glide instead of jumping.
* **The pushes are gathered up.**  They arrive far faster than a page can be
  drawn, so they are added together and the page is drawn **once**, at the
  value the fingers have reached by then - never at a value they have long
  passed.  The wait before that drawing grows with what the last one really
  cost, so a heavy diagram keeps answering the fingers.
* **One drawing, not three.**  Resizing the canvas used to make matplotlib
  repaint the diagram two or three times for a single push; now the asking
  is held back and one drawing is made at the end.

Five constants at the top of `aplot.py` set the feel of it:

| Constant | What it sets |
| --- | --- |
| `ZOOM_STEP` (1.035) | how much **one notch** zooms.  Raise it for coarser, faster steps, lower it for finer ones. |
| `ZOOM_WHEEL_UNIT` (4.0) | what counts as **one notch** when the system sends small numbers instead of the 120 a mouse wheel clicks (macOS does this for both the wheel and the trackpad).  **Raise it if the zoom runs away under two fingers**, lower it if it is too slow to answer. |
| `ZOOM_MAX_NOTCHES` (2.0) | the most a **single** push may zoom, so one flick cannot jump across the whole range. |
| `ZOOM_SETTLE_MS` (15) and `ZOOM_SETTLE_MAX_MS` (120) | the shortest and the longest wait before the gathered pushes are drawn. |
| `ZOOM_MAX_PIXELS` (6 million) | the largest the page is ever drawn.  However far you zoom in, the page stops here - a page of tens of millions of pixels would crawl.  It is why `Ctrl/Cmd`+`+` stops at a different place for a large page than for a small one. |
| `ZOOM_BUTTON_STEP` (1.25) | one press of `-` or `+` on the toolbar. |
| `ZOOM_SCROLL_LINES` (0.2) | how far the desk **scrolls** for one notch, in scroll units (one unit is a tenth of what the window shows). |
| `ZOOM_PRESETS` | the percentages the zoom button's menu offers. |

**Why there is no pinch gesture.**  macOS sends a pinch to **Cocoa**, and
Tk never sees it.  It can be picked up from Cocoa with `pyobjc`, and an
earlier version of this program did exactly that - but the gesture then
calls back into Python from inside Tk's own event loop, where Python has
let go of the interpreter lock, and the program dies on the spot:

    Fatal Python error: PyEval_RestoreThread: the function must be called
    with the GIL held ... the GIL is released

There is no way to make that safe while Tk runs the loop, so APlot does not
listen for the gesture at all.  What a trackpad *does* send to Tk is the
wheel: **two fingers sliding with `Ctrl`/`Cmd` held zoom exactly as a pinch
would**, and the `-` and `+` of the toolbar are always there.

**A new diagram starts at a set place on the page**, the one the `Frame`
tab of the settings holds (`left`, `bottom`, `x_length`, `y_length` as
fractions of the page) - and `Default layout` in `Frame and origin` puts
that place back.  It is deliberately modest, so that there is room to work
around the graph; `Resize graph > Fit to page` is the one command that
blows the whole diagram up to fill the page.  A size and origin of your
own, typed in `Frame and origin` or set in the settings, is used as it
stands.

### Clicking

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
nothing to move or copy on it by itself.  A curve is opened by clicking it
**twice**; one click takes hold of the whole graph and carries it to
another place (see `Moving the whole graph`).

| Action | Result |
| --- | --- |
| Drag the plot area, a curve or the frame | **Moves the whole graph** to another place in the window (see `Moving the whole graph`). |
| Click a curve twice | Curve properties: line and marker settings separately.  One click does not open it - it grabs the graph. |
| Click the title, an axis label, a legend box, a text box, a drawing or an arrow | Selects it (a text turns blue, a drawing shows control points). |
| Click the selected object again | Its property window: text, font, colours, distances - whatever belongs to that object. |
| Drag any selected-able object | Moves it (the title, the axis labels, the legend boxes, text boxes, drawings and arrows all move freely). |
| Drag a control point | Resizes a drawing, moves the tip or the tail of an arrow or of a line, or makes an axis longer or shorter.  On a **picture** the four **corner** points keep its proportions and the four **side** points squeeze or stretch it (see `Resizing with the control points`). |
| Drag the round control point above a drawing or a text box | Turns it around its centre (a text box around its own anchor); `Shift` keeps 15 degree steps.  A line has no such point: its two ends give the direction. |
| Arrow keys | Move the selected object by one pixel, with `Shift` by ten. |
| Right click (`Ctrl`+click on a Mac) | The menu of that object: `Copy`, `Cut`, `Paste`, `Duplicate`, `Bring to front`, `Bring forward`, `Send backward`, `Send to back` (see `Which object is in front`).  On the **paper** the same menu ends with `Resize graph`. |
| Wheel / `Ctrl/Cmd`+wheel | Scrolls the page in the window / zooms the view around the pointer; the toolbar's `-`, zoom and `+` do the same (see `The page`). |
| `Ctrl/Cmd+C`, `Ctrl/Cmd+X`, `Ctrl/Cmd+V` | Copies or cuts out the selected text box, drawing, picture or arrow with all of its properties, and pastes another copy of it.  Of the two things that can be waiting - an object copied here and a picture on the clipboard of the system - `Ctrl/Cmd+V` takes the **newer** one. |
| `Ctrl/Cmd+D` | `Edit > Duplicate`: a second copy of the selected object at once, a little to the lower right, without touching the clipboard. |
| `Ctrl/Cmd+Z` | Takes the last change back; `Shift+Ctrl/Cmd+Z` does it again (see section 3). |
| Drop a picture file on the diagram | Lays that picture where it was dropped (see `Pictures in the diagram`). |
| `Delete` / `Backspace` | Removes the selected text box, drawing, picture or arrow. |
| Click an axis line (the frame) | Selects that axis: a control point appears on each of its two ends. |
| Drag the axis line itself | Moves the whole graph, the same as dragging the plot area. |
| Drag one of those two points | Makes that axis longer or shorter - the other end stays where it is. |
| Click the selected axis line again | Frame and origin settings. |
| Click twice beside an axis (on the numbers or the label) | Axes properties, opened on the tab of that axis (the window also carries the title page and both Y axis pages). |
| Hold Shift while drawing or resizing an arrow or a line | Keeps it horizontal, vertical or at 45, 135, 225, 315 degrees. |
| Plot menu | The axes dialog (axes, frame and origin), the title/fonts dialog, copy, cut, paste and delete of the selected object, the four stacking commands, plus closing this diagram. |
| Toolbar | The Matplotlib tools (home, back, forward, pan, zoom, subplots, saving the figure as an image) in the drawn pastel icons of the program, the **T** button that adds a text box, the drawing tool, the arrow tool and the picture button. |

The blue veil and the control points are only on the screen: they are left
out of the image that the save button of the toolbar writes.

### Which object is in front

Everything drawn inside the plot area stands in one **stack**: the curves,
the drawings, the pictures, the arrows and the text boxes together.  What
is higher in the stack is painted over what is lower, and every one of them
can be moved up and down in it - so a picture can be pushed **behind** the
curves as a background, and one curve can be brought out **in front of**
another one.

* A **right click** on any of them (`Ctrl`+click on a Mac, or the right
  button of the mouse) opens a small menu.  Its first line names what was
  found under the pointer - `Curve`, `Drawing`, `Picture`, `Arrow`,
  `Text box`, or `The paper of the diagram` when the pointer was on the
  empty paper.
* Four commands move it: **Bring to front** and **Send to back** take it
  the whole way in one click, while **Bring forward** and **Send backward**
  lift it past exactly **one** neighbour - clicking the same line again and
  again walks it through the stack, and the toolbar says at every step what
  it has just passed.  All four are in the **Plot** menu as well, for
  whatever is selected.
* **Copy** and **Cut** put a text box, a drawing, a picture or an arrow
  aside - `Cut` takes it out of the diagram as well.  A **curve** belongs
  to the spreadsheet, so those two lines are greyed out over a curve; it
  can still be moved in the stack.
* **Paste** lays the copied object - or a picture waiting on the clipboard
  of the system - exactly **where the right button was pressed**, on top of
  everything.  This is what the empty paper is for: right click anywhere in
  the diagram and paste.
* What the pointer finds is what is **in front** at that point, so after a
  curve has been moved over a drawing the same click reaches the curve.
* A newly drawn object always appears in front of everything, and the whole
  order is written into the `.aplt` file and into the exported matplotlib
  program.
* The stack reaches **across both Y scales**.  Matplotlib draws one set of
  axes completely before the other, so a drawing could otherwise never
  stand over a curve of the **right hand** scale, whatever its place in the
  stack said.  APlot therefore lays the two axes themselves in the order
  the stack asks for and hands every drawn object to the one it has to be
  on - all of it by itself, so an ellipse really does come out in front of
  a curve of the right scale, and that curve really does go behind it.
* A curve is more than one drawn thing - its line, the **filled area**
  under it, its error bars, its bars.  They keep their own order among
  themselves but move as **one** object, so something pushed behind a
  filled curve disappears under the filling completely, not only under the
  line.

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
the objects follow the graph wherever it is moved or resized on the page,
and they are stored in `.aplt` files.  The starting line and fill of new objects come
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

* `Axes properties` always carries a **`Right Y axis`** page beside
  `X axis` and `Left Y axis` - range, step, minor ticks, label, fonts,
  colours, direction, scale and distances, all of it separately from the
  left axis.  While no curve is drawn there its `Direction` box reads
  `No right Y axis`; choosing `Standard` brings the axis out with a free
  0 ... 1 scale.  Its grid is left to the main axes, so no line is drawn
  twice.
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
* Dragging an axis **line** (anywhere but its two ends) moves the whole
  graph - see `Moving the whole graph` just below.
* The arrow keys move the **whole plot area** while an axis is selected
  (`Shift`: ten pixels), keeping its size.
* Everything in the diagram - the curves, the legend boxes, the text
  boxes, the drawings and the arrows - keeps its place inside the plot
  area and follows it.
* **Double clicking** an axis line opens `Frame and origin`, where the same
  numbers can be typed in fractions, centimetres or inches; the dialog
  always shows what the pointer has made.
* The size is kept in fractions of the **page**, so it is the same
  whatever the window does and at any zoom, and it is stored in `.aplt`
  files.

### Moving the whole graph

The plot area does not have to stay where the program put it.  **Press
anywhere that is not an object of its own and drag**, and the whole graph
travels with the pointer:

* the **plot area** itself and everything in it,
* any **curve** - grabbing a line no longer opens its properties, it takes
  hold of the graph (the properties are two clicks away now),
* any **axis line** of the frame - the same line whose two ends resize the
  axis, so its middle moves the graph and its ends stretch it,
* the **empty paper** around the graph, the numbers and the labels
  included.

Only the two distances of the origin change.  The length of both axes, the
ranges, the ticks and everything drawn inside - the curves, the legend
boxes, the text boxes, the drawings, the pictures and the arrows - stay as
they are and travel along.  The pointer turns into a four way arrow over
everything that can carry the graph, and the graph is kept inside the
**page**, so it cannot be pushed off it.

The whole drag is **one step**: `Edit > Undo` (`Ctrl/Cmd+Z`) puts the graph
back where it was.  The arrow keys still move it by single pixels while an
axis is selected, and `Frame and origin` still takes the same two distances
as numbers.

While the **pan** or the **zoom** tool of the toolbar is switched on the
canvas belongs to that tool, and dragging does what the tool says instead.

### Resizing the graph on the page

**Right click the paper** - anywhere that is not an object - and the menu
ends with `Resize graph`:

| Item | What it does |
| --- | --- |
| `Smaller` | Takes **ten per cent** off the length of both axes. |
| `Larger` | Puts **ten per cent** on. |
| `Fit to page` | The diagram is made **as large as the page allows**: the whole of it - the plot area *and* the numbers, the axis labels, the title and the legend boxes - is grown and centred until only a narrow strip of white is left around it (half a centimetre, `PAGE_FIT_MARGIN`). |

`Fit to page` measures the **whole drawing**, not the plot area alone:
the numbers, the axis labels, the title, the legend boxes and every text
box, drawing or arrow count, exactly as they do when a picture is
exported.  The two directions are fitted separately, so the same narrow
strip of white is left on all four sides, and the diagram is put in the
middle of the page.  Asking for it twice does nothing the second time -
the program says `The graph already fills the page` - and on a small page
a long title may keep a millimetre or two of the strip for itself, because
a font size is a whole number of points and cannot shrink any further.

`Smaller` and `Larger` keep the **middle** of the graph where it is, so it
grows and shrinks in place, and the graph is kept inside the page.
Everything drawn in the plot area - the curves, the legend boxes, the text
boxes, the drawings, the pictures and the arrows - keeps its place inside it
and follows.  Each choice is **one step** of `Edit > Undo`.

This changes the **graph on the page**, not the page and not the window:
`Resize graph` makes the drawing itself bigger or smaller, the zoom only
changes how large the page is shown, and the size of the page is set by
`Page width` and `Page height` in the settings.

#### The whole look is scaled with the graph

`Resize graph` does not only move the four sides of the plot area: it
scales the **whole drawing**, the way a picture is scaled.  Every size
that is a length or a font on the paper is multiplied by the same factor
as the axes, so a graph whose axes are **twice as long** is drawn with

* a title, axis labels, numbers and legend texts of **twice the font
  size** (12 pt becomes 24 pt),
* curves **twice as thick** and markers twice as large (a line width of
  1.5 becomes 3.0), with their edges to match,
* **tick marks twice as long** - major and minor - and a frame and grid
  lines twice as thick,
* the numbers, the axis labels and the title standing **twice as far**
  from the axes (`Number offset`, `Label offset` and `Title distance`),
* the drawings, the arrows and the text boxes carrying twice as thick
  lines, twice as large arrow heads and twice as large a font.

Nothing else changes: the data, the ranges, the number of ticks, the
colours and the **places** of everything in the plot area stay exactly as
they are.  A place is kept as a fraction of the plot area, so it follows
the plot area by itself and a text box that stood in the top right corner
stands there afterwards too.  Font sizes are whole points, so they are
rounded to the nearest point (and never fall below one).

`Fit to page` scales the sizes in the same way, by however much it had to
grow the axes, so the diagram that fills the page is the same picture, only
larger.  When the two axes did not change by the same amount - `Fit to
page` fits the two directions on their own, and one of them can reach the
edge of the page first - the factor the fonts and the lines follow is the
average of the two, the square root of their product.

**Only this menu does it.**  Dragging the end of an axis, typing an axis
length into `Frame and origin`, moving the graph about, resizing the
window and zooming the view all leave the fonts and the line widths
exactly where the user set them.  And every `Resize graph` choice is a
single step of `Edit > Undo`, sizes included.

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
arrows follow the graph wherever it is moved or resized on the page, while
the head keeps its size in points.  They are stored in `.aplt` files, and the head, size,
line and colour of new arrows come from the `Arrows` tab of the settings.

### Pictures in the diagram

A picture - a logo, a photograph of the sample, a sketch, a screenshot -
can be laid on a diagram in three ways:

* **Paste it.**  Copy a picture anywhere (a browser, a photo program, the
  Finder) and press `Ctrl/Cmd+V` in the diagram window.  If the clipboard
  holds a picture it is laid in the middle of the plot area; when it holds
  no picture, the same keys paste the object that was copied inside the
  program, exactly as before.
* **Drop it.**  Drag a picture file from the Finder (or from any file
  manager) onto the diagram: it is laid **where it was dropped**, and
  several files at once become several pictures, one beside the other.  A
  file that is not a picture is quietly ignored.
* **Choose it.**  The **picture button** of the toolbar - the little framed
  landscape beside the arrow tool - and `Plot > Insert picture...` open a
  file dialog.

A picture is one of the **drawn objects**, so everything that is true of a
drawing is true of it:

* one click **selects** it and shows its eight control points, a second
  click opens its **properties**,
* dragging it **moves** it, dragging a control point **resizes** it, and
  the arrow keys move it by one pixel (with `Shift` by ten),
* `Ctrl/Cmd+C` copies it and `Delete` removes it.

It is laid at its **own proportions** to begin with, taking about a third
of the width of the plot area, and `Its own proportions` in its properties
undoes a squeeze at any time, keeping the width.  A picture is never
rotated, so it has no round handle above it.

#### Resizing with the control points

The eight control points of a selected object do two different things, and
which is which is the same everywhere in the program:

* the four points at the **corners** resize the object **diagonally**, and
* the four points in the **middle of the sides** move that one side only,
  so they squeeze the object or stretch it.

For a **picture** the corners also **keep its proportions**.  A photograph
pulled by a corner therefore stays the photograph it was - never a little
taller or a little wider than it should be - however far the corner is
dragged, and in whatever direction: the object follows the longer of the
two directions the pointer went, and the corner opposite the one being
dragged stays exactly where it is.  The side points are left free on
purpose: they are the way to compress or elongate a picture deliberately.

Holding **Shift** while dragging a corner **turns the rule around**.  On a
picture `Shift` lets the corner resize it freely, and on the drawings -
rectangles, ellipses, triangles and the rest, whose corners resize freely
by default - `Shift` makes the corner keep the proportions the object has
at that moment.  So a circle is kept a circle by holding `Shift`, and a
logo is squashed on purpose in the same way.

The proportions are measured **on the screen**, not in the coordinates of
the axes, so a picture stays undistorted whatever the shape of the plot
area, and it stays undistorted after the graph itself has been made
smaller or larger.

Its **properties** are short: `Frame` draws a line around it (style,
thickness, colour - switched off to begin with) and `Opacity (0-1)` lets
the diagram show through it, which is what a watermark needs.

The picture itself is **written into the `.aplt` file** and into the
**exported matplotlib program**, so a saved graph carries its pictures with
it and the exported program runs anywhere without the original files.  A
photograph larger than 1600 pixels is made smaller first, which keeps the
files a sensible size and is still sharper than any screen.

**Dropping needs one extra package.**  Tk itself cannot take a drop; the
`tkdnd` extension does it, and it comes with `tkinterdnd2`
(`pip install tkinterdnd2`).  Without it everything else works as usual and
pictures arrive by pasting or through the button.

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

`Edit > Duplicate` (`Ctrl/Cmd+D`) is the short way of the same thing: one
key makes the copy, places it a little to the lower right and selects it,
and what was on the clipboard before stays there.

**Two things can be waiting, and the newer one wins.**  An object copied
here is kept inside the program; a picture lies on the clipboard of the
system - put there by `File > Copy figure to the clipboard`, or by any
other program.  `Ctrl/Cmd+V` always takes the one that was copied **last**:

* Between the two ways of copying inside the program the time of the copy
  decides, so copying the figure and then an object pastes the object, and
  the other way round pastes the picture.
* A picture copied in **another** program - a slide in PowerPoint or
  Keynote, a picture in a browser, a drawing in a photo editor - carries no
  time of its own.  For that one the clipboard itself is looked at: if it
  no longer holds what it held when this program last copied, then
  something newer is on it, and that is what is pasted, even when an object
  is still being kept here.  On macOS this is read from the counter the
  system keeps for it; elsewhere the picture is compared with the one that
  was there before.

So copying an ellipse here, then a picture in another program, and pressing
`Ctrl/Cmd+V` lays the **picture** into the diagram - and it goes on doing
so until something is copied here again, which puts the object back in
front.

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
  follows the graph wherever it is moved or resized on the page,
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

**Click a curve twice** to open it: line, bar, slice, filled area, the
staircase - anything drawn for that column.  A single click grabs the graph
and moves it (see `Moving the whole graph`), so the properties need the
second click, exactly like a text box or a drawing.

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
  * `Start angle` (90 degrees is the top) with the `Edge colour` beside it.
  * `Hole (0-0.9)` turns the pie into a **doughnut**, `Edge width` sets the
    line between the slices.
  * `Pull out the first` moves the first slice out of the circle.
  * The two texts of a slice - its **name** and its **number** - form two
    little groups of their own, and **the title of each group is a check
    button**: switched off, that text is not written at all.  A pie with no
    text around it (names off) or a plain pie of bare slices (both off) is
    one click away, and the slices themselves are of course untouched.
  * **The names of the slices** (the texts standing around the pie):
    * A list says **where the names come from**: the text of the first
      column of the table, or the row number.
    * `Distance`: **where they stand**.  `1.0` is the rim of the circle,
      less puts the name on the slice, more beside the pie; they start at
      `1.1`, just outside.
    * `Font size` and `Colour`: their own font, independent of the numbers.
    * `Turn them` lays every name along its own slice instead of standing
      it upright.
  * **The numbers on the slices** (the percentages) have the same:
    * `Distance` (they start at `0.6`, inside the slice), `Font size` and
      `Colour` - white numbers on strong slice colours read best.
    * `Turn them` lays each number along its own slice, which is what makes
      many thin slices readable at all.
    * `Decimals` says how precisely the percentage is written.
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
    the names stand beside the slices instead.  Switching the names off and
    the box on moves them from around the pie into the box, which is what a
    crowded pie of thin slices wants.  Switching `Legend` on gives
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
    `Curve properties` on the **second** click - which is where their font,
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

One window with five tabs: **Title and fonts**, **X axis**, **Left Y
axis**, **Right Y axis** and **Frame and origin**.  All of them are always
there - the right hand page too, even while no curve is drawn against it.

The first page, **Title and fonts**, is exactly the window that
`Plot > Title and fonts...` opens: the title with its font, colour and
distance, and the legend boxes.  Whichever of the two is used, the settings
are the same ones.

#### Direction and Scale

Every axis page begins, just under the tabs, with **two drop-down boxes
side by side** that decide what the axis is at all:

| Direction | What it does |
| --- | --- |
| `No X axis` / `No left Y axis` / `No right Y axis` | That axis is not drawn: no line, no numbers, no label. |
| `Standard` | The usual direction, values growing to the right and upwards. |
| `Reverse` | The axis runs the other way - useful for a wavelength that falls, a depth that grows downwards, an inverted scale. |

| Scale | The spacing of the numbers |
| --- | --- |
| `Linear` | Equal steps (the usual one). |
| `Log 10` | Powers of ten. |
| `Log 2` | Powers of two. |
| `Log (natural)` | Powers of `e`. |

A logarithmic axis cannot reach zero: a range that starts at or below it is
lifted onto the first positive decade.

**A `Log (natural)` axis is read in powers of `e`**: its numbers are
written `e⁰`, `e¹`, `e²` ... rather than 1, 2.718, 7.389, which is what
such an axis is for.  `Log 10` and `Log 2` keep the powers of ten and of
two matplotlib writes for them.

**`Major ticks interval` and `Minor ticks` work there too** - they simply
count in ratios instead of distances.

* **`Major ticks interval`** is how many **powers of the base** lie between
  one major tick and the next, and the line under the box says which base
  that is - `powers of 10`, `powers of 2`, `powers of e`.  On a `Log 10`
  axis `1` gives the usual 1, 10, 100; `2` gives 10⁻⁴, 10⁻², 10⁰ ...;
  `0.5` gives 1, 3.16, 10.  It works with an automatic range as well as
  with one of your own - on a logarithmic axis the spacing of the ticks
  and the range are two separate questions.
* Because a hundred is a sensible interval on a linear axis and an absurd
  one in powers of ten, **each scale keeps its own number**: switching to a
  logarithmic scale offers `1`, switching back brings the linear number
  you had.
* **`Minor ticks`** stand on the **whole numbers** inside the interval -
  2, 3, ... 9 within a decade - because that is what a reader of a
  logarithmic axis looks for.  The number says how many are drawn, and the
  ones kept are those that come nearest to standing at even distances on
  the paper:

  | Between 1 and 10 | The minor ticks |
  | --- | --- |
  | `1` | 3 |
  | `2` | 2 and 5 |
  | `3` | 2, 3 and 6 |
  | `8` | 2, 3, 4, 5, 6, 7, 8, 9 - the whole decade |

  An interval that holds **no whole number** - a `Log 2` axis holds none
  between 1 and 2 - or fewer than were asked for is divided into equal
  parts of the **value** instead: one minor tick is then the half (1.5 on
  a `Log 2` axis), three are the quarters (1.25, 1.5, 1.75).

  As on a linear axis, the minor ticks carry no numbers of their own.

One limit keeps a number typed in haste - or left in an older file, where
the interval meant nothing on a logarithmic axis - from asking the
impossible: an interval **wider than the axis itself** would leave a single
tick or none, so it is read as one power.

The **right hand Y axis** is the one whose Direction says the most:

* while nothing is drawn against it the box reads `No right Y axis`,
* choosing `Standard` or `Reverse` **makes it appear** even with no curve
  of its own - it then simply carries a free scale from **0 to 1**, ready
  for an arrow, a text box or a second reading,
* a curve moved to `y_R` draws that axis whatever the box said, and taking
  the last such curve away lets it disappear again.

#### The three sections of an axis page

Every axis tab has the same three sections, and **the name of each section
is its own check button**:

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
  side by side on one line - and `Major ticks interval` with `Minor ticks`
  (how many minor ones sit between two major ones) on the next line.  On a
  **logarithmic** axis the interval counts powers of the base, and a short
  line under the box says which base; see `Direction and Scale` above,
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

The last tab of the axes dialog, also reachable with
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
  to let the colour around the axes show through.
* **Around the axes**: the colour of the paper the graph sits on, or
  **Transparent around the axes** to leave it away altogether.

Both switches travel into the picture: with the second one ticked, a copied
or saved **PNG, PDF or SVG has no background at all**, so the graph can be
dropped onto a coloured slide or a printed page without a white box around
it.  (JPEG has no transparency of its own and fills it with white.)  The
starting state of both comes from the `Frame` tab of the settings, so every
new diagram can begin transparent if that is what you want.

Clicking any side of the frame on the diagram (the X axis line, the Y axis
line, or the top and right sides when they are drawn) opens this dialog;
the pointer becomes a hand over the frame.

### The menu bar of the diagram window

A diagram window carries the same menu bar as the spreadsheet window
(`APlot`, `File`, `Edit`, `Plot`, `Help`), so files can be opened and saved
and the settings and the documentation can be reached without going back to
the main window.  The `Edit` menu acts on the window it was opened from, so
the very same `Cut`, `Copy`, `Paste` and `Duplicate` work on the selected
object here and on the block of cells there (section 3).  This matters on macOS, where the menu bar always belongs to
the window that has the focus.  In a diagram window the `Plot` menu holds
the commands of that diagram after a separator: `Axes properties...`,
`Frame and origin...`, `Title and fonts...` and `Close this diagram`.

**Size and origin of the axes**

* **Units**: `Fraction of page`, `cm` or `inch`.  Fractions are what is
  really stored; the centimetre and inch values are worked out from the
  size of the page, and the line under the fields always shows the present
  size in centimetres.
* **Width (length of the X axis)** and **Height (length of the Y axis)**.
* **Y axis distance from the left** and **X axis distance from the bottom**
  - the position of the origin inside the window.
* **Default layout** puts back the place a new diagram starts at (the one
  in the `Frame` tab of the settings).  It moves and resizes the plot area
  only: unlike `Resize graph`, it leaves the fonts and the line widths
  alone.  To fill the page, use `Resize graph > Fit to page`.

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

* the **title**: click it on the diagram, use
  `Plot > Title and fonts...`, or open the **first tab of the axes
  dialog** - the same page under another roof,
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


## 3. Taking a step back

Every command that changes something can be taken back, in the sheet and in
the diagram alike.  The `Edit` menu is the same in both windows and always
works on the window it was opened from.

| Menu item | Key | What it does |
| --- | --- | --- |
| Undo | `Cmd/Ctrl+Z` | Takes back the last change - a cell that was written, a drawing that was added, an object that was moved, a whole block that was pasted. |
| Redo | `Shift+Cmd/Ctrl+Z` | Does it again. |
| Cut | `Cmd/Ctrl+X` | The selected object of the diagram, or the highlighted block of cells, goes to the clipboard and away. |
| Copy | `Cmd/Ctrl+C` | The same, without removing anything.  With **nothing** selected in a diagram this copies a picture of the whole diagram. |
| Paste | `Cmd/Ctrl+V` | Puts back what was copied. |
| Duplicate | `Cmd/Ctrl+D` | A second copy at once: in the diagram a little to the lower right of the original, in the sheet in the rows just under the block.  The clipboard is left alone. |

**The line says what it will take back.**  With something on the list the
first line of the menu reads `Undo the drawing`, `Undo the sheet`,
`Undo pasting` and so on, so it is clear beforehand what is about to
happen.  With nothing on the list both lines are grey.

**One command, one step.**  Pasting an object, duplicating it or bringing
it to the front is a single step even though the program does several
things for it, so one `Undo` puts everything back as it was.  The last
60 steps are kept; opening a file starts a fresh, empty list, because the
file itself is the state to go back to.

**What a step remembers.**  A change in a sheet remembers that sheet - its
values, its formulas and its column names; a change in a diagram remembers
that diagram - every curve, axis, drawing, text box and arrow with all of
its properties.  Objects keep their names through `Undo` and `Redo`, so
whatever was selected is still the same object afterwards.

**A cell that is open keeps the keys for its text.**  While a cell or a
text box is being written in, `Cmd/Ctrl+C`, `Cmd/Ctrl+V` and `Cmd/Ctrl+X`
belong to the characters of that text, exactly as everywhere else.


## 4. Files

| Menu item | Key | What it does |
| --- | --- | --- |
| Open graph (.aplt) | `Cmd/Ctrl+O` | Loads a complete APlot document: the data and the diagrams.  This is the **folder button** of the toolbar. |
| Save graph (.aplt) | `Cmd/Ctrl+S` | Saves the data together with every diagram that is open.  This is the **disc button** of the toolbar. |
| Save graph as... | | The same, always asking for a new name. |
| Import data (CSV, TXT, DAT)... | `Cmd/Ctrl+I` | Reads a text data file into the sheet; the separator is recognised automatically.  This is the **arrow button** of the toolbar. |
| Export data (CSV, TXT, DAT)... | `Shift+Cmd/Ctrl+S` | Writes the sheet into a text data file (`.csv`, `.txt`, `.dat`). |
| Export figure (image)... | `Cmd/Ctrl+E` | Writes the graph as a picture (PNG, PDF, SVG, ...), cut out of the page. |
| Export as matplotlib script... | `Shift+Cmd/Ctrl+E` | Writes the diagram as a Python program. |
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

**Opening a file never asks.**  `Open graph`, `Import data` and the
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
  the control points of a selected object are never on it.  What is written
  is the **graph, not the whole page** - the page is cut down to what is
  drawn on it, with a little air around that, exactly as `Copy figure to
  the clipboard` does, so the two ways out of the program give the same
  picture.  The **zoom of the view** never reaches the file either: a
  picture is always of the page at the resolution the settings give it.
* **Copy figure to the clipboard** (`Cmd/Ctrl+C` in the diagram window,
  with nothing selected) puts a 200 dpi picture on the clipboard, ready to
  be pasted into a text editor, a presentation or an e-mail.  Tick
  **`Transparent around the axes`** in `Frame and origin` and that picture
  has **no background at all** - it drops onto a coloured slide without a
  white box around it.  Both switches of that section are carried into the
  picture: the plot area and the paper around it, each on its own.  With an
  object **selected**, the same key copies that object instead, as before -
  so both uses of `Cmd/Ctrl+C` live side by side.  If the system has no
  tool for pictures on the clipboard, the program says where it wrote the
  file instead.
* **Export as matplotlib script...** (`Shift+Cmd/Ctrl+E`) writes a
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

`Import data` reads `.csv`, `.txt`, `.dat`, `.tsv` and `.asc` files (and
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


## 5. Settings

`Settings...` on the toolbar, in the `APlot` menu, or `Cmd+,` in the
application menu on macOS.  The values are written to

    ~/.aplot/config.json

and are read again at every start.  `Restore defaults` puts back the
built-in values.

Settings that belong together stand **side by side on one line** - the width
and the height of the figure, the style and the width of the line, the size
and the edge width of the marker, the colour and the opacity of the fill -
and the boxes are only as wide as what goes into them: a number needs far
less room than a title.

| Tab | Contents |
| --- | --- |
| Windows | Start size of the main window and of the diagram windows, and whether the property windows stay above the diagram. |
| Spreadsheet | Number of rows and column names at start, column width, font size, automatic row adding. |
| Plot | **Page size** (the size of the diagram itself - see `The page`) and resolution, the title pattern (`{x}` is the name of the X column), default Y label, default line style and width, default marker, size and edge width, hollow markers, legend visibility, starting corner, frame and background of the legend boxes, and the default fill under the curves (colour, opacity, pattern, baseline). |
| Fonts | **The font of the diagrams** (first line), then the size and colour of the title, the axis labels, the axis numbers and the legend boxes, and the starting distance (in pixels) of the title, the axis labels and the axis numbers. |
| Grid | Default grid: major and minor lines, colour, style, width, number of minor ticks. |
| Frame | Default frame style, thickness, colour, tick lengths, background colours, and the default size and origin of the axes (as fractions of the page). |
| Text boxes | Font size and colour, frame and background of the text boxes added with the **T** button. |
| Drawings | The shape the drawing tool starts with, and the line style, thickness, colour, fill colour and opacity of new objects. |
| Arrows | The head type the arrow tool starts with, the head size in pixels, and the line style, thickness and colour of new arrows. |
| Data files | Field separator and decimal sign of text data files (`auto` recognises them). |

Window sizes and plot defaults are used by windows opened after saving;
diagrams that are already open keep their settings.

### The font of the diagrams

The first line of the `Fonts` tab is a list of **every font this computer
has**.  Whatever is chosen there is used for the whole diagram - the title,
the axis labels, the numbers on the axes, the legend boxes, the text boxes,
the names on a pie - and, unlike the other settings, it reaches the diagrams
that are **already open** as well, so the effect can be seen at once.

* The starting value is the font the program was drawing with anyway
  (`DejaVu Sans`, which comes with matplotlib), so nothing changes until
  another one is chosen.
* The font is written into the `.aplt` file with the rest of the diagram,
  so a graph opens with the font it was saved with even on a computer whose
  setting says something else.
* The **exported matplotlib program** sets the same font in its first lines,
  so the picture it draws matches the one on the screen.
* A font that this computer does not have is quietly ignored and the usual
  one is kept.


## 6. Typical workflow

1. `Random data` (File menu), `Import data` or type the numbers by hand.
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


## 7. Notes

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
