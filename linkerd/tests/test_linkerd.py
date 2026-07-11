# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import pytest
import requests_mock

from datadog_checks.dev.kube_discovery import (
    assert_all_discovery_candidates_stable_kubernetes,
    run_discovery_check_kubernetes,
)
from datadog_checks.linkerd import LinkerdCheck

from .common import (
    EXPECTED_METRICS_V2,
    EXPECTED_METRICS_V2_E2E,
    EXPECTED_METRICS_V2_NEW,
    HERE,
    LINKERD_FIXTURE_VALUES,
    MOCK_INSTANCE,
    MOCK_INSTANCE_NEW,
    OPTIONAL_METRICS_V2_E2E,
)


def get_fixture_path(filename):
    return os.path.join(HERE, 'fixtures', filename)


def get_response(filename):
    metrics_file_path = get_fixture_path(filename)
    with open(metrics_file_path, 'r') as f:
        response = f.read()
    return response


def test_linkerd(aggregator, dd_run_check):
    """
    Test the full check
    """
    check = LinkerdCheck('linkerd', {}, [MOCK_INSTANCE])
    with requests_mock.Mocker() as metric_request:
        metric_request.get('http://fake.tld/prometheus', text=get_response('linkerd.txt'))
        dd_run_check(check)

    for metric in LINKERD_FIXTURE_VALUES:
        aggregator.assert_metric(metric, LINKERD_FIXTURE_VALUES[metric])

    aggregator.assert_metric('linkerd.prometheus.health', metric_type=aggregator.GAUGE)

    aggregator.assert_all_metrics_covered()

    aggregator.assert_service_check(
        'linkerd.prometheus.health', status=check.OK, tags=['endpoint:http://fake.tld/prometheus'], count=1
    )


def test_linkerd_v2(aggregator, dd_run_check):
    check = LinkerdCheck('linkerd', {}, [MOCK_INSTANCE])
    with requests_mock.Mocker() as metric_request:
        metric_request.get('http://fake.tld/prometheus', text=get_response('linkerd_v2.txt'))
        dd_run_check(check)

    for metric_name, metric_type in EXPECTED_METRICS_V2.items():
        aggregator.assert_metric(metric_name, metric_type=metric_type)

    aggregator.assert_all_metrics_covered()

    aggregator.assert_service_check(
        'linkerd.prometheus.health', status=LinkerdCheck.OK, tags=['endpoint:http://fake.tld/prometheus'], count=1
    )


def test_linkerd_v2_new(aggregator, dd_run_check, mock_http_response):
    mock_http_response(file_path=get_fixture_path('linkerd_v2.txt'))
    check = LinkerdCheck('linkerd', {}, [MOCK_INSTANCE_NEW])
    dd_run_check(check)

    for metric_name, metric_type in EXPECTED_METRICS_V2_NEW.items():
        aggregator.assert_metric(metric_name, metric_type=metric_type)

    aggregator.assert_all_metrics_covered()

    aggregator.assert_service_check(
        'linkerd.openmetrics.health', status=LinkerdCheck.OK, tags=['endpoint:http://fake.tld/prometheus'], count=1
    )


def test_openmetrics_error(monkeypatch, dd_run_check):
    check = LinkerdCheck('linkerd', {}, [MOCK_INSTANCE])
    with requests_mock.Mocker() as metric_request:
        metric_request.get('http://fake.tld/prometheus', exc="Exception")
        with pytest.raises(Exception):
            dd_run_check(check)


@pytest.mark.e2e
def test_e2e(dd_agent_check):
    aggregator = dd_agent_check(rate=True)
    for metric_name, metric_type in EXPECTED_METRICS_V2_E2E.items():
        if metric_name in OPTIONAL_METRICS_V2_E2E:
            aggregator.assert_metric(metric_name, metric_type=metric_type, at_least=0)
        else:
            aggregator.assert_metric(metric_name, metric_type=metric_type)
    aggregator.assert_all_metrics_covered()

    aggregator.assert_service_check('linkerd.prometheus.health', status=LinkerdCheck.OK, count=2)


@pytest.mark.e2e
def test_e2e_discovery_debug_dump2():
    # TEMPORARY debug test #2: inspect the mounted auto_conf.yaml and running processes inside
    # the discovery agent pod itself. Will be removed before merge.
    import subprocess

    from datadog_checks.dev._env import e2e_testing, get_state

    if not e2e_testing():
        pytest.skip('Not running E2E tests')

    state = get_state('kube_discovery')
    env = os.environ.copy()
    env['KUBECONFIG'] = state['kubeconfig_path']

    def agent_exec(*args):
        return subprocess.run(
            ['kubectl', 'exec', '-n', 'dd-agent-discovery', 'dd-agent-discovery', '--', *args],
            env=env,
            capture_output=True,
            text=True,
        )

    mounted_conf = agent_exec('cat', '/etc/datadog-agent/conf.d/linkerd.d/auto_conf.yaml')
    processes = agent_exec('ps', 'aux')
    agent_status = agent_exec('agent', 'status', '--json')

    raise AssertionError(
        'DEBUG mounted auto_conf.yaml:\n'
        + mounted_conf.stdout
        + mounted_conf.stderr
        + '\nDEBUG processes in agent pod:\n'
        + processes.stdout
        + processes.stderr
        + '\nDEBUG agent status --json (first 8000 chars):\n'
        + (agent_status.stdout + agent_status.stderr)[:8000]
    )


@pytest.mark.e2e
def test_e2e_discovery(aggregator, datadog_agent):
    # The `proxy` ad_identifier matches every linkerd-proxy sidecar in the cluster (control-plane
    # components and injected emojivoto pods alike), so the Agent's Autodiscovery has more
    # containers to enumerate and render configs for than a typical single-target integration;
    # give it more room than the default 30s to complete within a busy kind cluster.
    run_discovery_check_kubernetes(aggregator, datadog_agent, check_rate=True, discovery_timeout=90)

    for metric_name, metric_type in EXPECTED_METRICS_V2_E2E.items():
        if metric_name in OPTIONAL_METRICS_V2_E2E:
            aggregator.assert_metric(metric_name, metric_type=metric_type, at_least=0)
        else:
            aggregator.assert_metric(metric_name, metric_type=metric_type)
    aggregator.assert_all_metrics_covered()

    # Unlike the manual E2E test above, the `proxy` ad_identifier matches every linkerd-proxy
    # sidecar in the cluster (control-plane components and injected emojivoto pods alike), so
    # discovery yields more than one instance here; assert at least the two check runs
    # (check_rate=True) that a single instance would produce, rather than an exact count.
    aggregator.assert_service_check('linkerd.prometheus.health', status=LinkerdCheck.OK, at_least=2)


@pytest.mark.e2e
def test_e2e_discovery_all_candidates(aggregator, datadog_agent):
    assert_all_discovery_candidates_stable_kubernetes(
        LinkerdCheck,
        aggregator,
        datadog_agent,
        namespace='linkerd',
        pod_selector='linkerd.io/control-plane-component=controller',
    )
