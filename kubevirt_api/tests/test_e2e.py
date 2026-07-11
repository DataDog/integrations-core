# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.dev.kube_discovery import (
    assert_all_discovery_candidates_stable_kubernetes,
    run_discovery_check_kubernetes,
)
from datadog_checks.kubevirt_api import KubeVirtApiCheck

pytestmark = [pytest.mark.e2e]


healthz_tags = [
    "pod_name:virt-api-98cf864cc-zkgcd",
    "kube_namespace:kubevirt",
]


def test_e2e_connect_ok(dd_agent_check):
    aggregator = dd_agent_check()
    aggregator.assert_metric("kubevirt_api.can_connect", value=1)
    aggregator.assert_metric_has_tags("kubevirt_api.can_connect", tags=healthz_tags)


def test_e2e_check_collects_kubevirt_api_metrics(dd_agent_check):
    aggregator = dd_agent_check()

    aggregator.assert_metric("kubevirt_api.can_connect", value=1)
    aggregator.assert_metric_has_tags("kubevirt_api.can_connect", tags=healthz_tags)

    aggregator.assert_metric("kubevirt_api.process.open_fds")
    aggregator.assert_metric("kubevirt_api.promhttp.metric_handler_requests_in_flight")


def test_e2e_discovery(aggregator, datadog_agent):
    run_discovery_check_kubernetes(aggregator, datadog_agent)

    # discovery has no way to populate `kube_namespace`/`kube_pod_name` (the `Service`/`Port` model
    # discovery works off of carries no Kubernetes metadata), so `pod_name`/`kube_namespace` tags
    # are absent on discovered instances and aren't asserted here, unlike the static-instance tests
    # above.
    aggregator.assert_metric("kubevirt_api.can_connect", value=1)
    aggregator.assert_metric("kubevirt_api.process.open_fds")
    aggregator.assert_metric("kubevirt_api.promhttp.metric_handler_requests_in_flight")


def test_e2e_discovery_all_candidates(aggregator, datadog_agent):
    assert_all_discovery_candidates_stable_kubernetes(
        KubeVirtApiCheck,
        aggregator,
        datadog_agent,
        namespace="kubevirt",
        pod_selector="kubevirt.io=virt-api",
    )
