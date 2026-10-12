"""Tiny opt-in startup profiler.

Set ``W10SM_TIMING=1`` in the environment to print phase timings to stderr.
"""

from __future__ import annotations

import os
import sys
import time

_T0 = time.perf_counter()
ENABLED = bool(os.environ.get("W10SM_TIMING"))


def log(message: str) -> None:
    if ENABLED:
        elapsed = (time.perf_counter() - _T0) * 1000.0
        print(f"[win10startmenu] {elapsed:8.1f} ms  {message}", file=sys.stderr, flush=True)


def since() -> float:
    return (time.perf_counter() - _T0) * 1000.0
