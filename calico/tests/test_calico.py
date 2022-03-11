# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.calico import CalicoCheck
from datadog_checks.dev.utils import get_metadata_metrics

from . import common
from .utils import get_fixture_path


@pytest.mark.unit
def test_check(aggregator, dd_run_check, mock_http_response):

    mock_http_response(file_path=get_fixture_path('calico.txt'))
    check = CalicoCheck('calico', {}, [common.MOCK_CALICO_INSTANCE])
    dd_run_check(check)

    aggregator.assert_metric("calico.felix.active.local_endpoints", metric_type=aggregator.GAUGE)
    aggregator.assert_metric("calico.felix.active.local_policies", metric_type=aggregator.GAUGE)
    aggregator.assert_metric("calico.felix.active.local_selectors", metric_type=aggregator.GAUGE)
    aggregator.assert_metric("calico.felix.active.local_tags", metric_type=aggregator.GAUGE)
    aggregator.assert_metric("calico.felix.cluster.num_host_endpoints", metric_type=aggregator.GAUGE)
    aggregator.assert_metric("calico.felix.cluster.num_hosts", metric_type=aggregator.GAUGE)
    aggregator.assert_metric("calico.felix.cluster.num_workload_endpoints", metric_type=aggregator.GAUGE)
    aggregator.assert_metric("calico.felix.ipset.calls.count", metric_type=aggregator.MONOTONIC_COUNT)
    aggregator.assert_metric("calico.felix.ipset.errors.count", metric_type=aggregator.MONOTONIC_COUNT)
    aggregator.assert_metric("calico.felix.ipsets.calico", metric_type=aggregator.GAUGE)
    aggregator.assert_metric("calico.felix.ipsets.total", metric_type=aggregator.GAUGE)
    aggregator.assert_metric("calico.felix.iptables.chains", metric_type=aggregator.GAUGE)
    aggregator.assert_metric("calico.felix.iptables.rules", metric_type=aggregator.GAUGE)
    aggregator.assert_metric("calico.felix.iptables.restore_calls.count", metric_type=aggregator.MONOTONIC_COUNT)
    aggregator.assert_metric("calico.felix.iptables.restore_errors.count", metric_type=aggregator.MONOTONIC_COUNT)
    aggregator.assert_metric("calico.felix.iptables.save_calls.count", metric_type=aggregator.MONOTONIC_COUNT)
    aggregator.assert_metric("calico.felix.iptables.save_errors.count", metric_type=aggregator.MONOTONIC_COUNT)
    aggregator.assert_metric("calico.felix.int_dataplane_failures.count", metric_type=aggregator.MONOTONIC_COUNT)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
