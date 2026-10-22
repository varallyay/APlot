#!/usr/bin/env python3
"""Build the self-contained APlot - with a Python inside - on the system it
is for, with PyInstaller.  GitHub Actions runs it on a Mac, on Windows and on
Linux (.github/workflows/packages.yml); it can be run by hand as well:

    python -m pip install pyinstaller numpy pandas matplotlib pillow openpyxl tkinterdnd2
    python packaging/build_frozen.py

Into packaging/dist/:

  macOS    APlot-<version>-macOS-<arm64|x86_64>.dmg   APlot.app in a disk image
  Windows  APlot-<version>-Windows-frozen.zip          the application folder;
           build_packages.py msi --payload makes the .msi of it (on Linux)
  Linux    APlot-<version>-Linux-frozen.tar.gz         the application folder,
           which the flatpak (packaging/flatpak) is made of

The application is packaging/frozen/aplot_frozen.py made into a program;
aplot.py travels beside it as a plain file and is what runs (see there).
"""
import io
import os
import platform
import plistlib
import shutil
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
import aplot  # noqa: E402

VERSION = aplot.APP_VERSION
NAME = aplot.APP_NAME
DIST = HERE / "dist"
WORK = HERE / "build" / "frozen"
BOOTSTRAP = HERE / "frozen" / "aplot_frozen.py"


def run(command, **options):
    print("   $", " ".join(str(one) for one in command))
    subprocess.run([str(one) for one in command], check=True, **options)


def icons(folder):
    """The icons this system wants, drawn by APlot itself."""
    folder.mkdir(parents=True, exist_ok=True)
    if sys.platform == "darwin":
        (folder / "APlot.icns").write_bytes(aplot.icns_bytes(aplot.app_icon_png))
        (folder / f"{aplot.DOCUMENT_ICON_NAME}.icns").write_bytes(
            aplot.icns_bytes(aplot.document_icon_png))
        return folder / "APlot.icns"
    from PIL import Image
    if os.name == "nt":
        for name, painter in (("aplot.ico", aplot.app_icon_png),
                              ("aplot-document.ico", aplot.document_icon_png)):
            image = Image.open(io.BytesIO(painter(256))).convert("RGBA")
            image.save(folder / name, format="ICO",
                       sizes=[(16, 16), (24, 24), (32, 32), (48, 48),
                              (64, 64), (128, 128), (256, 256)])
        return folder / "aplot.ico"
    (folder / "aplot.png").write_bytes(aplot.app_icon_png(256))
    return folder / "aplot.png"


def pyinstaller(icon):
    """PyInstaller: the folder (Windows, Linux) or APlot.app (macOS)."""
    out = WORK / "out"
    if out.exists():
        shutil.rmtree(out)
    command = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean",
               "--windowed", "--name", NAME,
               "--distpath", out, "--workpath", WORK / "pyinstaller",
               "--specpath", WORK,
               "--add-data", f"{ROOT / 'aplot.py'}{os.pathsep}.",
               "--add-data", f"{ROOT / 'README.md'}{os.pathsep}.",
               "--hidden-import", "PIL._tkinter_finder",
               # what a Python on the build machine may have, and APlot
               # never uses
               "--exclude-module", "gi", "--exclude-module", "IPython",
               "--exclude-module", "pytest", "--exclude-module", "scipy",
               "--exclude-module", "PyQt5", "--exclude-module", "PyQt6",
               "--exclude-module", "PySide6", "--exclude-module", "wx",
               "--paths", ROOT]
    if sys.platform == "darwin" or os.name == "nt":
        command += ["--icon", icon]
    try:
        import tkinterdnd2  # noqa: F401  (dropping pictures onto a diagram)
        command += ["--collect-all", "tkinterdnd2"]
    except ImportError:
        print("   (tkinterdnd2 is not installed: no dropping of pictures)")
    if sys.platform == "darwin":
        command += ["--osx-bundle-identifier", aplot.APP_ID]
    run(command + [BOOTSTRAP])
    return out


def finish_macos(out):
    bundle = out / f"{NAME}.app"
    contents = bundle / "Contents"
    # what Finder needs to know: the kind of file, its icon, the version
    ours = plistlib.loads(aplot.app_plist(NAME).encode("utf-8"))
    with open(contents / "Info.plist", "rb") as handle:
        info = plistlib.load(handle)
    for key in ("CFBundleDocumentTypes", "UTExportedTypeDeclarations"):
        info[key] = ours[key]
    info.update(CFBundleShortVersionString=VERSION, CFBundleVersion=VERSION,
                CFBundleDisplayName=NAME, NSHighResolutionCapable=True,
                NSHumanReadableCopyright="GNU GPL version 3 or later")
    with open(contents / "Info.plist", "wb") as handle:
        plistlib.dump(info, handle)
    shutil.copy2(WORK / "icons" / f"{aplot.DOCUMENT_ICON_NAME}.icns",
                 contents / "Resources" / f"{aplot.DOCUMENT_ICON_NAME}.icns")
    # changed after PyInstaller signed it: signed again (ad hoc)
    run(["codesign", "--force", "--deep", "--sign", "-", bundle])
    volume = WORK / "volume"
    if volume.exists():
        shutil.rmtree(volume)
    volume.mkdir(parents=True)
    shutil.copytree(bundle, volume / bundle.name, symlinks=True)
    (volume / "Applications").symlink_to("/Applications")
    (volume / "Read me first.txt").write_text(MAC_README.format(
        version=VERSION, homepage=aplot.UPDATE_PAGE), encoding="utf-8")
    quicklook = HERE / "upstream" / "APlotQuickLook.zip"
    if not quicklook.is_file():
        quicklook = ROOT / "APlotQuickLook.zip"
    if quicklook.is_file():
        shutil.copy2(quicklook, volume / "APlot Quick Look (optional).zip")
    arch = platform.machine() or "mac"
    target = DIST / f"{NAME}-{VERSION}-macOS-{arch}.dmg"
    if target.exists():
        target.unlink()
    # hdiutil now and then finds the volume "busy" on a build machine: tried
    # a few times before giving up
    for attempt in range(4):
        try:
            run(["hdiutil", "create", "-volname", f"{NAME} {VERSION}",
                 "-srcfolder", volume, "-ov", "-format", "UDZO", target])
            break
        except subprocess.CalledProcessError:
            if attempt == 3:
                raise
            import time
            time.sleep(10)
    return target


MAC_README = """\
APlot {version} for macOS
=======================

Drag APlot onto the Applications folder beside it.  This APlot carries its
own Python with everything it needs - nothing else has to be installed.

The first start: APlot is not signed by an Apple developer account, so
macOS stops it the first time ("Apple could not verify APlot is free of
malware").  Press Done, open System Settings > Privacy & Security, scroll
down to "APlot was blocked" and press Open Anyway (once).  Or in Terminal:

    xattr -dr com.apple.quarantine /Applications/APlot.app

APlot brings itself up to date from GitHub (Help > Check for updates...);
the new versions go to ~/Library/Application Support/APlot.

"APlot Quick Look (optional).zip": the extensions that show the first
diagram of a graph as its icon in the Finder, and every diagram with the
Space bar - built with Xcode (see the README.md inside).

More:  {homepage}
"""


def finish_folder(out, suffix, archive_kind):
    folder = out / NAME
    shutil.copy2(ROOT / "README.md", folder / "README.md")
    target = DIST / f"{NAME}-{VERSION}-{suffix}"
    if archive_kind == "zip":
        with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as zipped:
            for path in sorted(folder.rglob("*")):
                if path.is_file():
                    zipped.write(path, Path(NAME) / path.relative_to(folder))
    else:
        with tarfile.open(target, "w:gz") as tarred:
            tarred.add(folder, arcname=NAME)
    return target


def main():
    DIST.mkdir(parents=True, exist_ok=True)
    icon = icons(WORK / "icons")
    out = pyinstaller(icon)
    if sys.platform == "darwin":
        built = finish_macos(out)
    elif os.name == "nt":
        built = finish_folder(out, "Windows-frozen.zip", "zip")
    else:
        built = finish_folder(out, "Linux-frozen.tar.gz", "tar")
    print(f"\nBuilt: {built}  ({built.stat().st_size / 1e6:.1f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
