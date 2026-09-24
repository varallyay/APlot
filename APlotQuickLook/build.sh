#!/bin/sh
# build.sh - build "APlot Quick Look.app": the Finder thumbnails and the
# Space bar preview of APlot graphs (.aplt files).
#
#     sh build.sh
#
# It needs Xcode (free in the App Store) or at least its command line tools
# (xcode-select --install), and macOS 12 or later.  The result is written
# into build/; install.sh copies it into ~/Applications and switches it on.
#
# Two settings can be given in front of the command:
#
#     SIGN_IDENTITY="Apple Development: Your Name (TEAMID)" sh build.sh
#         signs with a certificate instead of "for this Mac only" (see the
#         README: needed if macOS ignores the extensions, and to give the
#         program to others)
#     ARCHS="arm64 x86_64" sh build.sh
#         builds for both kinds of Mac (the default is this Mac's kind)
set -eu
cd "$(dirname "$0")"

NAME="APlot Quick Look"
MINIMUM="12.0"
SIGN="${SIGN_IDENTITY:--}"
ARCHS="${ARCHS:-$(uname -m)}"

say() { printf '%s\n' "$*"; }
fail() { say "build.sh: $*" >&2; exit 1; }

[ "$(uname -s)" = "Darwin" ] || fail "this builds a macOS program; run it on a Mac."
command -v xcrun >/dev/null 2>&1 \
    || fail "xcrun was not found: install Xcode, or run  xcode-select --install"
SDK="$(xcrun --sdk macosx --show-sdk-path)" \
    || fail "no macOS SDK was found: open Xcode once, or run  xcode-select --install"
SWIFTC="$(xcrun --sdk macosx --find swiftc)" || fail "swiftc was not found"

APP="build/$NAME.app"
rm -rf build
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources" "$APP/Contents/PlugIns" \
         build/objects

# compile OUTPUT MODULE KIND SOURCE...   (KIND: app or extension)
# One slice per architecture, joined into one program by lipo.
compile() {
    output="$1"; module="$2"; kind="$3"; shift 3
    slices=""
    for arch in $ARCHS; do
        slice="build/objects/$module-$arch"
        say "  compiling $module ($arch)"
        if [ "$kind" = extension ]; then
            # an extension has no main(): the system's NSExtensionMain
            # starts it and creates the class named in its Info.plist
            "$SWIFTC" -sdk "$SDK" -target "$arch-apple-macos$MINIMUM" \
                -O -whole-module-optimization -module-name "$module" \
                -parse-as-library -application-extension \
                -Xlinker -application_extension \
                -Xlinker -e -Xlinker _NSExtensionMain \
                "$@" -o "$slice"
        else
            "$SWIFTC" -sdk "$SDK" -target "$arch-apple-macos$MINIMUM" \
                -O -whole-module-optimization -module-name "$module" \
                "$@" -o "$slice"
        fi
        slices="$slices $slice"
    done
    # shellcheck disable=SC2086
    lipo -create $slices -output "$output"
}

# extension MODULE PLIST SOURCE...
extension() {
    module="$1"; plist="$2"; shift 2
    appex="$APP/Contents/PlugIns/$module.appex"
    mkdir -p "$appex/Contents/MacOS"
    cp "Resources/$plist" "$appex/Contents/Info.plist"
    compile "$appex/Contents/MacOS/$module" "$module" extension "$@"
}

say "Building $NAME for $ARCHS (macOS $MINIMUM or later)"
extension APlotThumbnail Thumbnail-Info.plist \
    Sources/Shared/APlotArchive.swift Sources/Thumbnail/ThumbnailProvider.swift
extension APlotPreview Preview-Info.plist \
    Sources/Shared/APlotArchive.swift Sources/Preview/PreviewProvider.swift
cp Resources/Host-Info.plist "$APP/Contents/Info.plist"
printf 'APPL????' > "$APP/Contents/PkgInfo"
compile "$APP/Contents/MacOS/APlotQuickLook" APlotQuickLook app Sources/Host/main.swift
rm -rf build/objects

# the icon of APlot, if aplot.py lies next to this folder (only a nicety:
# the program is opened once and is never seen again)
APLOT="${APLOT:-../aplot.py}"
if [ -f "$APLOT" ] && command -v python3 >/dev/null 2>&1 \
        && command -v iconutil >/dev/null 2>&1; then
    if python3 "$APLOT" --icon build/icon.png >/dev/null 2>&1; then
        mkdir -p build/icon.iconset
        for size in 16 32 128 256; do
            sips -z $size $size build/icon.png \
                --out "build/icon.iconset/icon_${size}x${size}.png" >/dev/null
            double=$((size * 2))
            sips -z $double $double build/icon.png \
                --out "build/icon.iconset/icon_${size}x${size}@2x.png" >/dev/null
        done
        cp build/icon.png build/icon.iconset/icon_512x512.png
        if iconutil -c icns build/icon.iconset -o "$APP/Contents/Resources/AppIcon.icns"; then
            /usr/libexec/PlistBuddy -c "Add :CFBundleIconFile string AppIcon" \
                "$APP/Contents/Info.plist" >/dev/null 2>&1 || true
        fi
        rm -rf build/icon.iconset build/icon.png
    fi
fi

# signing: the extensions first, the application around them last
if [ "$SIGN" = "-" ]; then
    say "  signing for this Mac only"
    options=""
    stamp="--timestamp=none"
else
    say "  signing as: $SIGN"
    options="--options runtime"          # what notarization asks for
    stamp="--timestamp"
fi
for appex in "$APP"/Contents/PlugIns/*.appex; do
    # shellcheck disable=SC2086
    codesign --force --sign "$SIGN" $options $stamp \
        --entitlements Resources/Extension.entitlements "$appex"
done
# shellcheck disable=SC2086
codesign --force --sign "$SIGN" $options $stamp "$APP"
codesign --verify --deep --strict "$APP" || fail "the signature does not verify"

say ""
say "Built: $(pwd)/$APP"
say "Next:  sh install.sh"
