# Building the APlot packages

The whole story is in the main README, section **Installable packages**.
In short - every released package carries its own Python:

| Command | Where | Makes |
| --- | --- | --- |
| `python packaging/build_frozen.py` | Windows | the portable `.zip`, and the folder of the `.msi` |
| `python packaging/build_frozen.py --self-test` | macOS | the `.dmg` (of the Mac's processor) |
| `python packaging/build_frozen.py --self-test` | Linux | the folder of the `.deb` and the `.rpm` |
| `python3 packaging/build_packages.py deb rpm --linux <tar.gz>` | Linux | the `.deb` and the `.rpm` |
| `python3 packaging/build_packages.py msi --windows <zip>` | Linux | the `.msi` |

The exact versions of the Python packages are in `requirements-frozen.txt`
(`python -m pip install -r packaging/requirements-frozen.txt`).
`build_frozen.py` tests the built program (`APlot --self-test REPORT`)
before packing it - always on Windows, with `--self-test` elsewhere.

`.github/workflows/packages.yml` builds all of them on GitHub when a
version tag (`v1.6.4`) is pushed, installs and tests the `.deb` (Ubuntu),
the `.rpm` (Fedora) and the `.msi` (Windows), and then publishes the
release with every package at once (the releases are immutable: a
published release takes no more files).

* `frozen/aplot_frozen.py` - the program PyInstaller builds; it starts
  `aplot.py`, tells APlot what kind of package it is (`PORTABLE` or
  `PACKAGED` beside the program), hands a portable APlot over to a newer
  copy of the user, and runs the helper scripts of the `.deb` and `.rpm`
  (`--script`)
* `windows/launcher.c` - `APlot.exe` of the light `.msi`; it finds a Python
  with numpy, pandas and matplotlib (conda first) and starts `aplot.py`

`build_packages.py` without `--linux` / `--windows` still makes the light
packages that use the computer's Python (`deb rpm dmg msi`), and
`flatpak --linux <tar.gz>` a flatpak; they are not released.

The results go to `packaging/dist/`, the work files to `packaging/build/`
(both can be deleted).  `packaging/upstream/` may hold `LICENSE` and
`APlotQuickLook.zip`; otherwise they are taken from the repository root.
