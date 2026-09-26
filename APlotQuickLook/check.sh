#!/bin/sh
# check.sh - see what macOS makes of one APlot graph.
#
#     sh check.sh "path/to/graph.aplt"
#
# It prints what the system thinks the file is and whether the two
# extensions are known and switched on, then asks Quick Look for the
# thumbnail (it opens in the Finder) and for the preview (a Quick Look
# window; close it to finish).
FILE="${1:-}"
if [ -z "$FILE" ] || [ ! -f "$FILE" ]; then
    echo "usage: sh check.sh \"path/to/graph.aplt\"" >&2
    exit 1
fi

echo "1. The kind of the file (should be hu.feti.aplot.graph):"
mdls -name kMDItemContentType "$FILE" 2>/dev/null || true
echo "   Its first bytes (should begin with PK and mimetypeapplication/x-aplot):"
head -c 60 "$FILE" | tr -c '[:print:]' '.'; echo
echo "   What it carries (thumbnail.png: the icon; preview.pdf: every diagram):"
unzip -l "$FILE" 2>/dev/null | grep "Thumbnails/" || echo "   no pictures inside: open the graph in APlot and save it once"

echo ""
echo "2. The extensions ('+' in front means switched on):"
pluginkit -m -v -i hu.feti.aplot.quicklook.thumbnail || echo "   the thumbnail extension is not registered"
pluginkit -m -v -i hu.feti.aplot.quicklook.preview || echo "   the preview extension is not registered"

echo ""
echo "3. The thumbnail, as Quick Look makes it:"
OUT="$(mktemp -d)"
qlmanage -t -s 512 -o "$OUT" "$FILE" && open "$OUT"

echo ""
echo "4. The preview (close its window to finish):"
qlmanage -p "$FILE" >/dev/null 2>&1
