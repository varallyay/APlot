# Building the APlot packages

The whole story is in the main README, section **Installable packages**.
In short:

| Command | Where | Makes |
| --- | --- | --- |
| `python3 packaging/build_packages.py` | Linux | `.deb`, `.rpm`, light `.dmg`, light `.msi` |
| `python packaging/build_frozen.py` | macOS | self-contained `.dmg` |
| `python packaging/build_frozen.py` | Windows | the folder of the self-contained `.msi` |
| `python packaging/build_frozen.py` | Linux | the folder of the `.flatpak` |
| `python3 packaging/build_packages.py msi --windows <zip>` | Linux | self-contained `.msi` |
| `python3 packaging/build_packages.py flatpak --linux <tar.gz>` | Linux | `.flatpak` |

`.github/workflows/packages.yml` runs all of it on GitHub when a version
tag (`v1.3.6`) is pushed and puts the packages on the Releases page.

* `frozen/aplot_frozen.py` - the program PyInstaller builds; it starts
  `aplot.py` (the newer of the bundled one and an update in the user's folder)
* `windows/launcher.c` - `APlot.exe` of the light `.msi`; it finds a Python
  with numpy, pandas and matplotlib (conda first) and starts `aplot.py`

The results go to `packaging/dist/`, the work files to `packaging/build/`
(both can be deleted).  `packaging/upstream/` may hold `LICENSE` and
`APlotQuickLook.zip`; otherwise they are taken from the repository root.
