# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.argo_workflows import ArgoWorkflowsCheck
from datadog_checks.base.constants import ServiceCheck
from datadog_checks.dev.kubernetes import assert_all_discovery_candidates_stable_kubernetes
from datadog_checks.dev.utils import assert_service_checks

from .conftest import ARGO_SERVER_ENDPOINT

GRPC_SERVER_METRICS = (
    'grpc.server.handled.count',
    'grpc.server.handling_seconds.bucket',
    'grpc.server.handling_seconds.count',
    'grpc.server.handling_seconds.sum',
    'grpc.server.msg_received.count',
    'grpc.server.msg_sent.count',
    'grpc.server.started.count',
)


def test_e2e_openmetrics_v2(dd_agent_check):
    # Monotonic counts are only submitted from the second run onward.
    aggregator = dd_agent_check(rate=True)

    # Two runs for each of the two instances: the workflow controller and the Argo Server.
    aggregator.assert_service_check('argo_workflows.openmetrics.health', ServiceCheck.OK, count=4)
    aggregator.assert_service_check(
        'argo_workflows.openmetrics.health', ServiceCheck.OK, tags=[f'endpoint:{ARGO_SERVER_ENDPOINT}'], count=2
    )
    for metric in GRPC_SERVER_METRICS:
        aggregator.assert_metric_has_tag(f'argo_workflows.{metric}', f'endpoint:{ARGO_SERVER_ENDPOINT}')
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
