# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import ctypes
import platform

import mock
import pytest

from datadog_checks.base.utils.native_memory import load_malloc_trim, malloc_trim

pytestmark = pytest.mark.unit


def glibc_is_loaded():
    """Probe the loaded libc for a glibc-only symbol.

    `platform.libc_ver()` greps the executable for a banner and reports `('', '')` whenever that
    fails, which would skip the binding test on a glibc host with a stripped or frozen build.
    """
    if platform.system() != 'Linux':
        return False
    try:
        return hasattr(ctypes.CDLL(None, use_errno=True), 'gnu_get_libc_version')
    except OSError:
        return False


class LibcWithoutMallocTrim:
    """Stands in for a libc that loads but exposes no `malloc_trim`, as musl and bionic do."""

    def __getattr__(self, name):
        raise AttributeError(name)


def test_malloc_trim_is_safe_to_call():
    # Callers invoke this unconditionally after a run, so it has to be a no-op rather than an
    # error on platforms without glibc.
    malloc_trim()


@pytest.mark.skipif(not glibc_is_loaded(), reason='malloc_trim is only expected to bind on glibc')
def test_malloc_trim_is_bound_on_glibc():
    # Guards the ctypes binding itself: a wrong symbol name or signature would surface here
    # rather than silently degrading to a no-op on the platforms that need the trim.
    trim = load_malloc_trim()

    assert trim is not None
    assert trim(0) in (0, 1)
    # Pinned because the binding is public: a caller passing a non-zero pad would have it
    # truncated to a C int without these, and `trim(0)` alone cannot tell the difference.
    assert trim.argtypes == [ctypes.c_size_t]
    assert trim.restype == ctypes.c_int


@pytest.mark.parametrize(
    'cdll',
    [
        pytest.param({'side_effect': OSError('cannot open shared object file')}, id='libc will not load'),
        pytest.param({'return_value': LibcWithoutMallocTrim()}, id='libc lacks the symbol'),
    ],
)
def test_load_malloc_trim_degrades_to_none_on_linux_without_glibc(cdll):
    # Only non-glibc Linux reaches this branch, so no CI platform covers it: macOS returns at the
    # platform gate and glibc gets a real binding. Without this, narrowing the except tuple would
    # go unnoticed until an Alpine collector crashed at import.
    with (
        mock.patch('datadog_checks.base.utils.native_memory.platform.system', return_value='Linux'),
        mock.patch('datadog_checks.base.utils.native_memory.ctypes.CDLL', **cdll),
    ):
        assert load_malloc_trim() is None


@pytest.mark.parametrize(
    ('loaded', 'expected_calls'),
    [
        pytest.param(None, [], id='no binding'),
        pytest.param(mock.Mock(), [mock.call(0)], id='binding available'),
    ],
)
def test_malloc_trim_calls_the_binding_only_when_one_was_loaded(loaded, expected_calls):
    # Patching the module global keeps both branches covered everywhere. Otherwise which one runs
    # depends on the runner: glibc never exercises the no-op, and non-glibc never exercises the call.
    with mock.patch('datadog_checks.base.utils.native_memory.MALLOC_TRIM', loaded):
        malloc_trim()

    assert (loaded.call_args_list if loaded is not None else []) == expected_calls
