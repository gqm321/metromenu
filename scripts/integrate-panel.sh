#!/usr/bin/env bash
# Add a launcher button for the start menu to an Xfce panel.
#
# Usage:  ./scripts/integrate-panel.sh [PANEL_NUMBER]
#
# The script creates a new "launcher" panel plugin whose single item runs the
# win10startmenu command, and inserts it as the first item of the panel so it
# behaves like the Windows "Start" button.
set -euo pipefail

PANEL="${1:-1}"
BIN="${HOME}/.local/bin/win10startmenu"
PANEL_DIR="${HOME}/.config/xfce4/panel"
CHANNEL="xfce4-panel"

if [[ ! -x "$BIN" ]]; then
    echo "error: $BIN not found - run scripts/install.sh first" >&2
    exit 1
fi

if ! command -v xfconf-query >/dev/null 2>&1; then
    echo "error: xfconf-query not found (is this an Xfce session?)" >&2
    exit 1
fi

# Find the next free plugin id.
max_id=0
while IFS= read -r line; do
    id="${line#/plugins/plugin-}"
    [[ "$id" =~ ^[0-9]+$ ]] || continue
    (( id > max_id )) && max_id=$id
done < <(xfconf-query -c "$CHANNEL" -p /plugins -l 2>/dev/null || true)
new_id=$((max_id + 1))

# Create the launcher item inside launcher-<plugin-id>/.
launcher_dir="$PANEL_DIR/launcher-$new_id"
mkdir -p "$launcher_dir"
item="w10sm-$(date +%s)-$$.desktop"
cat > "$launcher_dir/$item" <<EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=开始菜单
Name[en]=Start Menu
Comment=Windows 10 风格开始菜单
Exec=$BIN
Icon=win10startmenu
Terminal=false
StartupNotify=false
Categories=Utility;X-XFCE;
EOF

# Register the plugin and its item.
xfconf-query -c "$CHANNEL" -p "/plugins/plugin-$new_id" -n -t string -s launcher
xfconf-query -c "$CHANNEL" -p "/plugins/plugin-$new_id/items" -n -t string -s "$item"

# Prepend the new plugin id to the panel's plugin list.
mapfile -t ids < <(xfconf-query -c "$CHANNEL" -p "/panels/panel-$PANEL/plugin-ids" -v 2>/dev/null | grep -E '^[0-9]+$' || true)
args=()
for value in "$new_id" "${ids[@]}"; do
    args+=(-t int -s "$value")
done
xfconf-query -c "$CHANNEL" -p "/panels/panel-$PANEL/plugin-ids" "${args[@]}"

# Bring the panel back with the new button.
xfce4-panel --restart >/dev/null 2>&1 || true

echo "Added start menu button as panel plugin-$new_id (panel $PANEL)."
echo "Remove it with: scripts/uninstall.sh --panel"
