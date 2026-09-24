#!/bin/sh
# install.sh - put "APlot Quick Look.app" into ~/Applications and switch
# its two Quick Look extensions on.
#
#     sh install.sh
#     DEST=/Applications sh install.sh      (for every user of this Mac)
#
# It builds the program first when build/ does not hold it yet.
set -eu
cd "$(dirname "$0")"

NAME="APlot Quick Look"
DEST="${DEST:-$HOME/Applications}"
LSREGISTER=/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister

[ -d "build/$NAME.app" ] || sh ./build.sh

mkdir -p "$DEST"
TARGET="$DEST/$NAME.app"
if [ -d "$TARGET" ]; then
    for appex in "$TARGET"/Contents/PlugIns/*.appex; do
        pluginkit -r "$appex" >/dev/null 2>&1 || true
    done
    rm -rf "$TARGET"
fi
ditto "build/$NAME.app" "$TARGET"
echo "Copied to $TARGET"

# tell macOS about the kind of file and the extensions now, instead of
# waiting until it finds them by itself
if [ -x "$LSREGISTER" ]; then "$LSREGISTER" -f "$TARGET" || true; fi
for appex in "$TARGET"/Contents/PlugIns/*.appex; do
    identifier="$(/usr/libexec/PlistBuddy -c 'Print :CFBundleIdentifier' \
                  "$appex/Contents/Info.plist")"
    pluginkit -a "$appex" || true
    pluginkit -e use -i "$identifier" || true
    echo "Switched on: $identifier"
done

# Quick Look forgets the pictures it made before, so that it asks again
qlmanage -r >/dev/null 2>&1 || true
qlmanage -r cache >/dev/null 2>&1 || true

# opening the program once is what registers it for good
open "$TARGET"

echo ""
echo "Done.  Save a graph with the new APlot and look at it in the Finder."
echo "To check one file:   sh check.sh \"path/to/graph.aplt\""
