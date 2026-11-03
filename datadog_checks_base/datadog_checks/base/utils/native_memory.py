# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import ctypes
import platform
from collections.abc import Callable


def load_malloc_trim() -> Callable[[int], int] | None:
    """Return the process's `malloc_trim` on Linux, or `None` where it is unavailable (macOS, musl).

    The symbol is resolved from the process-wide namespace, so under an `LD_PRELOAD` allocator that
    interposes `malloc_trim` this binds the interposer's. That is intended: the allocator actually
    serving the process is the one holding the memory to release.
    """
    if platform.system() != 'Linux':
        return None
    try:
        # CDLL(None) reuses the libc already linked into the process. ctypes.util.find_library
        # would instead shell out to ldconfig, or to gcc where ldconfig is absent, on every import.
        libc = ctypes.CDLL(None, use_errno=True)
        trim = libc.malloc_trim
    except (OSError, AttributeError):
        return None
    trim.argtypes = [ctypes.c_size_t]
    trim.restype = ctypes.c_int
    return trim


MALLOC_TRIM = load_malloc_trim()


def malloc_trim() -> None:
    """Return the allocator's per-arena free memory to the OS after a run; no-op where unavailable."""
    if MALLOC_TRIM is not None:
        MALLOC_TRIM(0)
