"""Icon loading helpers built on top of ``Gtk.IconTheme`` with a small cache."""

from __future__ import annotations

import os

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("GdkPixbuf", "2.0")
from gi.repository import GdkPixbuf, Gtk  # noqa: E402

FALLBACK_ICONS = [
    "application-x-executable",
    "application-default-icon",
    "exec",
    "system-run",
]

_cache: dict[tuple[str, int], GdkPixbuf.Pixbuf | None] = {}


def load_icon(icon: str, size: int) -> GdkPixbuf.Pixbuf | None:
    """Load ``icon`` as a square pixbuf of at most ``size`` pixels."""
    key = (icon or "", size)
    if key in _cache:
        return _cache[key]
    pixbuf = _load_uncached(icon, size)
    _cache[key] = pixbuf
    return pixbuf


def _load_uncached(icon: str, size: int) -> GdkPixbuf.Pixbuf | None:
    if icon:
        # Absolute or explicit path (possibly with size suffix like foo.png).
        candidate = icon.split(" ", 1)[0]
        if os.path.isabs(candidate) and os.path.exists(candidate):
            try:
                return GdkPixbuf.Pixbuf.new_from_file_at_scale(candidate, size, size, True)
            except Exception:
                pass

    theme = Gtk.IconTheme.get_default()
    names = [icon] if icon else []
    names.extend(FALLBACK_ICONS)
    for name in names:
        if not name:
            continue
        try:
            info = theme.lookup_icon(name, size, Gtk.IconLookupFlags.FORCE_SIZE)
        except Exception:
            info = None
        if info is not None:
            try:
                return info.load_icon()
            except Exception:
                continue
        # Names with extension are not always resolvable through the theme.
        if name.endswith((".png", ".svg", ".xpm")):
            stem = os.path.splitext(name)[0]
            try:
                info = theme.lookup_icon(stem, size, Gtk.IconLookupFlags.FORCE_SIZE)
            except Exception:
                info = None
            if info is not None:
                try:
                    return info.load_icon()
                except Exception:
                    continue
    return None


def clear_cache() -> None:
    _cache.clear()
