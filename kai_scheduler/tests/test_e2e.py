# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import time

import pytest
import yaml

from datadog_checks.base.constants import ServiceCheck
from datadog_checks.kai_scheduler import KaiSchedulerCheck

from .common import CHECK_NAME, INSTANCE_STATE_KEY, KUBECONFIG_STATE_KEY, live_metadata_metrics
from .kube import (
    WORKLOAD_NAMESPACE,
    delete_event_job,
    delete_preemption_pods,
    podgroup_owned_by,
    retry_apply,
    run_event_job,
    trigger_preemption,
    wait_for_pod,
)

pytestmark = [pytest.mark.e2e]

EVENT_POLL_ATTEMPTS = 30


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

    # The Agent's check output does not include distributions, so only the unit tests check them.
    metadata_metrics, config_gated, _ = live_metadata_metrics()
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


def test_e2e_podgroup_events(dd_agent_check, dd_run_check, aggregator, dd_get_state, live_instance, kubeconfig):
    # `dd_agent_check` is requested first only so that this test is skipped outside of E2E runs.
    instance = {
        'scheduler_endpoint': live_instance['scheduler_endpoint'],
        'kube_config_dict': yaml.safe_load(dd_get_state(KUBECONFIG_STATE_KEY)),
    }
    check = KaiSchedulerCheck(CHECK_NAME, {}, [instance])
    # The preemption pods would leave no room in `team-a` for the Job.
    delete_preemption_pods()
    delete_event_job()
    dd_run_check(check)

    try:
        run_event_job()
        podgroup = podgroup_owned_by('event-job')
        for transition in ('created', 'admitted'):
            assert_podgroup_event(dd_run_check, check, aggregator, podgroup, transition)

        retry_apply('preempt-high-pod.yaml')
        wait_for_pod('preempt-high-pod', 'condition=Ready')
        evicted = assert_podgroup_event(dd_run_check, check, aggregator, podgroup, 'evicted')
        assert 'kai_eviction_action:preempt' in evicted['tags']
        assert f'kai_evicted_by:{WORKLOAD_NAMESPACE}/{podgroup_owned_by("preempt-high-pod")}' in evicted['tags']
        # The Job creates a replacement pod, which cannot fit in `team-a` next to the preemptor.
        assert_podgroup_event(dd_run_check, check, aggregator, podgroup, 'pending')
    finally:
        delete_event_job()


def assert_podgroup_event(dd_run_check, check, aggregator, podgroup: str, transition: str) -> dict:
    """Run the check until exactly one event of a PodGroup transition is submitted, and return it."""
    for attempt in range(EVENT_POLL_ATTEMPTS):
        events = [
            event
            for event in aggregator.events
            if event['event_type'] == f'kai.podgroup.{transition}' and f'kai_workload:{podgroup}' in event['tags']
        ]
        if events:
            assert len(events) == 1, events
            event = events[0]
            assert event['msg_title'] == f'KAI PodGroup {WORKLOAD_NAMESPACE}/{podgroup} {transition}'
            assert 'kai_queue:team-a' in event['tags']
            assert 'kai_nodepool:default' in event['tags']
            return event
        if attempt < EVENT_POLL_ATTEMPTS - 1:
            time.sleep(1)
            dd_run_check(check)
    raise AssertionError(f'No {transition} event was submitted for PodGroup {podgroup}: {aggregator.events}')
