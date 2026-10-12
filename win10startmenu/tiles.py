"""Metro tile widgets and a small grid packer.

Each tile is a square/rectangular block with an accent colour, an icon and a
label.  A few tiles are *live*: they refresh themselves on a timer (the clock
and the system monitor) which is what gives the menu its Windows 10 feel.
"""

from __future__ import annotations

import time

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gdk, GLib, Gtk  # noqa: E402

from . import icons  # noqa: E402
from .config import SIZE_ICONS, SIZE_PIXELS, TILE_SIZES  # noqa: E402

GAP = 3  # margin around every tile -> 6px visual gutter

SPECIAL_TILES = {
    "@clock": "时钟",
    "@date": "日历",
    "@system": "系统",
    "@recent": "最近使用",
}

SPECIAL_ICONS = {
    "@clock": "preferences-system-time",
    "@date": "x-office-calendar",
    "@system": "utilities-system-monitor",
    "@recent": "document-open-recent",
}


def tile_pixels(size: str) -> tuple[int, int]:
    return SIZE_PIXELS.get(size, SIZE_PIXELS["medium"])


def _shade(color: str, factor: float) -> str:
    """Lighten (factor > 1) or darken (factor < 1) a ``#rrggbb`` colour."""
    try:
        rgba = Gdk.RGBA()
        if not rgba.parse(color):
            return color
    except Exception:
        return color
    rgba.red = min(1.0, rgba.red * factor)
    rgba.green = min(1.0, rgba.green * factor)
    rgba.blue = min(1.0, rgba.blue * factor)
    return rgba.to_string()


class TileWidget(Gtk.EventBox):
    """A single clickable Metro tile."""

    def __init__(self, tile: dict, app, on_launch, on_context_menu):
        super().__init__()
        self.tile = tile
        self.app = app
        self.on_launch = on_launch
        self.on_context_menu = on_context_menu
        self.kind = tile["id"][1:] if tile["id"].startswith("@") else "app"
        self._base_color = tile.get("color") or "#0078d7"
        self._live_source = 0
        self._provider = Gtk.CssProvider()

        width, height = tile_pixels(tile.get("size", "medium"))
        self.set_size_request(width - GAP * 2, height - GAP * 2)
        self.set_margin_start(GAP)
        self.set_margin_end(GAP)
        self.set_margin_top(GAP)
        self.set_margin_bottom(GAP)
        self.set_events(
            Gdk.EventMask.BUTTON_PRESS_MASK
            | Gdk.EventMask.ENTER_NOTIFY_MASK
            | Gdk.EventMask.LEAVE_NOTIFY_MASK
        )
        self.set_hexpand(False)
        self.set_vexpand(False)

        self._box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self._box.set_margin_start(10)
        self._box.set_margin_end(10)
        self._box.set_margin_top(10)
        self._box.set_margin_bottom(8)
        self.add(self._box)

        icon_size = SIZE_ICONS.get(tile.get("size", "medium"), 40)
        self._icon = Gtk.Image()
        pixbuf = icons.load_icon(self._icon_name(), icon_size)
        if pixbuf is not None:
            self._icon.set_from_pixbuf(pixbuf)
        else:
            self._icon.set_from_icon_name("application-x-executable", Gtk.IconSize.DIALOG)
        self._icon.set_halign(Gtk.Align.START)
        self._icon.set_valign(Gtk.Align.START)

        self._title = Gtk.Label()
        self._title.set_xalign(0.0)
        self._title.set_ellipsize(3)  # Pango.EllipsizeMode.END
        self._title.set_line_wrap(False)
        self._title.get_style_context().add_class("tile-title")

        self._subtitle = Gtk.Label()
        self._subtitle.set_xalign(0.0)
        self._subtitle.set_ellipsize(3)
        self._subtitle.get_style_context().add_class("tile-subtitle")
        self._subtitle.set_no_show_all(True)

        set_title = self._display_name()
        self._title.set_text(set_title)

        if tile.get("size") != "small":
            self._box.pack_start(self._icon, False, False, 0)
            self._box.pack_end(self._subtitle, False, False, 0)
            self._box.pack_end(self._title, False, False, 0)
        else:
            self._box.set_halign(Gtk.Align.CENTER)
            self._box.set_valign(Gtk.Align.CENTER)
            self._box.pack_start(self._icon, True, True, 0)
            self._icon.set_halign(Gtk.Align.CENTER)
            self._icon.set_valign(Gtk.Align.CENTER)

        self._apply_color(self._base_color)

        self.connect("button-press-event", self._on_button_press)
        self.connect("enter-notify-event", self._on_enter)
        self.connect("leave-notify-event", self._on_leave)

        if self.kind in ("clock", "date", "system"):
            self._start_live()

    # -- helpers --------------------------------------------------------
    def _icon_name(self) -> str:
        if self.kind in SPECIAL_ICONS:
            return SPECIAL_ICONS["@" + self.kind]
        if self.app is not None:
            return self.app.icon or ""
        return ""

    def _display_name(self) -> str:
        if self.kind in SPECIAL_TILES:
            return SPECIAL_TILES["@" + self.kind]
        if self.app is not None:
            return self.app.name
        return self.tile["id"]

    def _apply_color(self, color: str) -> None:
        try:
            self._provider.load_from_data(
                f"* {{ background-color: {color}; border-radius: 2px; }}".encode("utf-8")
            )
        except GLib.Error:
            return
        ctx = self.get_style_context()
        ctx.add_provider(self._provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    # -- events ---------------------------------------------------------
    def _on_button_press(self, _widget, event: Gdk.EventButton) -> bool:
        if event.button == 1:
            self.on_launch(self)
            return True
        if event.button == 3:
            self.on_context_menu(self, event)
            return True
        return False

    def _on_enter(self, _widget, _event) -> bool:
        self._apply_color(_shade(self._base_color, 1.25))
        return False

    def _on_leave(self, _widget, _event) -> bool:
        self._apply_color(self._base_color)
        return False

    def set_color(self, color: str) -> None:
        self._base_color = color
        self._apply_color(color)

    # -- live content ---------------------------------------------------
    def _start_live(self) -> None:
        self._refresh_live()
        self._live_source = GLib.timeout_add_seconds(1, self._refresh_live)

    def _refresh_live(self) -> bool:
        if self.kind == "clock":
            self._title.set_text(time.strftime("%H:%M"))
            self._subtitle.set_text(time.strftime("%Y-%m-%d %A"))
            self._subtitle.show()
        elif self.kind == "date":
            self._title.set_text(time.strftime("%d"))
            self._subtitle.set_text(time.strftime("%B"))
            self._subtitle.show()
        elif self.kind == "system":
            cpu, mem = _read_system_load()
            self._title.set_text(f"CPU {cpu:.0f}%")
            self._subtitle.set_text(f"内存 {mem:.0f}%")
            self._subtitle.show()
        return True

    def stop(self) -> None:
        if self._live_source:
            GLib.source_remove(self._live_source)
            self._live_source = 0


def _read_system_load() -> tuple[float, float]:
    cpu = mem = 0.0
    try:
        with open("/proc/loadavg", "r", encoding="utf-8") as handle:
            load1 = float(handle.read().split()[0])
        cpu = min(100.0, load1 / (GLib.get_num_processors() or 1) * 100.0)
    except Exception:
        pass
    try:
        info: dict[str, int] = {}
        with open("/proc/meminfo", "r", encoding="utf-8") as handle:
            for line in handle:
                key, _, rest = line.partition(":")
                info[key] = int(rest.strip().split()[0])
        total = info.get("MemTotal", 0)
        available = info.get("MemAvailable", info.get("MemFree", 0))
        if total:
            mem = (total - available) / total * 100.0
    except Exception:
        pass
    return cpu, mem


def build_group_grid(widgets: list[TileWidget], columns: int = 6) -> Gtk.Grid:
    """Pack tiles into a grid using a first-fit placement strategy."""
    grid = Gtk.Grid()
    grid.set_column_homogeneous(False)
    grid.set_row_homogeneous(False)
    grid.set_row_spacing(0)
    grid.set_column_spacing(0)
    occupied: dict[tuple[int, int], bool] = {}

    def fits(col: int, row: int, w: int, h: int) -> bool:
        if col + w > columns:
            return False
        for c in range(col, col + w):
            for r in range(row, row + h):
                if occupied.get((c, r)):
                    return False
        return True

    def mark(col: int, row: int, w: int, h: int) -> None:
        for c in range(col, col + w):
            for r in range(row, row + h):
                occupied[(c, r)] = True

    for widget in widgets:
        w, h = TILE_SIZES.get(widget.tile.get("size", "medium"), (2, 2))
        placed = False
        row = 0
        while not placed:
            for col in range(columns - w + 1):
                if fits(col, row, w, h):
                    grid.attach(widget, col, row, w, h)
                    mark(col, row, w, h)
                    placed = True
                    break
            if not placed:
                row += 1
                if row > 200:  # safety valve
                    grid.attach(widget, 0, row, w, h)
                    mark(0, row, w, h)
                    placed = True
    return grid
