"""Desktop actions used by the start menu context menus.

These wrap the small Linux-specific operations that do not belong in the
widget code: revealing a desktop file, editing it, copying the launch command,
adding a shortcut to the desktop and adding a launcher to the Xfce panel.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import time
from pathlib import Path

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gdk, Gio, GLib, Gtk  # noqa: E402


def _which(program: str) -> str | None:
    return shutil.which(program)


def _spawn(argv: list[str]) -> None:
    try:
        subprocess.Popen(
            argv,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
        )
    except OSError:
        pass


def desktop_directory() -> Path:
    special = GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_DESKTOP)
    if special:
        return Path(special)
    return Path(os.path.expanduser("~/Desktop"))


def reveal_file(path: Path) -> bool:
    """Show ``path`` in the file manager (selecting it when supported)."""
    try:
        uri = Gio.File.new_for_path(str(path)).get_uri()
        connection = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        connection.call_sync(
            "org.freedesktop.FileManager1",
            "/org/freedesktop/FileManager1",
            "org.freedesktop.FileManager1",
            "ShowItems",
            GLib.Variant("(ass)", ([uri], "")),
            None,
            Gio.DBusCallFlags.NONE,
            2000,
            None,
        )
        return True
    except GLib.Error:
        pass
    # Fall back to opening the containing directory.
    parent = str(path.parent)
    for manager in ("thunar", "nemo", "nautilus", "dolphin", "pcmanfm", "caja", "xdg-open"):
        if _which(manager):
            _spawn([manager, parent])
            return True
    return False


def edit_file(path: Path) -> bool:
    for editor in ("mousepad", "gedit", "kate", "xed", "xdg-open"):
        if _which(editor):
            _spawn([editor, str(path)])
            return True
    return False


def copy_text(text: str) -> None:
    clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
    clipboard.set_text(text, -1)
    clipboard.store()


def add_to_desktop(desktop_file: Path) -> bool:
    """Copy a .desktop entry to the user's desktop directory."""
    target_dir = desktop_directory()
    try:
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / desktop_file.name
        shutil.copyfile(desktop_file, target)
        os.chmod(target, 0o755)
        # Mark it trusted so file managers do not refuse to run it.
        try:
            Gio.File.new_for_path(str(target)).set_attribute_string(
                "metadata::trusted", "yes"
            )
        except Exception:
            pass
        return True
    except OSError:
        return False


def _xfconf_get(*args: str) -> str:
    try:
        result = subprocess.run(
            ["xfconf-query", *args], capture_output=True, text=True, timeout=5
        )
        return result.stdout
    except (OSError, subprocess.SubprocessError):
        return ""


def _xfconf_set(args: list[str]) -> bool:
    try:
        subprocess.run(["xfconf-query", *args], capture_output=True, timeout=5)
        return True
    except (OSError, subprocess.SubprocessError):
        return False


def add_launcher_to_panel(desktop_file: Path, panel: int = 1) -> bool:
    """Register a launcher item for ``desktop_file`` on an Xfce panel."""
    if not _which("xfconf-query"):
        return False

    # Find the next free plugin id.
    listing = _xfconf_get("-c", "xfce4-panel", "-p", "/plugins", "-l")
    max_id = 0
    for line in listing.splitlines():
        name = line.rsplit("plugin-", 1)[-1]
        if name.isdigit():
            max_id = max(max_id, int(name))
    plugin_id = max_id + 1

    launcher_dir = Path.home() / ".config/xfce4/panel" / f"launcher-{plugin_id}"
    try:
        launcher_dir.mkdir(parents=True, exist_ok=True)
        item_name = f"w10sm-{int(time.time())}-{os.getpid()}.desktop"
        shutil.copyfile(desktop_file, launcher_dir / item_name)
    except OSError:
        return False

    if not _xfconf_set(
        ["-c", "xfce4-panel", "-p", f"/plugins/plugin-{plugin_id}", "-n", "-t", "string", "-s", "launcher"]
    ):
        return False
    _xfconf_set(
        ["-c", "xfce4-panel", "-p", f"/plugins/plugin-{plugin_id}/items", "-n", "-t", "string", "-s", item_name]
    )

    # Append the plugin to the panel's list.
    current = _xfconf_get("-c", "xfce4-panel", "-p", f"/panels/panel-{panel}/plugin-ids", "-v")
    ids = [line for line in current.splitlines() if line.strip().isdigit()]
    args = ["-c", "xfce4-panel", "-p", f"/panels/panel-{panel}/plugin-ids"]
    for value in [*ids, str(plugin_id)]:
        args += ["-t", "int", "-s", value]
    _xfconf_set(args)

    _spawn(["xfce4-panel", "--restart"])
    return True
