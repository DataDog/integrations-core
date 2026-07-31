# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os
import tempfile
import time
from collections.abc import Iterator

import pytest

from datadog_checks.dev._env import e2e_active
from datadog_checks.dev.subprocess import run_command
from datadog_checks.dev.utils import get_active_env
from datadog_checks.kueue import KueueCheck

from .common import (
    CHECK_NAME,
    CLUSTER_QUEUE_TAGS,
    EXPECTED_METRIC_TAGS,
    INACTIVE_CLUSTER_QUEUE_TAGS,
    INSTANCE_STATE_KEY,
    LOCAL_QUEUE_TAGS,
    assert_series_with_tags,
    live_metadata_metrics,
)
from .kube import delete_jobs, retry_apply, wait_for_job_workload_condition

EVENT_JOBS = ['event-workload', 'event-finish-workload']
EVENT_POLL_ATTEMPTS = 15


@pytest.mark.e2e
def test_e2e(dd_agent_check):
    aggregator = dd_agent_check(rate=True)

    metadata_metrics, config_gated = live_metadata_metrics()
    aggregator.assert_metrics_using_metadata(
        metadata_metrics,
        check_submission_type=True,
        check_symmetric_inclusion=True,
        exclude=config_gated,
    )

    for metric, tags in EXPECTED_METRIC_TAGS.items():
        aggregator.assert_metric(metric, at_least=1)
        aggregator.assert_metric_has_tags(metric, tags)

    assert_series_with_tags(aggregator, 'kueue.cluster_queue.status', [*CLUSTER_QUEUE_TAGS, 'status:active'], value=1)
    assert_series_with_tags(aggregator, 'kueue.local_queue.status', [*LOCAL_QUEUE_TAGS, 'active:True'], value=1)
    assert_series_with_tags(aggregator, 'kueue.cluster_queue.status', INACTIVE_CLUSTER_QUEUE_TAGS, value=1)


@pytest.mark.e2e
@pytest.mark.skipif(not e2e_active(), reason='Requires the Kueue kind environment to be running')
def test_e2e_workload_events(aggregator, kubectl_env, dd_get_state):
    check = KueueCheck(CHECK_NAME, {}, [live_instance(dd_get_state)])
    run_check(check)

    retry_apply('event-workload.yaml', env=kubectl_env)
    admitted_workload = wait_for_job_workload_condition('event-workload', 'Admitted=True', env=kubectl_env)
    for transition in ('created', 'quota_reserved', 'admitted'):
        assert_workload_event(check, aggregator, transition, admitted_workload)

    retry_apply('event-finish-workload.yaml', env=kubectl_env)
    finished_workload = wait_for_job_workload_condition('event-finish-workload', 'Finished=True', env=kubectl_env)
    assert_workload_event(check, aggregator, 'finished', finished_workload)


def run_check(check):
    """Run the check the way the Agent does so its initializations are applied."""
    error = check.run()
    assert not error, error


def live_instance(dd_get_state):
    """Return the instance config that `dd_environment` published for this env."""
    instance = dd_get_state(INSTANCE_STATE_KEY)
    assert instance, f'{INSTANCE_STATE_KEY} was not saved by dd_environment'
    return instance


def assert_workload_event(check, aggregator, transition, workload_name):
    """Poll the check until the workload event for a transition shows up."""
    for attempt in range(EVENT_POLL_ATTEMPTS):
        run_check(check)
        try:
            aggregator.assert_event(
                f'Workload default/{workload_name} {transition.replace("_", " ")}.',
                exact_match=False,
                event_type=f'kueue.workload.{transition}',
                source_type_name='kueue',
                alert_type='info',
            )
            return
        except AssertionError:
            if attempt == EVENT_POLL_ATTEMPTS - 1:
                raise
            time.sleep(1)


@pytest.fixture
def kubectl_env() -> Iterator[dict[str, str]]:
    """Yield an env pointing kubectl at the kind cluster, cleaning up the event Jobs on both sides."""
    with tempfile.NamedTemporaryFile('w', suffix='.yaml') as kubeconfig:
        kubeconfig.write(kind_kubeconfig())
        kubeconfig.flush()
        env = {**os.environ, 'KUBECONFIG': kubeconfig.name}
        delete_jobs(EVENT_JOBS, env=env)
        try:
            yield env
        finally:
            delete_jobs(EVENT_JOBS, env=env)


def kind_kubeconfig() -> str:
    cluster_name = f'cluster-{CHECK_NAME}-{get_active_env()}'
    return run_command(['kind', 'get', 'kubeconfig', '--name', cluster_name], capture='stdout', check=True).stdout
