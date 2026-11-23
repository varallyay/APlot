"""The update of the portable APlot, tried for real on Windows (packages.yml,
job frozen):  APlot.exe --script packaging/test_portable_update.py REPORT ZIP

It runs inside a portable APlot.exe - its own Python, with the environment
PyInstaller's bootloader set for it - and does what `Update now` does: the
portable .zip of the release is unpacked for the user (APlot's own
`install_release`), and the new APlot.exe is started from this one the way
`restart_program` starts it.  The new one must start - from the folder of
the user, not from the old one - and pass its self-test.

Writes what it found into REPORT; exit code 0 when all is well.
"""
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def main(report, archive):
    sys.path.insert(0, getattr(sys, "_MEIPASS", ""))
    import aplot
    lines, failed = [], 0
    work = Path(tempfile.mkdtemp(prefix="update test (1) ")).resolve()
    os.environ[aplot.VERSIONS_MARK] = str(work / "versions")
    package = work / "downloads" / "APlot-9.9.9-Windows-portable.zip"
    package.parent.mkdir()
    shutil.copy2(archive, package)
    result = aplot.install_release(package, {"version": "9.9.9"}, kind="portable")
    new = Path(result["command"][0])
    if not (result["installed"] and new.is_file() and new.parent.name == "APlot-9.9.9"):
        lines.append(f"FAIL  unpacked: {result}")
        failed += 1
    else:
        lines.append(f"ok    unpacked into {new.parent}")
        test_report = work / "self-test of the new one.txt"
        # as restart_program starts it: afresh, in the home folder
        env = dict(os.environ, **aplot.RELAUNCH_ENV)
        done = subprocess.run([str(new), "--self-test", str(test_report)], env=env,
                              cwd=str(Path.home()), timeout=600)
        text = (test_report.read_text(encoding="utf-8", errors="replace")
                if test_report.exists() else "(no report)")
        if done.returncode != 0 or "ALL OK" not in text or "APlot-9.9.9" not in text:
            lines.append(f"FAIL  the new APlot.exe (exit code {done.returncode}):\n{text}")
            failed += 1
        else:
            lines.append("ok    the new APlot.exe, started by this one, passed its "
                         "self-test from the folder of the user")
    shutil.rmtree(work, ignore_errors=True)
    with open(report, "w", encoding="utf-8") as handle:
        handle.write(f"portable update test: {'ALL OK' if not failed else 'FAILED'}\n\n"
                     + "\n".join(lines) + "\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))
