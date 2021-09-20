# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging

import mock
import pytest

from datadog_checks.base import AgentCheck
from datadog_checks.citrix_hypervisor import CitrixHypervisorCheck
from datadog_checks.dev.utils import get_metadata_metrics

from .common import SESSION_MASTER, _assert_standalone_metrics, mocked_xenserver

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    'side_effect, expected_session, tag',
    [
        pytest.param([mocked_xenserver('error')], {}, []),
        pytest.param([mocked_xenserver('master')], SESSION_MASTER, ['server_type:master']),
        pytest.param([mocked_xenserver('slave'), mocked_xenserver('master')], SESSION_MASTER, ['server_type:slave']),
        pytest.param([mocked_xenserver('slave'), mocked_xenserver('error')], {}, ['server_type:slave']),
        pytest.param(mock.Mock(side_effect=Exception('Error')), {}, []),
        pytest.param([mocked_xenserver('slave'), mock.Mock(side_effect=Exception('Error'))], {}, ['server_type:slave']),
    ],
)
def test_open_session(instance, side_effect, expected_session, tag):
    with mock.patch('six.moves.xmlrpc_client.Server', side_effect=side_effect):
        check = CitrixHypervisorCheck('citrix_hypervisor', {}, [instance])
        session = check.open_session()

        assert session == expected_session
        assert tag == check._additional_tags


@pytest.mark.usefixtures('mock_responses')
@pytest.mark.parametrize('server_type', [pytest.param('master'), pytest.param('slave')])
def test_check(aggregator, dd_run_check, instance, server_type):
    with mock.patch('six.moves.xmlrpc_client.Server', return_value=mocked_xenserver(server_type)):
        check = CitrixHypervisorCheck('citrix_hypervisor', {}, [instance])
        dd_run_check(check)

        _assert_standalone_metrics(aggregator, ['foo:bar', 'server_type:{}'.format(server_type)])

        aggregator.assert_all_metrics_covered()
        aggregator.assert_metrics_using_metadata(get_metadata_metrics())


@pytest.mark.usefixtures('mock_responses')
@pytest.mark.parametrize(
    'url, expected_status',
    [
        pytest.param('mocked', AgentCheck.OK),
        pytest.param('wrong', AgentCheck.CRITICAL),
    ],
)
def test_service_check(aggregator, dd_run_check, url, expected_status):
    instance = {'url': url}
    check = CitrixHypervisorCheck('citrix_hypervisor', {}, [instance])
    dd_run_check(check)

    aggregator.assert_service_check('citrix_hypervisor.can_connect', expected_status, tags=[])


@pytest.mark.usefixtures('mock_responses')
def test_initialization(caplog):
    caplog.clear()
    caplog.set_level(logging.WARNING)

    # Connection succeded
    check = CitrixHypervisorCheck('citrix_hypervisor', {}, [{'url': 'mocked'}])
    check._check_connection()
    assert check._last_timestamp == 1627907477

    # Connection failure
    check = CitrixHypervisorCheck('citrix_hypervisor', {}, [{'url': 'wrong'}])
    check._check_connection()
    assert check._last_timestamp == 0
    assert "Couldn't initialize the timestamp due to HTTP error" in caplog.text
