# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.aerospike import AerospikeCheck
from datadog_checks.base import AgentCheck
from datadog_checks.dev.utils import get_metadata_metrics

from .common import EXPECTED_PROMETHEUS_METRICS


@pytest.mark.e2e
def test_openmetrics_e2e(dd_agent_check, instance_openmetrics_v2):
    aggregator = dd_agent_check(instance_openmetrics_v2, rate=True)
    tags = "endpoint:" + instance_openmetrics_v2.get('openmetrics_endpoint')
    tags = instance_openmetrics_v2.get('tags').append(tags)
    aggregator.assert_service_check('aerospike.openmetrics.health', AgentCheck.OK, tags=tags)

    for metric in EXPECTED_PROMETHEUS_METRICS:
        aggregator.assert_metric(metric, tags=tags)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), check_submission_type=True)


@pytest.mark.integration
def test_metrics_warning(dd_run_check, instance_openmetrics_v2):
    instance_openmetrics_v2['metrics'] = ['migrate_rx_objs', 'migrate_tx_objs']
    check = AerospikeCheck('aerospike', {}, [instance_openmetrics_v2])

    with pytest.raises(Exception, match="Do not use 'metrics' parameter with 'openmetrics_endpoint'"):
        dd_run_check(check)
