# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from ..common import CILIUM_VERSION, requires_legacy_environment

# Legacy common metrics
from .common import ADDL_AGENT_METRICS, AGENT_DEFAULT_METRICS, OPERATOR_AWS_METRICS, OPERATOR_METRICS

pytestmark = [requires_legacy_environment]


def test_agent_check(aggregator, agent_instance_use_openmetrics, mock_agent_data, dd_run_check, check):
    c = check(agent_instance_use_openmetrics(False))

    dd_run_check(c)
    for m in AGENT_DEFAULT_METRICS + ADDL_AGENT_METRICS:
        aggregator.assert_metric(m)
    aggregator.assert_all_metrics_covered()


def test_operator_check(aggregator, operator_instance_use_openmetrics, mock_operator_data, check, dd_run_check):
    c = check(operator_instance_use_openmetrics(False))

    dd_run_check(c)
    for m in OPERATOR_METRICS + OPERATOR_AWS_METRICS:
        aggregator.assert_metric(m)
    aggregator.assert_all_metrics_covered()


def test_version_metadata(datadog_agent, agent_instance_use_openmetrics, mock_agent_data, check, dd_run_check):
    check = check(agent_instance_use_openmetrics(False))
    check.check_id = 'test:123'
    dd_run_check(check)

    major, minor, patch = CILIUM_VERSION.split('.')
    version_metadata = {
        'version.scheme': 'semver',
        'version.major': major,
        'version.minor': minor,
        'version.patch': patch,
        'version.raw': CILIUM_VERSION,
    }

    datadog_agent.assert_metadata('test:123', version_metadata)
