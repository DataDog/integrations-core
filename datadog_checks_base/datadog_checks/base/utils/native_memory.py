# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import ctypes
import ctypes.util
import platform
from collections.abc import Callable


def load_malloc_trim() -> Callable[[int], int] | None:
    """Return glibc's `malloc_trim` on Linux, or `None` where it is unavailable (macOS, musl)."""
    if platform.system() != 'Linux':
        return None
    try:
        libc = ctypes.CDLL(ctypes.util.find_library('c') or 'libc.so.6', use_errno=True)
        trim = libc.malloc_trim
    except (OSError, AttributeError):
        return None
    trim.argtypes = [ctypes.c_size_t]
    trim.restype = ctypes.c_int
    return trim


MALLOC_TRIM = load_malloc_trim()


def malloc_trim() -> None:
    """Return glibc per-arena free memory to the OS after a run; no-op where unavailable."""
    if MALLOC_TRIM is not None:
        MALLOC_TRIM(0)
