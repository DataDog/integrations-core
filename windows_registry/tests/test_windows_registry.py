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

    # Forward slashes and shorthand name for the hive
    c.check(
        {
            'keypath': 'HKLM/SYSTEM/CurrentControlSet/Control/SecureBoot/State',
            'metrics': [['UEFISecureBootEnabled', 'uefi_secure_boot_enabled', 'gauge']],
        }
    )

    with pytest.raises(FileNotFoundError):
        c.check(
            {
                'keypath': 'HKEY_LOCAL_MACHINE\\SYSTEM\\CurrentControlSet\\Control\\SecurityProviders\\SCHANNEL\\'
                'Protocols\\SSL 3.0\\Client',
                'metrics': [['enabled', 'enabled', 'gauge']],
            }
        )
