// main.swift - "APlot Quick Look.app", the carrier of the two extensions.
//
// macOS only loads Quick Look extensions that live inside an application,
// and it registers them the first time that application is opened.  This
// one has nothing else to do: it says so, and quits.

import AppKit

let application = NSApplication.shared
application.setActivationPolicy(.regular)
application.activate(ignoringOtherApps: true)

let alert = NSAlert()
alert.messageText = "APlot Quick Look is installed"
alert.informativeText = """
    The Finder now shows the picture of every APlot graph (.aplt) as its \
    icon, and the Space bar shows it large.

    If the pictures do not appear, switch the two APlot extensions on in \
    System Settings > General > Login Items & Extensions > Quick Look \
    (on older systems: System Settings > Privacy & Security > Extensions).

    Graphs saved by an older APlot carry no picture yet: open them and save \
    them once.

    This window can be closed; nothing has to keep running.
    """
alert.addButton(withTitle: "OK")
alert.runModal()
