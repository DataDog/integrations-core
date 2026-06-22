# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import mock
import pytest

from datadog_checks.base.utils.agent.common import get_agent_embedded_path


@pytest.mark.parametrize(
    'run_path, parts, expected_install',
    [
        pytest.param('/opt/datadog-agent/run', ('sbin', 'gstatus'), '/opt/datadog-agent', id='standard_install'),
        pytest.param(
            '/opt/datadog-packages/datadog-agent/7.79.0/run',
            ('sbin', 'gstatus'),
            '/opt/datadog-packages/datadog-agent/7.79.0',
            id='remote_management_install',
        ),
        pytest.param(
            '/custom/agent/dir', ('ssl', 'certs', 'cacert.pem'), '/custom/agent/dir', id='run_path_without_trailing_run'
        ),
        pytest.param('/opt/datadog-agent/run', (), '/opt/datadog-agent', id='no_parts'),
    ],
)
def test_get_agent_embedded_path_posix(run_path, parts, expected_install):
    with (
        mock.patch('datadog_checks.base.utils.agent.common.os.name', 'posix'),
        mock.patch(
            'datadog_checks.base.utils.agent.common.datadog_agent.get_config',
            return_value=run_path,
        ),
    ):
        assert get_agent_embedded_path(*parts) == os.path.join(expected_install, 'embedded', *parts)


def test_get_agent_embedded_path_missing_run_path_returns_none():
    with (
        mock.patch('datadog_checks.base.utils.agent.common.os.name', 'posix'),
        mock.patch(
            'datadog_checks.base.utils.agent.common.datadog_agent.get_config',
            return_value='',
        ),
    ):
        assert get_agent_embedded_path('sbin', 'gstatus') is None


def test_get_agent_embedded_path_windows_uses_sys_executable():
    """On Windows, derive from sys.executable and use the embedded3 directory."""
    install_dir = r'C:\Program Files\Datadog\Datadog Agent'
    sys_executable = os.path.join(install_dir, 'embedded3', 'python.exe')
    with (
        mock.patch('datadog_checks.base.utils.agent.common.os.name', 'nt'),
        mock.patch('datadog_checks.base.utils.agent.common.sys.executable', sys_executable),
    ):
        assert get_agent_embedded_path('ssl', 'certs', 'cacert.pem') == os.path.join(
            install_dir, 'embedded3', 'ssl', 'certs', 'cacert.pem'
        )
