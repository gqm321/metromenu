#!/usr/bin/env bash
# Remove the start menu.
#
# Usage:  ./scripts/uninstall.sh [--panel] [--hotkey] [--purge]
#   --panel    remove the panel launcher button (if present)
#   --hotkey   remove keyboard shortcut(s) pointing at the menu
#   --purge    also delete the saved layout (~/.config/win10startmenu)
set -euo pipefail

PREFIX="${PREFIX:-$HOME/.local}"
SHARE="$PREFIX/share"
APP_DIR="$SHARE/win10startmenu"
BIN_DIR="$PREFIX/bin"
BIN="$BIN_DIR/win10startmenu"
PANEL_DIR="${HOME}/.config/xfce4/panel"
CHANNEL="xfce4-panel"

WANT_PANEL=0
WANT_HOTKEY=0
WANT_PURGE=0
for arg in "$@"; do
    case "$arg" in
        --panel) WANT_PANEL=1 ;;
        --hotkey) WANT_HOTKEY=1 ;;
        --purge) WANT_PURGE=1 ;;
        *) echo "unknown option: $arg" >&2; exit 2 ;;
    esac
done

remove_panel_button() {
    command -v xfconf-query >/dev/null 2>&1 || return 0
    local removed=0

    # Launcher-plugin buttons created by integrate-panel.sh.
    for dir in "$PANEL_DIR"/launcher-*; do
        [[ -d "$dir" ]] || continue
        if grep -rqs "^Exec=$BIN\$" "$dir" 2>/dev/null; then
            local id="${dir##*/launcher-}"
            drop_plugin_id "$id"
            xfconf-query -c "$CHANNEL" -p "/plugins/plugin-$id" -r -R >/dev/null 2>&1 || true
            rm -rf "$dir"
            removed=1
        fi
    done

    # Native panel plugin created by install-panel-plugin.sh.
    while IFS= read -r line; do
        local id="${line#/plugins/plugin-}"
        [[ "$id" =~ ^[0-9]+$ ]] || continue
        if [[ "$(xfconf-query -c "$CHANNEL" -p "/plugins/plugin-$id" -v 2>/dev/null)" == "win10startmenu" ]]; then
            drop_plugin_id "$id"
            xfconf-query -c "$CHANNEL" -p "/plugins/plugin-$id" -r -R >/dev/null 2>&1 || true
            removed=1
        fi
    done < <(xfconf-query -c "$CHANNEL" -p /plugins -l 2>/dev/null | grep -E '^/plugins/plugin-[0-9]+$' || true)

    if [[ "$removed" == "1" ]]; then
        xfce4-panel --restart >/dev/null 2>&1 || true
        echo "Removed panel button(s)."
    fi
}

drop_plugin_id() {
    local id="$1" panel prop
    for panel in 1 2 3 4; do
        prop="/panels/panel-$panel/plugin-ids"
        xfconf-query -c "$CHANNEL" -p "$prop" >/dev/null 2>&1 || continue
        mapfile -t ids < <(xfconf-query -c "$CHANNEL" -p "$prop" -v | grep -E '^[0-9]+$' || true)
        local args=()
        for value in "${ids[@]}"; do
            [[ "$value" == "$id" ]] && continue
            args+=(-t int -s "$value")
        done
        [[ ${#args[@]} -gt 0 ]] && xfconf-query -c "$CHANNEL" -p "$prop" "${args[@]}" || true
    done
}

remove_hotkeys() {
    command -v xfconf-query >/dev/null 2>&1 || return 0
    while IFS= read -r prop; do
        [[ -n "$prop" ]] || continue
        xfconf-query -c xfce4-keyboard-shortcuts -p "$prop" -r >/dev/null 2>&1 || true
        echo "Removed shortcut $prop"
    done < <(xfconf-query -c xfce4-keyboard-shortcuts -p /commands/custom -l -v 2>/dev/null \
        | awk -v cmd="$BIN" '$NF == cmd { print $1 }')
}

[[ "$WANT_PANEL" == "1" ]] && remove_panel_button
[[ "$WANT_HOTKEY" == "1" ]] && remove_hotkeys

rm -rf "$APP_DIR"
rm -f "$BIN"
rm -f "$SHARE/applications/win10startmenu.desktop"
for size in 16 22 24 32 48 64 128 256; do
    rm -f "$SHARE/icons/hicolor/${size}x${size}/apps/win10startmenu.png"
done
rm -f "$SHARE/icons/hicolor/scalable/apps/win10startmenu.svg"

# Native panel plugin module + descriptor.
find "$HOME/.local" -path "*/xfce4/panel/plugins/libwin10startmenu.so" -delete 2>/dev/null || true
rm -f "$HOME/.local/share/xfce4/panel/plugins/win10startmenu.desktop"

command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database "$SHARE/applications" >/dev/null 2>&1 || true
command -v gtk-update-icon-cache >/dev/null 2>&1 && gtk-update-icon-cache -q -t -f "$SHARE/icons/hicolor" >/dev/null 2>&1 || true

if [[ "$WANT_PURGE" == "1" ]]; then
    rm -rf "${XDG_CONFIG_HOME:-$HOME/.config}/win10startmenu"
    echo "Removed saved layout."
fi

echo "Uninstalled."
