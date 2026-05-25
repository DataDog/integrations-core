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
    res = get_agent_requirement_line('datadog_checks_base', '1.1.0', mock.Mock())
    assert res == 'datadog-checks-base==1.1.0'

    with mock.patch('datadog_checks.dev.tooling.release.load_manifest') as load:
        # all platforms
        load.return_value = {"supported_os": ["linux", "mac_os", "windows"]}
        res = get_agent_requirement_line('foo', '1.2.3', mock.Mock())
        assert res == 'datadog-foo==1.2.3'

        # one platform
        load.return_value = {"supported_os": ["linux"]}
        res = get_agent_requirement_line('foo', '1.2.3', mock.Mock())
        assert res == "datadog-foo==1.2.3; sys_platform == 'linux2'"

        # multiple platforms
        load.return_value = {"supported_os": ["linux", "mac_os"]}
        res = get_agent_requirement_line('foo', '1.2.3', mock.Mock())
        assert res == "datadog-foo==1.2.3; sys_platform != 'win32'"


@pytest.mark.parametrize(
    'overrides, expected_line',
    [
        ({"my_check": ["linux"]}, "datadog-my-check==1.1.0; sys_platform == 'linux2'"),
        ({"my_check": ["mac_os", "windows"]}, "datadog-my-check==1.1.0; sys_platform != 'linux2'"),
        ({"my_check": ["linux", "mac_os", "windows"]}, "datadog-my-check==1.1.0"),
    ],
    ids=["one_platform", "all_except_one", "all_platforms"],
)
def test_get_agent_requirement_line_with_overrides(overrides: dict[str, list[str]], expected_line: str):
    with mock.patch('datadog_checks.dev.tooling.release.load_manifest') as load:
        load.return_value = {}
        app = mock.MagicMock(repo=mock.MagicMock(config={'/overrides/manifest/platforms': overrides}))
        res = get_agent_requirement_line('my_check', '1.1.0', app)
        assert res == expected_line


def _tile_manifest(supported_os_values):
    return {
        'tile': {
            'classifier_tags': [f'Supported OS::{v}' for v in supported_os_values],
        }
    }


@pytest.mark.parametrize(
    'classifier_supported_os, expected_line',
    [
        (['Linux', 'macOS', 'Windows', 'AIX'], 'datadog-foo==1.2.3'),
        (['Linux', 'AIX'], "datadog-foo==1.2.3; sys_platform == 'linux2'"),
        (['Linux', 'Windows', 'AIX'], "datadog-foo==1.2.3; sys_platform != 'darwin'"),
        (['Linux', 'macOS', 'AIX'], "datadog-foo==1.2.3; sys_platform != 'win32'"),
        (['macOS', 'Windows', 'AIX'], "datadog-foo==1.2.3; sys_platform != 'linux2'"),
    ],
    ids=['all_plus_aix', 'linux_plus_aix', 'no_macos_plus_aix', 'no_windows_plus_aix', 'no_linux_plus_aix'],
)
def test_get_agent_requirement_line_tile_manifest_with_aix(classifier_supported_os, expected_line):
    with mock.patch('datadog_checks.dev.tooling.release.load_manifest') as load:
        load.return_value = _tile_manifest(classifier_supported_os)
        assert get_agent_requirement_line('foo', '1.2.3', mock.Mock()) == expected_line


@pytest.mark.parametrize(
    'supported_os, expected_line',
    [
        (['aix', 'linux', 'mac_os', 'windows'], 'datadog-foo==1.2.3'),
        (['aix', 'linux'], "datadog-foo==1.2.3; sys_platform == 'linux2'"),
        (['aix', 'linux', 'mac_os'], "datadog-foo==1.2.3; sys_platform != 'win32'"),
    ],
    ids=['all_plus_aix', 'linux_plus_aix', 'no_windows_plus_aix'],
)
def test_get_agent_requirement_line_supported_os_with_aix(supported_os, expected_line):
    with mock.patch('datadog_checks.dev.tooling.release.load_manifest') as load:
        load.return_value = {'supported_os': supported_os}
        assert get_agent_requirement_line('foo', '1.2.3', mock.Mock()) == expected_line


@pytest.mark.parametrize(
    'manifest',
    [
        _tile_manifest(['AIX']),
        {'supported_os': ['aix']},
    ],
    ids=['tile', 'supported_os'],
)
def test_get_agent_requirement_line_returns_none_when_only_ignored_platforms(manifest):
    with mock.patch('datadog_checks.dev.tooling.release.load_manifest') as load:
        load.return_value = manifest
        assert get_agent_requirement_line('foo', '1.2.3', mock.Mock()) is None


@pytest.mark.parametrize(
    'manifest',
    [
        _tile_manifest([]),
        {'supported_os': []},
    ],
    ids=['tile', 'supported_os'],
)
def test_get_agent_requirement_line_raises_when_no_supported_os(manifest):
    with mock.patch('datadog_checks.dev.tooling.release.load_manifest') as load:
        load.return_value = manifest
        with pytest.raises(ManifestError):
            get_agent_requirement_line('foo', '1.2.3', mock.Mock())


def test_get_agent_requirement_line_with_overrides_no_manifest_no_override():
    with mock.patch('datadog_checks.dev.tooling.release.load_manifest') as load:
        load.return_value = {}
        app = mock.MagicMock(repo=mock.MagicMock(config={'/overrides/manifest/platforms': {}}))
        with pytest.raises(ManifestError):
            get_agent_requirement_line('my_check', '1.1.0', app)


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
