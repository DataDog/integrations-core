# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from pathlib import Path
from typing import Any, Callable
from unittest import mock

import pytest

from datadog_checks.base.stubs.aggregator import AggregatorStub
from datadog_checks.base.stubs.datadog_agent import DatadogAgentStub
from datadog_checks.base.utils.http_exceptions import HTTPClientConnectionError
from datadog_checks.n8n import N8nCheck

from . import common

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    'fixture, extra_instance',
    [
        pytest.param('n8n.txt', {}, id='default-prefix'),
        pytest.param('n8n_custom.txt', {'raw_metric_prefix': 'test_'}, id='custom-prefix'),
    ],
)
def test_check_emits_metrics_as_in_metadata(
    dd_run_check: Callable[[N8nCheck], Any],
    aggregator: AggregatorStub,
    fake_http_response: Callable[..., Any],
    fixture: str,
    extra_instance: dict[str, Any],
):
    # The fixtures are a static capture of n8n@2.19.5; the assertion is version-pinned
    # to major=2 regardless of which hatch matrix leg runs the unit tier.
    instance: dict[str, Any] = {'openmetrics_endpoint': 'http://localhost:5678/metrics', **extra_instance}
    fake_http_response(
        instance['openmetrics_endpoint'],
        Path(common.get_fixture_path(fixture)).read_text(),
        headers={'Content-Type': 'text/plain; version=0.0.4'},
        match_options={'stream': True},
    )
    check = N8nCheck('n8n', {}, [instance])
    with mock.patch.object(N8nCheck, '_check_n8n_readiness', return_value=None):
        dd_run_check(check)

    aggregator.assert_metrics_using_metadata(
        common.get_openmetrics_metadata_metrics(major=2),
        check_submission_type=True,
        check_symmetric_inclusion=True,
    )


@pytest.fixture
def initialized_check(instance: dict[str, Any], fake_http: Any) -> N8nCheck:
    check = N8nCheck('n8n', {}, [instance])
    check.load_configuration_models()
    return check


@pytest.mark.parametrize(
    'status_code, expected_value',
    [
        pytest.param(200, 1, id='ready_200'),
        pytest.param(204, 1, id='ready_204'),
        pytest.param(299, 1, id='ready_299_edge'),
        pytest.param(300, 0, id='not_ready_3xx'),
        pytest.param(503, 0, id='not_ready_503'),
    ],
)
def test_readiness_check(
    aggregator: AggregatorStub,
    initialized_check: N8nCheck,
    fake_http_response: Callable[..., Any],
    status_code: int,
    expected_value: int,
):
    fake_http_response(initialized_check._readiness_endpoint, status_code=status_code)
    initialized_check._check_n8n_readiness()

    aggregator.assert_metric(
        'n8n.readiness.check',
        value=expected_value,
        tags=['n8n_process:main', f'status_code:{status_code}'],
    )


def test_readiness_check_unreachable(aggregator: AggregatorStub, initialized_check: N8nCheck, fake_http: Any):
    fake_http.register_response(
        'GET',
        initialized_check._readiness_endpoint,
        HTTPClientConnectionError('boom'),
    )
    initialized_check._check_n8n_readiness()

    aggregator.assert_metric('n8n.readiness.check', value=0, tags=['n8n_process:main', 'status_code:none'])


def test_readiness_uses_endpoint_host_not_metrics_path(initialized_check: N8nCheck):
    """The readiness endpoint must be derived from the host, not appended to /metrics."""
    expected = f'http://{common.HOST}:{common.MAIN_PORT}/healthz/readiness'
    assert initialized_check._readiness_endpoint == expected


def test_version_metadata(
    datadog_agent: DatadogAgentStub,
    dd_run_check: Callable[[N8nCheck], Any],
    fake_http_response: Callable[..., Any],
    instance: dict[str, Any],
):
    fake_http_response(
        instance['openmetrics_endpoint'],
        Path(common.get_fixture_path('n8n.txt')).read_text(),
        headers={'Content-Type': 'text/plain; version=0.0.4'},
        match_options={'stream': True},
    )
    check = N8nCheck('n8n', {}, [instance])
    check.check_id = 'n8n_test'
    with mock.patch.object(N8nCheck, '_check_n8n_readiness', return_value=None):
        dd_run_check(check)
    version_metadata = {
        'version.scheme': 'semver',
        'version.major': '2',
        'version.minor': '19',
        'version.patch': '5',
        'version.raw': 'v2.19.5',
    }

    datadog_agent.assert_metadata('n8n_test', version_metadata)
