#!/usr/bin/env bash
# Install the Windows 10 style start menu into the user's home directory.
#
# Usage:  ./scripts/install.sh [--panel] [--hotkey] [--hotkey KEY]
#   --panel        also add a launcher button to the Xfce panel
#   --hotkey       bind a keyboard shortcut to toggle the menu
#   --hotkey KEY   use KEY as the shortcut (default: <Super>)
set -euo pipefail

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PREFIX="${PREFIX:-$HOME/.local}"
SHARE="$PREFIX/share"
APP_DIR="$SHARE/win10startmenu"
BIN_DIR="$PREFIX/bin"

WANT_PANEL=0
WANT_HOTKEY=0
HOTKEY="<Super>"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --panel) WANT_PANEL=1 ;;
        --hotkey) WANT_HOTKEY=1 ;;
        --hotkey=*) WANT_HOTKEY=1; HOTKEY="${1#*=}" ;;
        --key) WANT_HOTKEY=1; HOTKEY="${2:-<Super>}"; shift ;;
        *) echo "unknown option: $1" >&2; exit 2 ;;
    esac
    shift
done

echo "Installing to $PREFIX"
mkdir -p "$APP_DIR" "$BIN_DIR" "$SHARE/applications"

rm -rf "$APP_DIR/win10startmenu" "$APP_DIR/assets"
cp -r "$SRC/win10startmenu" "$APP_DIR/win10startmenu"
cp -r "$SRC/assets" "$APP_DIR/assets"
find "$APP_DIR" -name '__pycache__' -type d -prune -exec rm -rf {} + 2>/dev/null || true

# -- command wrapper -------------------------------------------------
cat > "$BIN_DIR/win10startmenu" <<EOF
#!/usr/bin/env bash
export W10SM_HOME="$APP_DIR"
export PYTHONPATH="$APP_DIR\${PYTHONPATH:+:\$PYTHONPATH}"
exec python3 -m win10startmenu "\$@"
EOF
chmod +x "$BIN_DIR/win10startmenu"

# -- desktop entry ---------------------------------------------------
sed "s|@EXEC@|$BIN_DIR/win10startmenu|g" \
    "$SRC/data/win10startmenu.desktop" > "$SHARE/applications/win10startmenu.desktop"

# -- icons -----------------------------------------------------------
for size in 16 22 24 32 48 64 128 256; do
    icon_dir="$SHARE/icons/hicolor/${size}x${size}/apps"
    mkdir -p "$icon_dir"
    cp "$SRC/assets/win10startmenu-${size}.png" "$icon_dir/win10startmenu.png"
done
mkdir -p "$SHARE/icons/hicolor/scalable/apps"
cp "$SRC/assets/win10startmenu.svg" "$SHARE/icons/hicolor/scalable/apps/win10startmenu.svg"

command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database "$SHARE/applications" >/dev/null 2>&1 || true
command -v gtk-update-icon-cache >/dev/null 2>&1 && gtk-update-icon-cache -q -t -f "$SHARE/icons/hicolor" >/dev/null 2>&1 || true

echo "  installed command : $BIN_DIR/win10startmenu"
echo "  installed entry   : $SHARE/applications/win10startmenu.desktop"

if [[ "$WANT_PANEL" == "1" ]]; then
    "$SRC/scripts/integrate-panel.sh"
fi

if [[ "$WANT_HOTKEY" == "1" ]]; then
    "$SRC/scripts/menu-hotkey.sh" "$HOTKEY"
fi

echo
echo "Done. Start the menu with: win10startmenu"
if [[ "$WANT_PANEL" == "0" ]]; then
    echo "To add it to the panel later:  $SRC/scripts/integrate-panel.sh"
fi
if [[ "$WANT_HOTKEY" == "0" ]]; then
    echo "To bind a shortcut later:      $SRC/scripts/menu-hotkey.sh '<Super>'"
fi
