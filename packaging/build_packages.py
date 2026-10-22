#!/usr/bin/env python3
"""Build the installable packages of APlot from aplot.py, on Linux.

    python3 packaging/build_packages.py                  # deb rpm dmg msi
    python3 packaging/build_packages.py deb rpm          # only these
    python3 packaging/build_packages.py flatpak --linux packaging/dist/APlot-<v>-Linux-frozen.tar.gz
    python3 packaging/build_packages.py msi --windows packaging/dist/APlot-<v>-Windows-frozen.zip

Into packaging/dist/:

  aplot_<version>_all.deb             Debian, Ubuntu, Mint...   (dpkg-deb)
  aplot-<version>-1.noarch.rpm        Fedora, openSUSE, RHEL... (rpmbuild)
  APlot-<version>-macOS-light.dmg     macOS: APlot.app, uses the Mac's Python
  APlot-<version>-Windows-light.msi   Windows: uses the computer's Python
  APlot-<version>-Windows.msi         Windows, self-contained (--windows)
  APlot-<version>-Linux.flatpak       any Linux, self-contained (--linux)

APlot is one Python file.  The .deb and the .rpm depend on the
distribution's python3-tk, numpy, pandas and matplotlib, which the package
manager installs with them.  The *light* .dmg and .msi look for a Python
that has those packages when APlot starts (conda - Anaconda - is the
recommended one, python.org's works as well) and say where to get one when
there is none.  The self-contained ones carry a Python of their own: they
are made of what packaging/build_frozen.py builds with PyInstaller on that
system (on GitHub: .github/workflows/packages.yml), and a self-contained
macOS .dmg comes from build_frozen.py on a Mac directly.

Tools it needs (Ubuntu/Debian names):
  dpkg-deb (dpkg), rpmbuild (rpm), xorriso, wixl (wixl),
  x86_64-w64-mingw32-gcc and -windres (gcc-mingw-w64-x86-64), flatpak
and a Python that can import aplot.py (numpy, pandas, matplotlib, tkinter,
pillow for the icons).
"""
import argparse
import gzip
import hashlib
import io
import os
import shutil
import subprocess
import sys
import tarfile
import textwrap
import time
import uuid
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
import aplot  # noqa: E402  (the program itself: version, icons, desktop files)

VERSION = aplot.APP_VERSION
NAME = aplot.APP_NAME
HOMEPAGE = aplot.UPDATE_PAGE
MAINTAINER = "Zoltán Várallyay <z.varallyay@feti.hu>"
SUMMARY = "Spreadsheet and publication quality diagrams"
DESCRIPTION = """\
APlot is a small desktop program for typing or loading tabular data and
turning it into a Matplotlib diagram whose every detail can be changed by
clicking on it: curves, markers, axes, legends, text boxes, drawings,
arrows and pictures.  A graph is saved with its data, its formulas and its
pictures in one .aplt file; the file managers show its first diagram as
the icon of the file."""
DIST = HERE / "dist"
WORK = HERE / "build"
UPSTREAM = HERE / "upstream"           # LICENSE, APlotQuickLook.zip
PROGRAM = ROOT / "aplot.py"
README = ROOT / "README.md"


def run(command, **options):
    print("   $", " ".join(str(one) for one in command))
    subprocess.run([str(one) for one in command], check=True, **options)


def fresh(folder):
    folder = Path(folder)
    if folder.exists():
        shutil.rmtree(folder)
    folder.mkdir(parents=True)
    return folder


def license_text():
    found = UPSTREAM / "LICENSE"
    if not found.is_file():
        found = ROOT / "LICENSE"
    return found.read_text(encoding="utf-8") if found.is_file() else (
        "APlot is free software, released under the GNU General Public "
        "License, version 3 or later: https://www.gnu.org/licenses/gpl-3.0\n")


def history(limit=8):
    """The newest lines of the version history, for the changelogs."""
    return aplot.version_history(README.read_text(encoding="utf-8"))[:limit]


# ---------------------------------------------------------------------------
# Linux: one tree for /usr, written by APlot's own --install-desktop code
# ---------------------------------------------------------------------------
def linux_tree(kind):
    """The files of a .deb or .rpm below WORK/<kind>/root (as in /usr)."""
    root = fresh(WORK / kind / "root")
    aplot.install_linux_desktop(system=True, prefix="/usr", program=PROGRAM,
                                python="/usr/bin/python3", refresh=False,
                                destdir=root, package=kind)
    # Sushi (the Space bar of GNOME Files) reads its viewers from the home
    # folder of each user only, and nothing in /usr/share/sushi
    shutil.rmtree(root / "usr" / "share" / "sushi", ignore_errors=True)
    docs = root / "usr" / "share" / "doc" / "aplot"
    docs.mkdir(parents=True, exist_ok=True)
    shutil.copy2(README, docs / "README.md")
    for path in root.rglob("*"):
        if path.is_dir():
            os.chmod(path, 0o755)
    return root


def build_deb():
    root = linux_tree("deb")
    docs = root / "usr" / "share" / "doc" / "aplot"
    (docs / "copyright").write_text(textwrap.dedent(f"""\
        Format: https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/
        Upstream-Name: APlot
        Source: {HOMEPAGE}

        Files: *
        Copyright: 2026 Zoltán Várallyay
        License: GPL-3+
         This program is free software: you can redistribute it and/or modify
         it under the terms of the GNU General Public License as published by
         the Free Software Foundation, either version 3 of the License, or
         (at your option) any later version.
         .
         On Debian systems, the complete text of the GNU General Public
         License version 3 can be found in /usr/share/common-licenses/GPL-3.
        """), encoding="utf-8")
    changes = "".join(
        f"aplot ({version}) stable; urgency=medium\n\n"
        + "".join(f"  * {line}\n" for line in textwrap.wrap(what, 72)) + "\n"
        f" -- {MAINTAINER}  {time.strftime('%a, %d %b %Y 12:00:00 +0000', time.strptime(date, '%Y-%m-%d'))}\n\n"
        for version, date, what in history())
    with gzip.GzipFile(docs / "changelog.gz", "wb", mtime=0) as out:
        out.write(changes.encode("utf-8"))
    for path in docs.iterdir():
        os.chmod(path, 0o644)
    size = sum(path.stat().st_size for path in root.rglob("*") if path.is_file())
    control = root / "DEBIAN"
    control.mkdir()
    long = "\n".join(" " + (line or ".") for line in DESCRIPTION.splitlines())
    (control / "control").write_text(textwrap.dedent(f"""\
        Package: aplot
        Version: {VERSION}
        Section: science
        Priority: optional
        Architecture: all
        Depends: python3 (>= 3.10), python3-tk, python3-numpy, python3-pandas, python3-matplotlib
        Recommends: python3-pil, python3-pil.imagetk, python3-openpyxl
        Installed-Size: {(size + 1023) // 1024}
        Maintainer: {MAINTAINER}
        Homepage: {HOMEPAGE}
        Description: {SUMMARY}
        """) + long + "\n", encoding="utf-8")
    sums = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and "DEBIAN" not in path.parts:
            digest = hashlib.md5(path.read_bytes()).hexdigest()
            sums.append(f"{digest}  {path.relative_to(root)}")
    (control / "md5sums").write_text("\n".join(sums) + "\n", encoding="utf-8")
    # Python may leave compiled copies beside the program: they go with it
    (control / "prerm").write_text(
        "#!/bin/sh\nset -e\nrm -rf /usr/share/aplot/__pycache__\nexit 0\n",
        encoding="utf-8")
    for path in control.iterdir():
        os.chmod(path, 0o755 if path.name == "prerm" else 0o644)
    os.chmod(control, 0o755)
    target = DIST / f"aplot_{VERSION}_all.deb"
    run(["dpkg-deb", "--root-owner-group", "-Zxz", "--build", root, target])
    return target


def build_rpm():
    root = linux_tree("rpm")
    license_file = root / "usr" / "share" / "licenses" / "aplot" / "LICENSE"
    license_file.parent.mkdir(parents=True)
    license_file.write_text(license_text(), encoding="utf-8")
    os.chmod(license_file.parent, 0o755)
    files = []
    for path in sorted(root.rglob("*")):
        if path.is_file():
            files.append("/" + str(path.relative_to(root)))
    owned = ["/usr/share/aplot", "/usr/share/doc/aplot", "/usr/share/licenses/aplot"]
    changes = "".join(
        f"* {time.strftime('%a %b %d %Y', time.strptime(date, '%Y-%m-%d'))} "
        f"{MAINTAINER} - {version}-1\n"
        + "".join(f"- {line}\n" for line in textwrap.wrap(what, 72)[:6]) + "\n"
        for version, date, what in history())
    top = fresh(WORK / "rpm" / "top")
    spec = top / "aplot.spec"
    spec.write_text(textwrap.dedent(f"""\
        %global debug_package %{{nil}}
        %global __os_install_post %{{nil}}
        %global __brp_python_bytecompile %{{nil}}
        %define _build_id_links none
        Name:           aplot
        Version:        {VERSION}
        Release:        1
        Summary:        {SUMMARY}
        License:        GPL-3.0-or-later
        URL:            {HOMEPAGE}
        BuildArch:      noarch
        AutoReqProv:    no
        Requires:       python3 >= 3.10
        Requires:       (python3-tkinter or python3-tk)
        Requires:       python3-numpy
        Requires:       python3-pandas
        Requires:       python3-matplotlib
        Requires:       python3-matplotlib-tk
        Recommends:     python3-pillow-tk
        Recommends:     python3-openpyxl
        Provides:       aplot = {VERSION}

        %description
        """) + DESCRIPTION + textwrap.dedent(f"""

        %install
        mkdir -p %{{buildroot}}
        cp -a {root}/. %{{buildroot}}/

        %preun
        rm -rf /usr/share/aplot/__pycache__

        %files
        """) + "".join(f"%dir {one}\n" for one in owned)
        + "".join(f"{one}\n" for one in files)
        + "\n%changelog\n" + changes, encoding="utf-8")
    run(["rpmbuild", "--define", f"_topdir {top}", "--define",
         "_binary_payload w9.xzdio", "-bb", spec])
    built = next((top / "RPMS" / "noarch").glob("aplot-*.rpm"))
    target = DIST / built.name
    shutil.copy2(built, target)
    return target


# ---------------------------------------------------------------------------
# macOS: APlot.app in a disk image
# ---------------------------------------------------------------------------
MAC_README = """\
APlot {version} for macOS
=======================

Installing
----------
Drag APlot onto the Applications folder beside it.

APlot is one Python program, and APlot.app starts it with the Python of
this Mac.  It needs Python 3 with numpy, pandas and matplotlib - the
recommended one is conda, the Anaconda Distribution, which brings all of
them:  https://www.anaconda.com/download
(The Python of python.org works too:  python3 -m pip install numpy pandas
matplotlib.)  APlot.app finds conda in /opt/anaconda3, ~/anaconda3,
~/miniconda3 and ~/miniforge3 by itself.  Without such a Python it says
so and offers the download page.

The first start
---------------
APlot is not signed by an Apple developer account, so macOS stops it the
first time:  "Apple could not verify APlot is free of malware".  Press
Done, then open System Settings > Privacy & Security, scroll down to
"APlot was blocked..." and press Open Anyway (once).  Or type in Terminal:

    xattr -dr com.apple.quarantine /Applications/APlot.app

From then on APlot starts like any other program, and it brings itself up
to date from GitHub (Help > Check for updates...).

The pictures of the graphs in the Finder
----------------------------------------
"APlot Quick Look (optional).zip" holds the Quick Look extensions that
show the first diagram of a graph as its icon, and every diagram with the
Space bar.  They are built with Xcode: unpack it and follow the README.md
inside (sh build.sh, then sh install.sh).

More:  {homepage}
"""


def build_dmg():
    volume = fresh(WORK / "dmg" / "volume")
    bundle = aplot.make_macos_app(volume, program=PROGRAM, platform="darwin",
                                  python="", package="dmg")
    if bundle is None:
        raise RuntimeError("APlot.app could not be built")
    resources = bundle / "Contents" / "Resources"
    for name in ("APlot.icns", f"{aplot.DOCUMENT_ICON_NAME}.icns"):
        if not (resources / name).is_file():
            raise RuntimeError(f"{name} is missing from APlot.app")
    shutil.copy2(README, resources / "README.md")
    (volume / "Applications").symlink_to("/Applications")
    (volume / "Read me first.txt").write_text(
        MAC_README.format(version=VERSION, homepage=HOMEPAGE), encoding="utf-8")
    quicklook = UPSTREAM / "APlotQuickLook.zip"
    if not quicklook.is_file():
        quicklook = ROOT / "APlotQuickLook.zip"      # in the repository
    if quicklook.is_file():
        shutil.copy2(quicklook, volume / "APlot Quick Look (optional).zip")
    for path in volume.rglob("*"):
        if path.is_symlink():
            continue
        os.chmod(path, 0o755 if (path.is_dir() or os.access(path, os.X_OK))
                 else 0o644)
    os.chmod(bundle / "Contents" / "MacOS" / NAME, 0o755)
    target = DIST / f"{NAME}-{VERSION}-macOS-light.dmg"
    if target.exists():
        target.unlink()
    # ISO 9660 with Rock Ridge: macOS mounts it as a disk image, and Rock
    # Ridge keeps the permissions (the launcher must stay executable) and
    # the link to /Applications
    run(["xorriso", "-as", "mkisofs", "-quiet", "-V", f"{NAME} {VERSION}",
         "-R", "-o", target, volume])
    # the same APlot.app as a .zip, for anyone whose Mac does not take the
    # disk image (the zip keeps the permissions as well)
    archive = DIST / f"{NAME}-{VERSION}-macOS-light.app.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as out:
        for path in sorted(bundle.rglob("*")):
            name = str(path.relative_to(volume))
            info = zipfile.ZipInfo(name + ("/" if path.is_dir() else ""),
                                   date_time=time.localtime()[:6])
            mode = path.stat().st_mode
            info.external_attr = (mode & 0xFFFF) << 16
            if path.is_dir():
                info.external_attr |= 0x10
                out.writestr(info, b"")
            else:
                info.compress_type = zipfile.ZIP_DEFLATED
                out.writestr(info, path.read_bytes())
    return target


# ---------------------------------------------------------------------------
# Windows: APlot.exe (the launcher) and aplot.py in an .msi
# ---------------------------------------------------------------------------
def png_image(painter, size):
    from PIL import Image
    return Image.open(io.BytesIO(painter(size))).convert("RGBA")


def write_ico(path, painter):
    image = png_image(painter, 256)
    image.save(path, format="ICO",
               sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64),
                      (128, 128), (256, 256)])


def build_launcher(folder):
    source = HERE / "windows" / "launcher.c"
    write_ico(folder / "aplot.ico", aplot.app_icon_png)
    write_ico(folder / "aplot-document.ico", aplot.document_icon_png)
    major, minor, patch = (list(aplot.version_tuple(VERSION)) + [0, 0, 0])[:3]
    (folder / "launcher.rc").write_text(textwrap.dedent(f"""\
        1 ICON "aplot.ico"
        1 VERSIONINFO
        FILEVERSION {major},{minor},{patch},0
        PRODUCTVERSION {major},{minor},{patch},0
        BEGIN
          BLOCK "StringFileInfo"
          BEGIN
            BLOCK "040904B0"
            BEGIN
              VALUE "CompanyName", "Zoltan Varallyay"
              VALUE "FileDescription", "APlot - data plotting"
              VALUE "FileVersion", "{VERSION}"
              VALUE "InternalName", "APlot"
              VALUE "LegalCopyright", "GNU GPL version 3 or later"
              VALUE "OriginalFilename", "APlot.exe"
              VALUE "ProductName", "APlot"
              VALUE "ProductVersion", "{VERSION}"
            END
          END
          BLOCK "VarFileInfo"
          BEGIN
            VALUE "Translation", 0x409, 1200
          END
        END
        """), encoding="utf-8")
    run(["x86_64-w64-mingw32-windres", "launcher.rc", "-O", "coff",
         "-o", "launcher.res"], cwd=folder)
    run(["x86_64-w64-mingw32-gcc", "-municode", "-mwindows", "-O2", "-static",
         "-s", "-o", folder / "APlot.exe", source, folder / "launcher.res",
         "-lshell32", "-ladvapi32"])
    return folder / "APlot.exe"


def guid(name):
    """A GUID that stays the same from build to build (for the same name)."""
    return "{" + str(uuid.uuid5(uuid.NAMESPACE_URL, f"{HOMEPAGE}#{name}")).upper() + "}"


def unpack_payload(payload, into):
    """A self-contained application folder (a folder, .zip or .tar.gz made
    by build_frozen.py) copied to `into`; the folder holding the program."""
    payload = Path(payload)
    into = fresh(into)
    if payload.is_dir():
        shutil.copytree(payload, into / payload.name, symlinks=True)
    elif payload.suffix == ".zip":
        with zipfile.ZipFile(payload) as archive:
            archive.extractall(into)
    else:
        with tarfile.open(payload) as archive:
            archive.extractall(into, filter="tar")
    folders = [one for one in into.iterdir() if one.is_dir()]
    if len(folders) != 1:
        raise RuntimeError(f"{payload} should hold one folder ({NAME})")
    return folders[0]


def wix_id(prefix, text):
    return f"{prefix}_{hashlib.md5(text.encode('utf-8')).hexdigest()[:20]}"


def wix_tree(folder):
    """The <Directory> elements of every folder below `folder`, each with
    one component for its files (a per-user install keeps the key of every
    component in HKCU, and takes every folder away again on uninstall)."""
    components = []

    def walk(path, depth):
        pad = "  " * depth
        relative = path.relative_to(folder).as_posix()
        lines = []
        files = sorted(one for one in path.iterdir() if one.is_file())
        dirs = sorted(one for one in path.iterdir() if one.is_dir())
        component = wix_id("c", relative or ".")
        components.append(component)
        lines.append(f'{pad}<Component Id="{component}" Guid="{guid(component)}" Win64="yes">')
        for one in files:
            source = one.relative_to(folder).as_posix()
            lines.append(f'{pad}  <File Id="{wix_id("f", source)}" Name="{one.name}" '
                         f'Source="{source}"/>')
        lines.append(f'{pad}  <RegistryValue Root="HKCU" Key="Software\\{NAME}\\Components" '
                     f'Name="{component}" Type="integer" Value="1" KeyPath="yes"/>')
        lines.append(f'{pad}  <RemoveFolder Id="r{component}" On="uninstall"/>')
        lines.append(f"{pad}</Component>")
        for one in dirs:
            inner = one.relative_to(folder).as_posix()
            lines.append(f'{pad}<Directory Id="{wix_id("d", inner)}" Name="{one.name}">')
            lines.extend(walk(one, depth + 1))
            lines.append(f"{pad}</Directory>")
        return lines

    return "\n".join(walk(folder, 6)), components


def build_msi(payload=None):
    """The .msi: the light one (APlot.exe finds the computer's Python), or -
    with `payload`, the Windows folder of build_frozen.py - the
    self-contained one."""
    folder = fresh(WORK / "msi")
    tools = fresh(WORK / "msi-tools")
    build_launcher(tools)
    if payload is not None:
        app = unpack_payload(payload, WORK / "msi-payload")
        shutil.copytree(app, folder, dirs_exist_ok=True)
        if not (folder / "APlot.exe").is_file():
            raise RuntimeError("the Windows folder has no APlot.exe")
        target = DIST / f"{NAME}-{VERSION}-Windows.msi"
        description = f"{NAME} {VERSION} - {SUMMARY} (with its own Python)"
    else:
        shutil.copy2(tools / "APlot.exe", folder / "APlot.exe")
        shutil.copy2(PROGRAM, folder / "aplot.py")
        (folder / aplot.PACKAGE_MARK).write_text("msi\n", encoding="utf-8")
        target = DIST / f"{NAME}-{VERSION}-Windows-light.msi"
        description = f"{NAME} {VERSION} - {SUMMARY}"
    shutil.copy2(README, folder / "README.md")
    (folder / "LICENSE.txt").write_text(license_text(), encoding="utf-8")
    for name in ("aplot.ico", "aplot-document.ico"):
        shutil.copy2(tools / name, folder / name)
    shutil.copy2(tools / "aplot.ico", WORK / "aplot-product.ico")
    tree, components = wix_tree(folder)
    progid = "APlot.Graph"
    refs = "\n".join(f'      <ComponentRef Id="{one}"/>' for one in components)
    wxs = f"""<?xml version="1.0" encoding="utf-8"?>
<Wix xmlns="http://schemas.microsoft.com/wix/2006/wi">
  <Product Id="{guid('product-' + VERSION + ('-frozen' if payload else ''))}" Name="{NAME}"
           Language="1033" Version="{VERSION}" Manufacturer="Zoltan Varallyay"
           UpgradeCode="{guid('upgrade')}">
    <Package InstallerVersion="500" Compressed="yes" InstallScope="perUser"
             Description="{description}" Comments="{HOMEPAGE}"/>
    <MajorUpgrade DowngradeErrorMessage="A newer APlot is installed already."/>
    <Media Id="1" Cabinet="aplot.cab" EmbedCab="yes"/>
    <Icon Id="aplot.ico" SourceFile="{WORK / 'aplot-product.ico'}"/>
    <Property Id="ARPPRODUCTICON" Value="aplot.ico"/>
    <Property Id="ARPURLINFOABOUT" Value="{HOMEPAGE}"/>
    <Property Id="ARPNOREPAIR" Value="1"/>
    <Directory Id="TARGETDIR" Name="SourceDir">
      <Directory Id="LocalAppDataFolder">
        <Directory Id="ProgramsDir" Name="Programs">
          <Directory Id="INSTALLDIR" Name="{NAME}">
{tree}
            <Component Id="Association" Guid="{guid('component-association')}" Win64="yes">
              <RegistryValue Root="HKCU" Key="Software\\{NAME}" Name="InstallDir"
                             Type="string" Value="[INSTALLDIR]" KeyPath="yes"/>
              <RegistryValue Root="HKCU" Key="Software\\Classes\\{aplot.PROJECT_SUFFIX}"
                             Type="string" Value="{progid}"/>
              <RegistryValue Root="HKCU" Key="Software\\Classes\\{aplot.PROJECT_SUFFIX}"
                             Name="Content Type" Type="string" Value="{aplot.PROJECT_MIMETYPE}"/>
              <RegistryValue Root="HKCU" Key="Software\\Classes\\{progid}"
                             Type="string" Value="APlot graph"/>
              <RegistryValue Root="HKCU" Key="Software\\Classes\\{progid}\\DefaultIcon"
                             Type="string" Value="[INSTALLDIR]aplot-document.ico"/>
              <RegistryValue Root="HKCU" Key="Software\\Classes\\{progid}\\shell\\open\\command"
                             Type="string" Value="&quot;[INSTALLDIR]APlot.exe&quot; &quot;%1&quot;"/>
            </Component>
          </Directory>
        </Directory>
      </Directory>
      <Directory Id="ProgramMenuFolder">
        <Component Id="Menu" Guid="{guid('component-menu')}" Win64="yes">
          <Shortcut Id="MenuShortcut" Name="{NAME}" Description="{SUMMARY}"
                    Target="[INSTALLDIR]APlot.exe" WorkingDirectory="INSTALLDIR"/>
          <RegistryValue Root="HKCU" Key="Software\\{NAME}" Name="MenuShortcut"
                         Type="integer" Value="1" KeyPath="yes"/>
        </Component>
      </Directory>
    </Directory>
    <Feature Id="Complete" Title="{NAME}" Level="1">
{refs}
      <ComponentRef Id="Association"/>
      <ComponentRef Id="Menu"/>
    </Feature>
  </Product>
</Wix>
"""
    (WORK / "aplot.wxs").write_text(wxs, encoding="utf-8")
    run(["wixl", "--arch", "x64", "-o", target, WORK / "aplot.wxs"], cwd=folder)
    return target


# ---------------------------------------------------------------------------
# Linux: the self-contained flatpak
# ---------------------------------------------------------------------------
FLATPAK_ID = "hu.feti.APlot"
FLATPAK_RUNTIME = "25.08"        # org.freedesktop.Platform, from Flathub
FLATPAK_REPO = "https://dl.flathub.org/repo/flathub.flatpakrepo"


def build_flatpak(payload):
    """The .flatpak of the self-contained Linux folder of build_frozen.py.

    It needs no runtime here: the files are put together and committed as
    they are (nothing is compiled in the sandbox), and the runtime - the
    freedesktop Platform - is taken from Flathub when it is installed.
    """
    folder = fresh(WORK / "flatpak")
    appdir = folder / "appdir"
    files = appdir / "files"
    app = unpack_payload(payload, WORK / "flatpak-payload")
    (files / "lib").mkdir(parents=True)
    shutil.copytree(app, files / "lib" / "aplot", symlinks=True)
    (files / "bin").mkdir()
    (files / "bin" / "aplot").symlink_to("../lib/aplot/APlot")
    share = files / "share"
    (share / "applications").mkdir(parents=True)
    (share / "applications" / f"{FLATPAK_ID}.desktop").write_text(textwrap.dedent(f"""\
        [Desktop Entry]
        Type=Application
        Name={NAME}
        GenericName=Data plotting
        Comment={SUMMARY}
        Exec=aplot %f
        Icon={FLATPAK_ID}
        Terminal=false
        StartupNotify=true
        Categories=Science;DataVisualization;
        MimeType={aplot.PROJECT_MIMETYPE};
        """), encoding="utf-8")
    for size in aplot.DESKTOP_ICON_SIZES:
        icons = share / "icons" / "hicolor" / f"{size}x{size}"
        (icons / "apps").mkdir(parents=True)
        (icons / "apps" / f"{FLATPAK_ID}.png").write_bytes(aplot.app_icon_png(size))
        (icons / "mimetypes").mkdir()
        (icons / "mimetypes" / f"{FLATPAK_ID}.application-x-aplot.png").write_bytes(
            aplot.document_icon_png(size))
    (share / "mime" / "packages").mkdir(parents=True)
    (share / "mime" / "packages" / f"{FLATPAK_ID}.xml").write_text(
        aplot.DESKTOP_MIME_XML.format(
            mime=aplot.PROJECT_MIMETYPE, name=NAME, suffix=aplot.PROJECT_SUFFIX,
            icon=f"{FLATPAK_ID}.application-x-aplot"), encoding="utf-8")
    releases = "\n".join(
        f'    <release version="{version}" date="{date}"/>'
        for version, date, _what in history(5))
    paragraphs = "".join(f"    <p>{one.strip()}</p>\n"
                         for one in DESCRIPTION.split("\n\n"))
    (share / "metainfo").mkdir()
    (share / "metainfo" / f"{FLATPAK_ID}.metainfo.xml").write_text(f"""\
<?xml version="1.0" encoding="UTF-8"?>
<component type="desktop-application">
  <id>{FLATPAK_ID}</id>
  <name>{NAME}</name>
  <summary>{SUMMARY}</summary>
  <metadata_license>CC0-1.0</metadata_license>
  <project_license>GPL-3.0-or-later</project_license>
  <developer id="hu.feti"><name>Zoltán Várallyay</name></developer>
  <description>
{paragraphs}  </description>
  <launchable type="desktop-id">{FLATPAK_ID}.desktop</launchable>
  <url type="homepage">{HOMEPAGE}</url>
  <categories><category>Science</category><category>DataVisualization</category></categories>
  <provides><mediatype>{aplot.PROJECT_MIMETYPE}</mediatype></provides>
  <content_rating type="oars-1.1"/>
  <releases>
{releases}
  </releases>
</component>
""", encoding="utf-8")
    (appdir / "metadata").write_text(textwrap.dedent(f"""\
        [Application]
        name={FLATPAK_ID}
        runtime=org.freedesktop.Platform/x86_64/{FLATPAK_RUNTIME}
        sdk=org.freedesktop.Sdk/x86_64/{FLATPAK_RUNTIME}
        command=aplot
        """), encoding="utf-8")
    # Tk draws on X11 (XWayland on a Wayland desktop); the graphs are read
    # and written anywhere in the home folder; the updates come from GitHub
    run(["flatpak", "build-finish", "--socket=x11", "--share=ipc",
         "--share=network", "--filesystem=home", "--command=aplot", appdir])
    repo = folder / "repo"
    run(["flatpak", "build-export", "--subject", f"{NAME} {VERSION}", repo, appdir])
    target = DIST / f"{NAME}-{VERSION}-Linux.flatpak"
    run(["flatpak", "build-bundle", f"--runtime-repo={FLATPAK_REPO}", repo,
         target, FLATPAK_ID])
    return target


KINDS = ("deb", "rpm", "dmg", "msi", "flatpak")


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("kinds", nargs="*", metavar="KIND",
                        help=f"the packages to build: {', '.join(KINDS)} "
                             "(deb rpm dmg msi when none is named)")
    parser.add_argument("--windows", metavar="FOLDER_OR_ZIP",
                        help="the self-contained Windows folder of "
                             "build_frozen.py: msi is built of it")
    parser.add_argument("--linux", metavar="FOLDER_OR_TAR",
                        help="the self-contained Linux folder of "
                             "build_frozen.py: flatpak is built of it")
    options = parser.parse_args()
    kinds = options.kinds or ["deb", "rpm", "dmg", "msi"]
    wrong = [one for one in kinds if one not in KINDS]
    if wrong:
        parser.error(f"unknown kind {', '.join(wrong)} (choose from {', '.join(KINDS)})")
    if "flatpak" in kinds and not options.linux:
        parser.error("flatpak needs --linux (the folder or .tar.gz of build_frozen.py)")
    DIST.mkdir(parents=True, exist_ok=True)
    builders = {"deb": build_deb, "rpm": build_rpm, "dmg": build_dmg,
                "msi": lambda: build_msi(options.windows),
                "flatpak": lambda: build_flatpak(options.linux)}
    built = []
    for kind in kinds:
        print(f"== {kind}")
        built.append(builders[kind]())
    print("\nBuilt (APlot " + VERSION + "):")
    for path in built:
        print(f"  {path.relative_to(ROOT)}  ({path.stat().st_size / 1e6:.1f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
