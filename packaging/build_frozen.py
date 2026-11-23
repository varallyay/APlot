#!/usr/bin/env python3
"""Build the self-contained APlot - with a Python inside - on the system it
is for, with PyInstaller.  GitHub Actions runs it on a Mac, on Windows and on
Linux (.github/workflows/packages.yml); it can be run by hand as well:

    python -m pip install -r packaging/requirements-frozen.txt   # the exact versions
    python packaging/build_frozen.py                 # Windows
    python packaging/build_frozen.py --self-test     # macOS, Linux: test the result too
    python packaging/build_frozen.py graph.aplt      # the self-test opens it as well

Into packaging/dist/:

  macOS    APlot-<version>-macOS-<arm64|x86_64>.dmg   APlot.app in a disk image
  Windows  APlot-<version>-Windows-portable.zip        the application folder to
           unpack and start - nothing installed, no Python needed
           APlot-<version>-Windows-frozen.zip          the same folder;
           build_packages.py msi --windows makes the .msi of it (on Linux)
  Linux    APlot-<version>-Linux-frozen.tar.gz         the application folder,
           which build_packages.py deb rpm --linux makes the .deb and .rpm of

The application is packaging/frozen/aplot_frozen.py made into a program;
aplot.py travels beside it as a plain file and is what runs (see there).
The built program is tested before it is packed (`APlot --self-test`, see
aplot_frozen.py): always on Windows, with --self-test on macOS and Linux.
"""
import argparse
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
WINDOWS = os.name == "nt"
PORTABLE_MARK = "PORTABLE"      # aplot_frozen.py knows the portable folder by it


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


def write_version_info(path):
    """The version resource of APlot.exe (its Properties > Details)."""
    numbers = [int(part) for part in VERSION.split(".")[:4] if part.isdigit()]
    numbers = tuple(numbers + [0] * (4 - len(numbers)))
    path.write_text(f"""VSVersionInfo(
  ffi=FixedFileInfo(filevers={numbers}, prodvers={numbers}, mask=0x3f, flags=0x0,
                    OS=0x40004, fileType=0x1, subtype=0x0, date=(0, 0)),
  kids=[
    StringFileInfo([StringTable('040904B0', [
      StringStruct('FileDescription', '{NAME} - Data Visualizer'),
      StringStruct('FileVersion', '{VERSION}'),
      StringStruct('InternalName', '{NAME}'),
      StringStruct('LegalCopyright', 'GNU GPL version 3 or later'),
      StringStruct('OriginalFilename', '{NAME}.exe'),
      StringStruct('ProductName', '{NAME}'),
      StringStruct('ProductVersion', '{VERSION}')])]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
""", encoding="utf-8")
    return path


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
               # the picture formats of the Save dialog: matplotlib loads
               # their writers by name, so PyInstaller does not see them
               "--hidden-import", "matplotlib.backends.backend_svg",
               "--hidden-import", "matplotlib.backends.backend_ps",
               "--hidden-import", "matplotlib.backends.backend_pgf",
               # what a Python on the build machine may have, and APlot
               # never uses
               "--exclude-module", "gi", "--exclude-module", "IPython",
               "--exclude-module", "pytest", "--exclude-module", "scipy",
               "--exclude-module", "PyQt5", "--exclude-module", "PyQt6",
               "--exclude-module", "PySide6", "--exclude-module", "wx",
               "--paths", ROOT]
    if sys.platform == "darwin" or os.name == "nt":
        command += ["--icon", icon]
    if WINDOWS:
        command += ["--version-file",
                    write_version_info(WORK / "version_info.txt")]
    try:
        import openpyxl  # noqa: F401  (Excel files; pandas imports it late)
        command += ["--hidden-import", "openpyxl"]
    except ImportError:
        print("   (openpyxl is not installed: no Excel files)")
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


def self_test(out, graphs=()):
    """Start the built program with --self-test (see aplot_frozen.py);
    stops the build when anything in it does not work."""
    if sys.platform == "darwin":
        program = out / f"{NAME}.app" / "Contents" / "MacOS" / NAME
    else:
        program = out / NAME / (NAME + (".exe" if WINDOWS else ""))
    report = WORK / "self_test.txt"
    if report.exists():
        report.unlink()
    print(f"\nSelf-test of {program}", flush=True)
    result = subprocess.run([str(program), "--self-test", str(report)]
                            + [str(Path(one).resolve()) for one in graphs],
                            timeout=600)
    text = (report.read_text(encoding="utf-8") if report.is_file()
            else "(no report written)\n")
    print(text, flush=True)
    if result.returncode != 0:
        sys.exit(f"The self-test of {program} failed (exit code {result.returncode}).")
    if WINDOWS and "package portable" not in text:
        sys.exit("The self-test did not see the folder as the portable APlot.")


PORTABLE_README = """\
APlot {version} for Windows - portable
==================================

Nothing to install, and no Python is needed: APlot carries its own.
Keep this folder together (APlot.exe and _internal), anywhere - on the
desktop, a USB stick, a server or a network share - and start APlot.exe.
Delete the folder to remove it; the registry and the system are never
touched.

The first start: Windows SmartScreen may warn about an unknown publisher
(APlot is not signed) - More info > Run anyway.  When Windows blocks the
unpacked files, unpack again after Properties > Unblock on the downloaded
.zip.

Where APlot writes, for each user who starts it: the settings into
%USERPROFILE%\\.aplot\\config.json, and an update from GitHub (Help > Check
for updates...) - the portable .zip of the new release - unpacked into
%LOCALAPPDATA%\\APlot\\versions\\APlot-<version>; the APlot.exe of this
folder starts that one from then on.  This folder stays as it was unpacked,
so it may be read-only (a folder on a server that several users start APlot
from).

The file PORTABLE marks this folder as the portable APlot (About APlot says
so).  README.md is the full manual.

More:  {homepage}
"""


def write_zip(folder, target, extra=None):
    """`folder` packed as the folder NAME in `target`, with the files of
    `extra` ({name: text}) added beside the program."""
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as zipped:
        for path in sorted(folder.rglob("*")):
            if path.is_file():
                zipped.write(path, Path(NAME) / path.relative_to(folder))
        for name, text in (extra or {}).items():
            zipped.writestr(f"{NAME}/{name}", text)
    return target


def finish_windows(out):
    """The portable .zip, and the folder for the .msi (without PORTABLE)."""
    folder = out / NAME
    (folder / PORTABLE_MARK).unlink(missing_ok=True)
    shutil.copy2(ROOT / "README.md", folder / "README.md")
    shutil.copy2(ROOT / "VERSION_HISTORY.md", folder / "VERSION_HISTORY.md")
    portable = write_zip(folder, DIST / f"{NAME}-{VERSION}-Windows-portable.zip", {
        PORTABLE_MARK: f"{NAME} {VERSION} portable: started from this folder, "
                       "not installed.\n",
        "Read me first.txt": PORTABLE_README.format(
            version=VERSION, homepage=aplot.UPDATE_PAGE).replace("\n", "\r\n")})
    frozen = write_zip(folder, DIST / f"{NAME}-{VERSION}-Windows-frozen.zip")
    print(f"\nBuilt: {frozen}  ({frozen.stat().st_size / 1e6:.1f} MB)")
    return portable


def finish_folder(out, suffix, archive_kind):
    folder = out / NAME
    shutil.copy2(ROOT / "README.md", folder / "README.md")
    shutil.copy2(ROOT / "VERSION_HISTORY.md", folder / "VERSION_HISTORY.md")
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
    parser = argparse.ArgumentParser(
        description="Build the self-contained APlot for this system.")
    parser.add_argument("graphs", nargs="*", metavar="GRAPH.aplt",
                        help="graphs the self-test opens as well")
    parser.add_argument("--self-test", action="store_true",
                        help="test the built program (always done on Windows)")
    options = parser.parse_args()
    DIST.mkdir(parents=True, exist_ok=True)
    icon = icons(WORK / "icons")
    out = pyinstaller(icon)
    if WINDOWS:
        # tested as the portable folder it becomes: PORTABLE beside APlot.exe
        (out / NAME / PORTABLE_MARK).write_text("self-test\n", encoding="utf-8")
    if WINDOWS or options.self_test or options.graphs:
        self_test(out, options.graphs)
    if sys.platform == "darwin":
        built = finish_macos(out)
    elif WINDOWS:
        built = finish_windows(out)
    else:
        built = finish_folder(out, "Linux-frozen.tar.gz", "tar")
    print(f"\nBuilt: {built}  ({built.stat().st_size / 1e6:.1f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
