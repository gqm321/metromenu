"""Icon loading helpers built on top of ``Gtk.IconTheme``.

Two layers of caching are used:

* an in-process dict (``_cache``), and
* a small on-disk cache of pre-rendered PNGs, so a cold start does not have to
  look the icon up in the theme and rasterise it again.
"""

from __future__ import annotations

import hashlib
import os
import shutil
from pathlib import Path

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

_ICON_CACHE_VERSION = 1
_CACHE_HOME = os.environ.get("XDG_CACHE_HOME") or os.path.expanduser("~/.cache")
CACHE_DIR = Path(_CACHE_HOME) / "metromenu" / "icons"

_cache: dict[tuple[str, int], GdkPixbuf.Pixbuf | None] = {}


def load_icon(icon: str, size: int) -> GdkPixbuf.Pixbuf | None:
    """Load ``icon`` as a square pixbuf of at most ``size`` pixels."""
    key = (icon or "", size)
    if key in _cache:
        return _cache[key]

    pixbuf = _load_from_disk(icon, size)
    if pixbuf is None:
        pixbuf = _load_uncached(icon, size)
        if pixbuf is not None:
            _save_to_disk(icon, size, pixbuf)

    _cache[key] = pixbuf
    return pixbuf


def _cache_key(icon: str, size: int) -> str:
    # Include the icon theme so switching themes does not serve stale icons,
    # and the file mtime for icons referenced by absolute path.
    try:
        theme_name = Gtk.IconTheme.get_default().get_name() or ""
    except Exception:
        theme_name = ""
    stamp = ""
    if icon:
        candidate = icon.split(" ", 1)[0]
        if os.path.isabs(candidate) and os.path.exists(candidate):
            try:
                stamp = str(os.stat(candidate).st_mtime_ns)
            except OSError:
                stamp = ""
    raw = f"{_ICON_CACHE_VERSION}|{theme_name}|{icon}|{size}|{stamp}"
    return hashlib.sha1(raw.encode("utf-8", "replace")).hexdigest()


def _disk_path(icon: str, size: int) -> Path:
    return CACHE_DIR / f"{_cache_key(icon, size)}.png"


def _load_from_disk(icon: str, size: int) -> GdkPixbuf.Pixbuf | None:
    try:
        path = _disk_path(icon, size)
    except Exception:
        return None
    if not path.exists():
        return None
    try:
        return GdkPixbuf.Pixbuf.new_from_file(str(path))
    except Exception:
        return None


def _save_to_disk(icon: str, size: int, pixbuf: GdkPixbuf.Pixbuf) -> None:
    try:
        path = _disk_path(icon, size)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.parent / (path.name + ".tmp")
        pixbuf.savev(str(tmp), "png", [], [])
        tmp.replace(path)
    except Exception:
        pass


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


def clear_cache(disk: bool = False) -> None:
    _cache.clear()
    if disk:
        shutil.rmtree(CACHE_DIR, ignore_errors=True)
