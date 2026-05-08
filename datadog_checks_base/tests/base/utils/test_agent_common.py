# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import mock

from datadog_checks.base.utils.agent.common import get_agent_embedded_path


class TestGetAgentEmbeddedPath:
    def test_standard_install(self):
        with mock.patch(
            'datadog_checks.base.utils.agent.common.datadog_agent.get_config',
            return_value='/opt/datadog-agent/run',
        ):
            assert get_agent_embedded_path('sbin', 'gstatus') == '/opt/datadog-agent/embedded/sbin/gstatus'

    def test_remote_management_install(self):
        with mock.patch(
            'datadog_checks.base.utils.agent.common.datadog_agent.get_config',
            return_value='/opt/datadog-packages/datadog-agent/7.79.0/run',
        ):
            assert (
                get_agent_embedded_path('sbin', 'gstatus')
                == '/opt/datadog-packages/datadog-agent/7.79.0/embedded/sbin/gstatus'
            )

    def test_missing_run_path_returns_none(self):
        with mock.patch(
            'datadog_checks.base.utils.agent.common.datadog_agent.get_config',
            return_value='',
        ):
            assert get_agent_embedded_path('sbin', 'gstatus') is None

    def test_run_path_without_trailing_run(self):
        with mock.patch(
            'datadog_checks.base.utils.agent.common.datadog_agent.get_config',
            return_value='/custom/agent/dir',
        ):
            assert (
                get_agent_embedded_path('ssl', 'certs', 'cacert.pem')
                == '/custom/agent/dir/embedded/ssl/certs/cacert.pem'
            )

    def test_no_parts_returns_embedded_dir(self):
        with mock.patch(
            'datadog_checks.base.utils.agent.common.datadog_agent.get_config',
            return_value='/opt/datadog-agent/run',
        ):
            assert get_agent_embedded_path() == '/opt/datadog-agent/embedded'
