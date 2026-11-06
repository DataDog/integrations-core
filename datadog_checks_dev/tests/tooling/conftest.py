# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.dev.tooling.constants import get_root, set_root


@pytest.fixture
def restore_root():
    """Restore the global tooling root after a test that points it at a temp repo."""
    original_root = get_root()
    yield
    set_root(original_root)
