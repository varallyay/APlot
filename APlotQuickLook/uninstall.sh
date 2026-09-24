#!/bin/sh
# uninstall.sh - take "APlot Quick Look.app" away again.
#
#     sh uninstall.sh
#     DEST=/Applications sh uninstall.sh    (if it was installed there)
NAME="APlot Quick Look"
DEST="${DEST:-$HOME/Applications}"
TARGET="$DEST/$NAME.app"
if [ -d "$TARGET" ]; then
    for appex in "$TARGET"/Contents/PlugIns/*.appex; do
        pluginkit -r "$appex" >/dev/null 2>&1 || true
    done
    rm -rf "$TARGET"
    echo "Removed $TARGET"
else
    echo "Nothing to remove at $TARGET"
fi
qlmanage -r >/dev/null 2>&1 || true
qlmanage -r cache >/dev/null 2>&1 || true
