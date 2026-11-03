# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import platform

import mock
import pytest

from datadog_checks.base.utils.native_memory import load_malloc_trim, malloc_trim

pytestmark = pytest.mark.unit


class LibcWithoutMallocTrim:
    """Stands in for a libc that loads but exposes no `malloc_trim`, as musl and bionic do."""

    def __getattr__(self, name):
        raise AttributeError(name)


def test_malloc_trim_is_safe_to_call():
    # Callers invoke this unconditionally after a run, so it has to be a no-op rather than an
    # error on platforms without glibc.
    malloc_trim()


@pytest.mark.skipif(
    platform.system() != 'Linux' or platform.libc_ver()[0] != 'glibc',
    reason='malloc_trim is only expected to bind on glibc',
)
def test_malloc_trim_is_bound_on_glibc():
    # Guards the ctypes binding itself: a wrong symbol name or signature would surface here
    # rather than silently degrading to a no-op on the platforms that need the trim.
    trim = load_malloc_trim()

    assert trim is not None
    assert trim(0) in (0, 1)


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
