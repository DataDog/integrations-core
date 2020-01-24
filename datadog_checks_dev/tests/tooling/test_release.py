# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import mock
import pytest

from datadog_checks.dev.errors import ManifestError
from datadog_checks.dev.tooling.release import get_agent_requirement_line, get_folder_name, get_package_name


def test_get_package_name():
    assert get_package_name('datadog_checks_base') == 'datadog-checks-base'
    assert get_package_name('my_check') == 'datadog-my-check'


def test_get_folder_name():
    assert get_folder_name('datadog-checks-base') == 'datadog_checks_base'
    assert get_folder_name('datadog-my-check') == 'my_check'


def test_get_agent_requirement_line():
    res = get_agent_requirement_line('datadog_checks_base', '1.1.0')
    assert res == 'datadog-checks-base==1.1.0'

    with mock.patch('datadog_checks.dev.tooling.release.load_manifest') as load:
        # wrong manifest
        load.return_value = {}
        with pytest.raises(ManifestError):
            get_agent_requirement_line('foo', '1.2.3')

        # all platforms
        load.return_value = {"supported_os": ["linux", "mac_os", "windows"]}
        res = get_agent_requirement_line('foo', '1.2.3')
        assert res == 'datadog-foo==1.2.3'

        # one platform
        load.return_value = {"supported_os": ["linux"]}
        res = get_agent_requirement_line('foo', '1.2.3')
        assert res == "datadog-foo==1.2.3; sys_platform == 'linux2'"

        # multiple platforms
        load.return_value = {"supported_os": ["linux", "mac_os"]}
        res = get_agent_requirement_line('foo', '1.2.3')
        assert res == "datadog-foo==1.2.3; sys_platform != 'win32'"
