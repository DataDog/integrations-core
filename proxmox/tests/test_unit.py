# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any, Callable, Dict  # noqa: F401

import pytest

from datadog_checks.base import AgentCheck  # noqa: F401
from datadog_checks.base.stubs.aggregator import AggregatorStub  # noqa: F401
from datadog_checks.dev.http import MockResponse
from datadog_checks.proxmox import ProxmoxCheck


@pytest.mark.usefixtures('mock_http_get')
def test_api_up(dd_run_check, datadog_agent, aggregator, instance):
    check = ProxmoxCheck('proxmox', {}, [instance])
    dd_run_check(check)
    aggregator.assert_metric("proxmox.api.up", 1, tags=['proxmox_server:http://localhost:8006/api2/json', 'testing'])


@pytest.mark.parametrize(
    ('mock_http_get'),
    [
        pytest.param(
            {'http_error': {'/api2/json/version': MockResponse(status_code=500)}},
            id='500',
        ),
        pytest.param(
            {'http_error': {'/api2/json/version': MockResponse(status_code=404)}},
            id='404',
        ),
    ],
    indirect=['mock_http_get'],
)
@pytest.mark.usefixtures('mock_http_get')
def test_api_down(dd_run_check, datadog_agent, aggregator, instance):
    check = ProxmoxCheck('proxmox', {}, [instance])
    dd_run_check(check)
    aggregator.assert_metric("proxmox.api.up", 0, tags=['proxmox_server:http://localhost:8006/api2/json', 'testing'])


@pytest.mark.usefixtures('mock_http_get')
def test_version_metadata(dd_run_check, datadog_agent, aggregator, instance):
    check = ProxmoxCheck('proxmox', {}, [instance])
    check.check_id = 'test:123'
    dd_run_check(check)

    version_metadata = {
        'version.scheme': 'semver',
        'version.major': '8',
        'version.minor': '4',
        'version.patch': '1',
        'version.raw': '8.4.1',
    }
    datadog_agent.assert_metadata('test:123', version_metadata)
