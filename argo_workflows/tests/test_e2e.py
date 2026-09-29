# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.argo_workflows import ArgoWorkflowsCheck
from datadog_checks.base.constants import ServiceCheck
from datadog_checks.dev.kubernetes import assert_all_discovery_candidates_stable_kubernetes
from datadog_checks.dev.utils import assert_service_checks


def test_e2e_openmetrics_v2(dd_agent_check):
    aggregator = dd_agent_check()

    aggregator.assert_service_check('argo_workflows.openmetrics.health', ServiceCheck.OK, count=1)
    assert_service_checks(aggregator)


def test_e2e_discovery(dd_agent_check_discovery):
    aggregator = dd_agent_check_discovery(check_rate=True)

    aggregator.assert_service_check('argo_workflows.openmetrics.health', ServiceCheck.OK)
    assert_service_checks(aggregator)


def test_e2e_discovery_all_candidates(dd_agent_check, argo_workflows_kubeconfig):
    assert_all_discovery_candidates_stable_kubernetes(
        dd_agent_check,
        ArgoWorkflowsCheck,
        argo_workflows_kubeconfig,
        namespace='argo',
        pod_selector='app=workflow-controller',
    )
