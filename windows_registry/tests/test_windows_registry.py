# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base import ConfigurationError
from datadog_checks.dev.testing import requires_windows
from datadog_checks.windows_registry import WindowsRegistryCheck


@requires_windows
@pytest.mark.unit
def test_config():
    instance = {}
    c = WindowsRegistryCheck('check', {}, [instance])

    # empty instance
    with pytest.raises(ConfigurationError):
        c.check(instance)

    # This key is pretty much guaranteed to exists in all environments
    c.check(
        {
            'keypath': 'HKLM\\Software\\Microsoft\\Windows NT\\CurrentVersion',
            'metrics': [
                # This is a REG_SZ
                ['CurrentBuild', 'windows.current_build', 'gauge'],
                # This is a REG_DWORD
                ['InstallDate', 'windows.install_date', 'gauge'],
            ],
        }
    )

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
