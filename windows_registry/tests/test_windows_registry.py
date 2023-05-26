# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base import ConfigurationError
from datadog_checks.dev.testing import requires_windows
from datadog_checks.windows_registry import WindowsRegistryCheck
from tests.common import INSTANCE


@requires_windows
@pytest.mark.unit
def test_config():
    instance = {}
    c = WindowsRegistryCheck('check', {}, [instance])

    # empty instance
    with pytest.raises(ConfigurationError):
        c.check(instance)

    # Test with valid configuration
    c.check(INSTANCE)

    # Path doesn't exist
    with pytest.raises(FileNotFoundError):
        c.check(
            {
                # Forward slashes
                'keypath': 'HKLM/Foo',
                'metrics': [['bar', 'bar', 'gauge']],
            }
        )

    # Invalid path
    with pytest.raises(ConfigurationError):
        c.check({'keypath': 'foo'})
