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
    EXPECTED_METRIC_TAGS,
    INACTIVE_CLUSTER_QUEUE_TAGS,
    INSTANCE_STATE_KEY,
    assert_series_with_tags,
    live_metadata_metrics,
)
from .kube import delete_jobs, retry_apply, wait_for_job_workload_condition

# Jobs the event test creates. They are torn down on both sides of the test so a previous run cannot
# leave a Workload behind that is already in the check's baseline snapshot.
EVENT_JOBS = ['event-workload', 'event-finish-workload']
# Each run_check advances the workload-event state by one poll, so a transition gets several polls to
# appear before the test fails: the API server can lag the condition the test already waited on.
EVENT_POLL_ATTEMPTS = 15


@pytest.mark.e2e
def test_e2e(dd_agent_check):
    # rate=True runs the check twice so OpenMetrics monotonic counters flush their `.count` submission;
    # otherwise the metadata assertion never validates counter/histogram metrics against metadata.csv.
    aggregator = dd_agent_check(rate=True)

    # Symmetric inclusion pins metadata.csv against the live cluster in both directions: a row nothing
    # emits fails just as loudly as an emitted metric with no row.
    metadata_metrics, config_gated = live_metadata_metrics()
    aggregator.assert_metrics_using_metadata(
        metadata_metrics,
        check_submission_type=True,
        check_symmetric_inclusion=True,
        exclude=config_gated,
    )

    for metric, tags in EXPECTED_METRIC_TAGS.items():
        aggregator.assert_metric(metric, at_least=1)
        assert_series_with_tags(aggregator, metric, tags)

    # `invalid-queue` references a missing flavor and so never activates, making it the only live
    # coverage of a ClusterQueue that is not in the `active` state.
    assert_series_with_tags(aggregator, 'kueue.cluster_queue.status', INACTIVE_CLUSTER_QUEUE_TAGS, value=1)


@pytest.mark.e2e
# This test builds its own check instead of using `dd_agent_check`, so it does not inherit that
# fixture's skip and needs the environment gate spelled out.
@pytest.mark.skipif(not e2e_active(), reason='Requires the Kueue kind environment to be running')
def test_e2e_workload_events(aggregator, kubectl_env, dd_get_state):
    check = KueueCheck(CHECK_NAME, {}, [live_instance(dd_get_state)])
    # Baseline poll. The check suppresses events for workloads it sees on its first run, so every
    # transition asserted below has to be produced after this call.
    run_check(check)

    retry_apply('event-workload.yaml', env=kubectl_env)
    admitted_workload = wait_for_job_workload_condition('event-workload', 'Admitted=True', env=kubectl_env)
    # A workload first seen after the baseline emits `created` plus every condition that is already
    # true, so all three transitions are reachable from this single admitted workload.
    for transition in ('created', 'quota_reserved', 'admitted'):
        assert_workload_event(check, aggregator, transition, admitted_workload)

    retry_apply('event-finish-workload.yaml', env=kubectl_env)
    finished_workload = wait_for_job_workload_condition('event-finish-workload', 'Finished=True', env=kubectl_env)
    assert_workload_event(check, aggregator, 'finished', finished_workload)

    # `running` (PodsReady) and `evicted` are deliberately not asserted here. PodsReady is only set when
    # `waitForPodsReady` is enabled, which would make the GPU workload — whose pod is unschedulable by
    # design — evict and requeue in a loop. Evicted flips back to False as soon as Kueue requeues the
    # preempted workload, a window far shorter than a collection interval, so asserting it would be
    # flaky; it is covered by the unit tests instead, against real Kueue message text.


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
    # Cluster naming matches datadog_checks_dev/dev/kind.py.
    cluster_name = f'cluster-{CHECK_NAME}-{get_active_env()}'
    return run_command(['kind', 'get', 'kubeconfig', '--name', cluster_name], capture='stdout', check=True).stdout
