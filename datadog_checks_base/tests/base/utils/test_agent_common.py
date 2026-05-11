# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import mock
import pytest

from datadog_checks.base.utils.agent.common import get_agent_embedded_path


@pytest.mark.parametrize(
    'run_path, parts, expected',
    [
        pytest.param(
            '/opt/datadog-agent/run',
            ('sbin', 'gstatus'),
            '/opt/datadog-agent/embedded/sbin/gstatus',
            id='standard_install',
        ),
        pytest.param(
            '/opt/datadog-packages/datadog-agent/7.79.0/run',
            ('sbin', 'gstatus'),
            '/opt/datadog-packages/datadog-agent/7.79.0/embedded/sbin/gstatus',
            id='remote_management_install',
        ),
        pytest.param(
            '/custom/agent/dir',
            ('ssl', 'certs', 'cacert.pem'),
            '/custom/agent/dir/embedded/ssl/certs/cacert.pem',
            id='run_path_without_trailing_run',
        ),
        pytest.param('/opt/datadog-agent/run', (), '/opt/datadog-agent/embedded', id='no_parts'),
        pytest.param('', ('sbin', 'gstatus'), None, id='missing_run_path'),
    ],
)
def test_get_agent_embedded_path(run_path, parts, expected):
    with mock.patch(
        'datadog_checks.base.utils.agent.common.datadog_agent.get_config',
        return_value=run_path,
    ):
        assert get_agent_embedded_path(*parts) == expected
