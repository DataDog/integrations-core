# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.dev._env import e2e_testing
from datadog_checks.dev.kube_discovery import (
    assert_all_discovery_candidates_stable_kubernetes,
    get_kube_discovery_state,
    get_pod,
    resolve_pod_name,
    run_discovery_check_kubernetes,
)
from datadog_checks.kubevirt_handler import KubeVirtHandlerCheck

pytestmark = [pytest.mark.e2e]

healthz_tags = [
    "pod_name:virt-handler-98cf864cc-zkgcd",
    "kube_namespace:kubevirt",
]


def get_virt_handler_pod():
    if not e2e_testing():
        pytest.skip("Not running E2E tests")

    state = get_kube_discovery_state()
    pod_name = resolve_pod_name(state["kubeconfig_path"], "kubevirt", "kubevirt.io=virt-handler")
    return get_pod(state["kubeconfig_path"], "kubevirt", pod_name)


def get_virt_handler_container_id(pod):
    for status in pod["status"]["containerStatuses"]:
        if status["name"] == "virt-handler":
            return status["containerID"]

    raise AssertionError("virt-handler container status not found")


def test_e2e_connect_ok(dd_agent_check):
    aggregator = dd_agent_check()
    aggregator.assert_metric("kubevirt_handler.can_connect", value=1)
    aggregator.assert_metric_has_tags("kubevirt_handler.can_connect", tags=healthz_tags)


def test_e2e_check_collects_kubevirt_handler_metrics(dd_agent_check):
    aggregator = dd_agent_check()
    aggregator.assert_metric("kubevirt_handler.can_connect", value=1)
    aggregator.assert_metric_has_tags("kubevirt_handler.can_connect", tags=healthz_tags)
    aggregator.assert_metric_has_tags("kubevirt_handler.info", tags=[])


def test_e2e_discovery(aggregator, datadog_agent):
    pod = get_virt_handler_pod()

    run_discovery_check_kubernetes(aggregator, datadog_agent)

    aggregator.assert_metric("kubevirt_handler.can_connect", value=1)
    aggregator.assert_metric_has_tags(
        "kubevirt_handler.can_connect",
        tags=[
            f"pod_name:{pod['metadata']['name']}",
            "kube_namespace:kubevirt",
        ],
    )
    aggregator.assert_metric_has_tags("kubevirt_handler.info", tags=[])


def test_e2e_discovery_all_candidates(aggregator, datadog_agent, mocker):
    pod = get_virt_handler_pod()
    pod_name = pod["metadata"]["name"]
    container_id = get_virt_handler_container_id(pod)
    mocker.patch(
        "datadog_checks.kubevirt_handler.config_models.discovery_strategies.tagger.tag",
        return_value=[
            f"pod_name:{pod_name}",
            "kube_namespace:kubevirt",
        ],
    )

    assert_all_discovery_candidates_stable_kubernetes(
        KubeVirtHandlerCheck,
        aggregator,
        datadog_agent,
        namespace="kubevirt",
        pod_selector="kubevirt.io=virt-handler",
        service_id=container_id,
    )
