# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

pytestmark = [pytest.mark.e2e]

healthz_tags = [
    "endpoint:https://192.168.1.10:63159/healthz",
    "pod_name:virt-handler-98cf864cc-zkgcd",
    "kube_namespace:kubevirt",
    "kube_cluster_name:test-cluster-e2e",
]


def test_e2e_connect_ok(dd_agent_check):
    aggregator = dd_agent_check()
    aggregator.assert_metric("kubevirt_handler.can_connect", value=1, tags=healthz_tags)


def test_e2e_check_collects_kubevirt_handler_metrics(dd_agent_check):
    aggregator = dd_agent_check()
    aggregator.assert_metric("kubevirt_handler.can_connect", value=1, tags=healthz_tags)
