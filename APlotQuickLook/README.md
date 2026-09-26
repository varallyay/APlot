# APlot Quick Look

This folder builds **APlot Quick Look.app**, a small macOS program. It adds two
Quick Look extensions for APlot graphs (`.aplt` files):

| Extension | What it does |
| --- | --- |
| **APlot Thumbnail** | The Finder shows the picture of the graph - its **first diagram** - as the file's icon, in every view. The same icon appears in the Open and Save dialogs and in Spotlight. |
| **APlot Preview** | Pressing the **Space bar** on a graph (or choosing *Quick Look*) shows **every diagram** of the file, one page each, about 1024 points large. Scroll to page through them; the sidebar button of the Quick Look window shows them all small. |

The extensions show what APlot stores in the file when it saves it, inside
the `.aplt` ZIP container: `Thumbnails/thumbnail.png` for the icon and
`Thumbnails/preview.pdf` (one page for each diagram) for the Space bar. A
graph that has no PDF yet - saved by an APlot before it came in - shows its
one picture in the Space bar instead. The extensions never run Python, and
they never change a file.

## What it needs

* **macOS 12 (Monterey) or later.**
* **Xcode**, free in the App Store. The command line tools alone may also be
  enough (`xcode-select --install`). Nothing else: no extra libraries and no
  Xcode project.
* **APlot's newer `aplot.py`** (the one that saves `.aplt` as a ZIP
  container). Graphs saved by an older APlot have no picture yet. Open them
  and save them once.

## Building and installing

In Terminal, in this folder:

    sh build.sh
    sh install.sh

* `build.sh` compiles the three small parts: the two extensions and the
  program that carries them. It then signs them and writes
  `build/APlot Quick Look.app`.
* `install.sh` copies the program to `~/Applications` and switches both
  extensions on. It also clears the old pictures from Quick Look's memory and
  opens the program once. That first opening is how macOS registers the
  program. A short message says it is installed, and that is all it ever
  shows.

Then look at a graph in the Finder. The picture can take a moment to appear
the first time.

It is best to also rebuild **APlot.app** with the new `aplot.py`:

    python3 aplot.py --make-app

That gives every graph an icon of its own, even one that has no picture yet.
It also lets a double click on a graph open it in APlot.

To see what macOS makes of one file:

    sh check.sh "path/to/graph.aplt"

`check.sh` shows:

* what the system thinks the file is,
* whether the extensions are switched on,
* the thumbnail and the preview, exactly as Quick Look makes them.

To remove everything again:

    sh uninstall.sh

## After an update of this folder

Build and install again, then save each graph once more with the new
APlot:

    sh build.sh
    sh install.sh

The Space bar preview of every diagram needs both the rebuilt extension and
a graph saved by the new `aplot.py`, which stores the PDF of the diagrams.
An extension built earlier shows only the first picture, and so does a
graph saved earlier, until it is saved again. `check.sh` lists what a
graph carries (`thumbnail.png`, `preview.pdf`).

## When the pictures do not appear

1. **Is the extension switched on?** Open *System Settings > General >
   Login Items & Extensions*, then *Quick Look* (on macOS 13–14: *Privacy &
   Security > Extensions > Quick Look*). Both *APlot Thumbnail* and *APlot
   Preview* must be ticked.
2. **Was the graph saved by the new APlot?** An old graph is plain JSON and
   has no picture. `check.sh` prints the first bytes of the file: a new graph
   begins with `PK` and `mimetypeapplication/x-aplot`.
3. **Does macOS know the kind of file?** `check.sh` should report
   `hu.feti.aplot.graph`. If it reports something beginning with `dyn.`, open
   *APlot Quick Look* once from `~/Applications` (or run
   `python3 aplot.py --make-app`), then log out and back in.
4. **Is Finder still using its old pictures?** Run `qlmanage -r cache`, then
   restart the Finder: hold `Option`, right-click its Dock icon and choose
   *Relaunch*.
5. **Signing.** By default `build.sh` signs the program "for this Mac only".
   Xcode calls this *Sign to Run Locally*, and it is normally enough on your
   own Mac. If macOS still ignores the extensions (`check.sh` shows no `+`
   in front of them), sign them with a free development certificate instead:
   * In Xcode, open *Settings > Accounts*, add your Apple ID, select it and
     choose *Manage Certificates... > + > Apple Development*.
   * Find the name of the certificate:
     `security find-identity -v -p codesigning`
   * Build and install again with that name:

         SIGN_IDENTITY="Apple Development: Your Name (ABCDE12345)" sh build.sh
         sh install.sh

6. **Is the Space-bar preview only as large as an icon?** Then Quick Look
   is showing the icon (the thumbnail), not the preview. Check that
   *APlot Preview* is switched on (see 1.); `check.sh` shows it with a `+`.
7. **What Quick Look itself says**, while pressing the Space bar on a graph:

       log stream --predicate 'subsystem == "com.apple.quicklook"' --level debug

## Giving it to other people

A program signed "for this Mac only", or with a development certificate,
runs on the Mac that built it. Two ways to share it:

* Everyone builds it on their own Mac from this folder.
* Sign it with a **Developer ID** certificate (Apple Developer Program,
  USD 99 a year), then have Apple notarize it:

      SIGN_IDENTITY="Developer ID Application: Your Name (ABCDE12345)" sh build.sh
      ditto -c -k --keepParent "build/APlot Quick Look.app" APlotQuickLook.zip
      xcrun notarytool submit APlotQuickLook.zip --keychain-profile "notary" --wait
      xcrun stapler staple "build/APlot Quick Look.app"

  Before the first submission, save the Apple ID for `notarytool` once with
  `xcrun notarytool store-credentials "notary"`.

`ARCHS="arm64 x86_64" sh build.sh` builds a program that runs on both Apple
silicon and Intel Macs.

## What is in this folder

| File | What it is |
| --- | --- |
| `Sources/Shared/APlotArchive.swift` | Finds the picture and the PDF inside the `.aplt` ZIP container. It reads only the directory at the end of the file and the one entry asked for. No ZIP library is needed. |
| `Sources/Thumbnail/ThumbnailProvider.swift` | The Finder icon: the picture, fitted into the size the Finder asks for. |
| `Sources/Preview/PreviewProvider.swift` | The Space bar preview: the PDF of every diagram, shown by Quick Look as a document (or the picture, for a graph without the PDF). |
| `Sources/Host/main.swift` | The program that carries the two extensions. It only says that it is installed. |
| `Resources/*.plist` | What each part tells macOS. The kind of file is `hu.feti.aplot.graph` (`.aplt`, `application/x-aplot`). The extensions are `hu.feti.aplot.quicklook.thumbnail` and `hu.feti.aplot.quicklook.preview`. |
| `Resources/Extension.entitlements` | The App Sandbox. Quick Look requires it for its extensions. |
| `build.sh`, `install.sh`, `check.sh`, `uninstall.sh` | See above. |

The name `hu.feti.aplot.graph` must be the same here as in `aplot.py`
(`PROJECT_UTI`). APlot.app announces it as the owner of the file type. This
program only borrows the declaration, in case APlot.app has not been rebuilt
yet.
