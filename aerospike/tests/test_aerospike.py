# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import time

import mock
import pytest

from datadog_checks.aerospike import AerospikeCheck
from datadog_checks.base import AgentCheck
from datadog_checks.dev.testing import requires_py3
from datadog_checks.dev.utils import get_metadata_metrics

from .common import (
    EXPECTED_PROMETHEUS_METRICS,
    EXPECTED_PROMETHEUS_METRICS_5_6,
    LATENCIES_METRICS,
    LAZY_METRICS,
    LEGACY_SET_METRICS,
    NAMESPACE_METRICS,
    SET_METRICS,
    STATS_METRICS,
    TPS_METRICS,
    VERSION,
)


@pytest.mark.usefixtures('dd_environment')
@pytest.mark.integration
def test_check(aggregator, instance, dd_run_check):
    check = AerospikeCheck('aerospike', {}, [instance])
    # sleep to make sure client is available
    time.sleep(30)
    for _ in range(10):
        dd_run_check(check)
        time.sleep(1)
    _test_check(aggregator)


def test_version_metadata(aggregator, instance, datadog_agent, dd_run_check):

    check = AerospikeCheck('aerospike', {}, [instance])
    check.check_id = 'test:123'

    # sleep to make sure client is available
    time.sleep(30)
    for _ in range(10):
        dd_run_check(check)
        time.sleep(1)

    raw_version = check.get_info("build")[0]
    major, minor = raw_version.split('.')[:2]
    version_metadata = {
        'version.scheme': 'semver',
        'version.major': major,
        'version.minor': minor,
        'version.patch': mock.ANY,
        'version.raw': raw_version,
    }

    datadog_agent.assert_metadata('test:123', version_metadata)


@pytest.mark.e2e
def test_e2e(dd_agent_check, instance):
    aggregator = dd_agent_check(instance)

    _test_check(aggregator)

    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


@requires_py3
@pytest.mark.e2e
def test_openmetrics_e2e(dd_agent_check, instance_openmetrics_v2):
    version_parts = [int(p) for p in VERSION.split('.')]

    aggregator = dd_agent_check(instance_openmetrics_v2, rate=True)

    tags = "endpoint:" + instance_openmetrics_v2.get('openmetrics_endpoint')
    tags = instance_openmetrics_v2.get('tags').append(tags)

    aggregator.assert_service_check('aerospike.openmetrics.health', AgentCheck.OK, tags=tags)

    for metric in EXPECTED_PROMETHEUS_METRICS:
        aggregator.assert_metric(metric, tags=tags)

    if version_parts >= [5, 6]:
        for metric in EXPECTED_PROMETHEUS_METRICS_5_6:
            aggregator.assert_metric(metric, tags=tags)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), check_submission_type=True)


@requires_py3
@pytest.mark.integration
def test_metrics_warning(dd_run_check, instance_openmetrics_v2):
    instance_openmetrics_v2['metrics'] = ['migrate_rx_objs', 'migrate_tx_objs']
    check = AerospikeCheck('aerospike', {}, [instance_openmetrics_v2])

    with pytest.raises(Exception, match="Do not use 'metrics' parameter with 'openmetrics_endpoint'"):
        dd_run_check(check)


def _test_check(aggregator):
    version_parts = [int(p) for p in VERSION.split('.')]

    for metric in NAMESPACE_METRICS:
        aggregator.assert_metric("aerospike.namespace.{}".format(metric))

    if version_parts >= [5, 3]:
        for metric in LATENCIES_METRICS:
            aggregator.assert_metric(metric)
        aggregator.assert_metric('aerospike.set.device_data_bytes')

    else:
        for metric in TPS_METRICS:
            aggregator.assert_metric("aerospike.namespace.{}".format(metric))

        for metric in LAZY_METRICS:
            aggregator.assert_metric(metric)

    for metric in STATS_METRICS:
        aggregator.assert_metric("aerospike.{}".format(metric))

    if version_parts >= [5, 6]:
        for metric in SET_METRICS:
            aggregator.assert_metric("aerospike.set.{}".format(metric))
    else:
        for metric in LEGACY_SET_METRICS:
            aggregator.assert_metric("aerospike.set.{}".format(metric))

    aggregator.assert_all_metrics_covered()

    aggregator.assert_service_check('aerospike.can_connect', AerospikeCheck.OK)
    aggregator.assert_service_check('aerospike.cluster_up', AerospikeCheck.OK)
