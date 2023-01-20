# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import mock
import pytest
from click.testing import CliRunner

from datadog_checks.dev.errors import ManifestError
from datadog_checks.dev.fs import read_file_lines
from datadog_checks.dev.tooling.release import (
    get_agent_requirement_line,
    get_folder_name,
    get_package_name,
    update_agent_requirements,
)


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


@pytest.mark.parametrize(
    'check,new_version,expected_result',
    [
        (
            "activemq",
            "2.4.0",
            [
                "datadog-activemq-xml==2.2.0\n",
                "datadog-activemq==2.4.0\n",
                "datadog-zk==1.0.0\n",
            ],
        ),
        (
            "impala",
            "1.0.0",
            [
                "datadog-activemq-xml==2.2.0\n",
                "datadog-activemq==2.3.1\n",
                "datadog-impala==1.0.0\n",
                "datadog-zk==1.0.0\n",
            ],
        ),
    ],
    ids=["existing_integration", "new_integration"],
)
def test_update_agent_requirements(check, new_version, expected_result):
    with CliRunner().isolated_filesystem():
        with open('requirements-agent-release.txt', 'w') as file:
            file.write("datadog-activemq-xml==2.2.0\n")
            file.write("datadog-activemq==2.3.1\n")
            file.write("datadog-zk==1.0.0\n")

        update_agent_requirements('requirements-agent-release.txt', check, "datadog-{}=={}".format(check, new_version))

        assert read_file_lines('requirements-agent-release.txt') == expected_result
