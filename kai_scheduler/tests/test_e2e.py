# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base.constants import ServiceCheck
from datadog_checks.kai_scheduler import KaiSchedulerCheck

from .common import CHECK_NAME, INSTANCE_STATE_KEY, KUBECONFIG_STATE_KEY, live_metadata_metrics
from .kube import delete_preemption_pods, trigger_preemption

pytestmark = [pytest.mark.e2e]


@pytest.fixture
def live_instance(dd_get_state) -> dict:
    instance = dd_get_state(INSTANCE_STATE_KEY)
    assert instance, f'{INSTANCE_STATE_KEY} was not saved by dd_environment'
    return instance


@pytest.fixture
def kubeconfig(dd_get_state, tmp_path, monkeypatch):
    path = tmp_path / 'kubeconfig'
    path.write_text(dd_get_state(KUBECONFIG_STATE_KEY))
    monkeypatch.setenv('KUBECONFIG', str(path))


def test_e2e(dd_agent_check, live_instance):
    aggregator = dd_agent_check(rate=True)

    metadata_metrics, config_gated = live_metadata_metrics()
    aggregator.assert_metrics_using_metadata(
        metadata_metrics, check_submission_type=True, check_symmetric_inclusion=True, exclude=config_gated
    )

    for option, component in (
        ('scheduler_endpoint', 'scheduler'),
        ('queue_controller_endpoint', 'queue_controller'),
        ('binder_endpoint', 'binder'),
    ):
        aggregator.assert_service_check(
            'kai.openmetrics.health',
            ServiceCheck.OK,
            tags=[f'endpoint:{live_instance[option]}', f'kai_component:{component}', 'test:e2e'],
        )


def test_e2e_evicted_pods(dd_agent_check, dd_run_check, aggregator, live_instance, kubeconfig):
    # `dd_agent_check` is requested first only so that this test is skipped outside of E2E runs.
    check = KaiSchedulerCheck(CHECK_NAME, {}, [{'scheduler_endpoint': live_instance['scheduler_endpoint']}])
    delete_preemption_pods()
    dd_run_check(check)

    trigger_preemption()
    aggregator.reset()
    dd_run_check(check)

    aggregator.assert_metric(
        'kai.evicted_pods.count',
        value=1,
        count=1,
        tags=[
            f'endpoint:{live_instance["scheduler_endpoint"]}',
            'action:preempt',
            'kai_component:scheduler',
            'kai_nodepool:default',
            'kube_namespace:default',
        ],
    )
