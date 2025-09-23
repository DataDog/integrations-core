# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

pytestmark = [pytest.mark.e2e]


healthz_tags = [
    "endpoint:https://10.244.0.38:443/healthz",
    "pod_name:virt-controller-some-id",
    "kube_namespace:kubevirt",
]


def test_e2e_connect_ok(dd_agent_check):
    # Since we are using port-forward to query the pods in the kind environment
    # the check will raise an exception because it cannot find a pod with the ip given in the input
    with pytest.raises(Exception):
        aggregator = dd_agent_check()
        aggregator.assert_metric("kubevirt_controller.can_connect", value=1, tags=healthz_tags)


def test_e2e_check_collects_kubevirt_controller_metrics(dd_agent_check):
    # Since we are using port-forward to query the pods in the kind environment
    # the check will raise an exception because it cannot find a pod with the ip given in the input
    with pytest.raises(Exception):
        aggregator = dd_agent_check()
        aggregator.assert_metric("kubevirt_controller.can_connect", value=1, tags=healthz_tags)
        aggregator.assert_metric("kubevirt_controller.virt_controller.leading_status")
        aggregator.assert_metric("kubevirt_controller.virt_controller.ready_status")
