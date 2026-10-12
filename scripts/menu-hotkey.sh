#!/usr/bin/env bash
# Bind a keyboard shortcut that toggles the start menu.
#
# Usage:  ./scripts/menu-hotkey.sh [KEY]
#   KEY defaults to "<Super>" (the Windows key).
#   Examples: "<Super>", "<Super>s", "<Primary>space"
set -euo pipefail

KEY="${1:-<Super>}"
CMD="${HOME}/.local/bin/metromenu"
CHANNEL="xfce4-keyboard-shortcuts"
PROP="/commands/custom/$KEY"

if [[ ! -x "$CMD" ]]; then
    echo "error: $CMD not found - run scripts/install.sh first" >&2
    exit 1
fi

if xfconf-query -c "$CHANNEL" -p "$PROP" -n -t string -s "$CMD" 2>/dev/null; then
    :
else
    xfconf-query -c "$CHANNEL" -p "$PROP" -t string -s "$CMD"
fi

echo "Bound '$KEY' to the start menu."
echo "If '$KEY' does not respond, make sure it is not already used by"
echo "xfwm4 or the whisker menu in Settings -> Keyboard -> Application Shortcuts."
