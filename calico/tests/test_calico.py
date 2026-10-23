# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from pathlib import Path

import pytest

from datadog_checks.calico import CalicoCheck
from datadog_checks.dev.utils import get_metadata_metrics

from . import common
from .utils import get_fixture_path


@pytest.mark.unit
def test_check(aggregator, dd_run_check, fake_http, fake_http_response):
    fake_http_response(
        common.MOCK_CALICO_INSTANCE['openmetrics_endpoint'], Path(get_fixture_path('calico.txt')).read_bytes()
    )
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

    fake_http.assert_all_responses_consumed()
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
