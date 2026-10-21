# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import platform

import pytest

from datadog_checks.base.utils.native_memory import load_malloc_trim, malloc_trim

pytestmark = pytest.mark.unit


def test_malloc_trim_is_safe_to_call():
    # Callers invoke this unconditionally after a run, so it has to be a no-op rather than an
    # error on platforms without glibc.
    malloc_trim()


@pytest.mark.skipif(platform.system() != 'Linux', reason='glibc is only expected on Linux')
def test_malloc_trim_is_bound_on_linux():
    # Guards the ctypes binding itself: a wrong symbol name or signature would surface here
    # rather than silently degrading to a no-op on the platforms that need the trim.
    trim = load_malloc_trim()

    assert trim is not None
    assert trim(0) in (0, 1)
