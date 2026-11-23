"""The update helper of the .msi, tried for real on Windows (packages.yml,
job msi-test):  APlot.exe --script packaging/test_msi_update.py REPORT MSI

It runs inside the installed APlot.exe - its own Python - and uses APlot's
own `install_release`, as `Help > Check for updates > Update now` does:

* the helper waits until the APlot that asked for the update has ended (a
  second APlot.exe stands in for it here) and only then runs msiexec;
* it is started in the folder of the installed APlot, as from the Start
  menu - the folder the installer replaces - and in a downloads folder whose
  name has spaces and brackets;
* a good package is installed and the program started with the graph that
  was open; a broken one leaves the reason (the code of msiexec) for the next
  start of APlot, and APlot is started all the same.

The program started at the end is a small batch file here, which writes
down what it was given; that APlot.exe itself starts is the self-test's work.
Writes what it found into REPORT; exit code 0 when all is well.
"""
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

lines = []
report_file = None


def say(text):
    """Noted, and written down at once: a test that hangs still tells how far it got."""
    lines.append(text)
    if report_file:
        with open(report_file, "w", encoding="utf-8") as handle:
            handle.write("msi update test: RUNNING\n\n" + "\n".join(lines) + "\n")


def until(test, seconds):
    deadline = time.time() + seconds
    while time.time() < deadline:
        if test():
            return True
        time.sleep(0.5)
    return False


def main(report, msi):
    global report_file
    report_file = report
    sys.path.insert(0, getattr(sys, "_MEIPASS", ""))
    import aplot
    exe = Path(sys.executable).resolve()
    work = Path(tempfile.mkdtemp(prefix="update test (1) ")).resolve()
    aplot.UPDATE_FAILED = work / "update-failed.txt"
    sleeper = work / "sleep.py"
    sleeper.write_text("import time\ntime.sleep(8)\n", encoding="utf-8")
    started = work / "started.txt"
    program = work / "fake APlot.cmd"
    # `start` runs a batch file as `cmd /K`, which stays open after it; `exit`
    # ends it - else Start-Process -Wait in packages.yml waits for it forever
    program.write_text(f'@echo off\r\n>>"{started}" echo started %1\r\nexit\r\n',
                       encoding="ascii")
    graph = work / "my graph (2).aplt"
    graph.write_text("graph", encoding="utf-8")
    failed = 0

    for case, package_bytes in (("good", Path(msi).read_bytes()), ("broken", b"not an msi")):
        folder = work / f"downloads {case}"
        folder.mkdir()
        package = folder / "APlot-9.9.9-Windows.msi"
        package.write_bytes(package_bytes)
        started.unlink(missing_ok=True)
        aplot.UPDATE_FAILED.unlink(missing_ok=True)
        # another APlot.exe stands in for the APlot that asked for the update
        stand_in = subprocess.Popen([str(exe), "--script", str(sleeper)])
        result = aplot.install_release(package, {"version": "9.9.9"}, kind="msi",
                                       executable=exe, pid=stand_in.pid)
        env = dict(os.environ, **aplot.RELAUNCH_ENV, **result["env"])
        env["APLOT_UPDATE_PROGRAM"] = str(program)
        env[result["open_variable"]] = str(graph)
        # started in the folder of the installed APlot (as from the Start menu)
        helper = subprocess.Popen(result["command"], creationflags=0x08000000, env=env,
                                  cwd=str(exe.parent), close_fds=True)
        say(f"..    {case}: helper {helper.pid} started, waiting for APlot {stand_in.pid}")
        log = Path(result["env"]["APLOT_UPDATE_LOG"])
        time.sleep(4)
        if log.exists() or started.exists():
            say(f"FAIL  {case}: msiexec ran while the APlot it waits for was running")
            failed += 1
        stand_in.wait()
        say(f"..    {case}: APlot {stand_in.pid} ended")
        if not until(started.exists, 300):
            say(f"FAIL  {case}: the program was not started after the installer "
                f"(helper {'still running' if helper.poll() is None else 'ended'}, "
                f"installer log {'written' if log.exists() else 'not written'})")
            failed += 1
            continue
        time.sleep(1)
        given = started.read_text(encoding="ascii", errors="replace").strip()
        if given != f'started "{graph}"':
            say(f"FAIL  {case}: the program was given {given!r}, not the graph")
            failed += 1
        reason = (aplot.UPDATE_FAILED.read_text(encoding="utf-8-sig", errors="replace")
                  if aplot.UPDATE_FAILED.exists() else "")
        if case == "good" and reason:
            say(f"FAIL  good: the installer failed: {reason}")
            if log.exists():
                raw = log.read_bytes()
                tail = raw.decode("utf-16" if raw[:2] == b"\xff\xfe" else "latin-1",
                                  errors="replace").splitlines()[-30:]
                say("      " + "\n      ".join(tail))
            failed += 1
        elif case == "broken" and "ended with the code 16" not in reason:
            say(f"FAIL  broken: the reason was not left for the next start: {reason!r}")
            failed += 1
        else:
            say(f"ok    {case}: installer run after APlot ended, program started with "
                f"the graph" + (f"; reason kept: ...{reason[-40:]!r}" if reason else ""))
    if failed:
        say(f"the files of the test are kept in {work}")
    else:
        shutil.rmtree(work, ignore_errors=True)
    text = (f"msi update test: {'ALL OK' if not failed else 'FAILED'}\n\n"
            + "\n".join(lines) + "\n")
    with open(report, "w", encoding="utf-8") as handle:
        handle.write(text)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))
