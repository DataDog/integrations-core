# ABOUTME: Unit tests for the NiFi integration.
# ABOUTME: Currently a smoke test; expanded as check logic is added.

# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.nifi import NifiCheck


def test_check_import():
    """Verify the check class can be imported and instantiated."""
    check = NifiCheck('nifi', {}, [{}])
    assert check.__NAMESPACE__ == 'nifi'
