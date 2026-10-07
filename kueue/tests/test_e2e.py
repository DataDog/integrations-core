# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os
import tempfile
import time
from collections.abc import Iterable, Iterator
from contextlib import ExitStack
from typing import NamedTuple

import pytest
import yaml
from tenacity import retry, stop_after_attempt, wait_fixed

from datadog_checks.kueue import KueueCheck

from .common import (
    CHECK_NAME,
    CLUSTER_QUEUE_TAGS,
    EXPECTED_METRIC_TAGS,
    INACTIVE_CLUSTER_QUEUE_TAGS,
    INSTANCE_STATE_KEY,
    LOCAL_QUEUE_TAGS,
    live_metadata_metrics,
)
from .kube import (
    KUEUE_NAMESPACE,
    KUEUE_REPLICAS,
    delete_jobs,
    kubectl,
    kueue_leader_pod,
    port_forward_pod,
    ready_kueue_pods,
    retry_apply,
    scale_kueue_controller,
    trigger_preemption,
    wait_for_controller,
    wait_for_job_workload_condition,
)

EVENT_JOBS = ['event-workload', 'event-pending-workload', 'event-finish-workload']
EVENT_POLL_ATTEMPTS = 15
FAILOVER_POLL_ATTEMPTS = 60


class KueueReplicas(NamedTuple):
    leader: str
    instances: dict[str, dict]

    @property
    def followers(self) -> list[str]:
        return [pod for pod in self.instances if pod != self.leader]


@pytest.mark.e2e
def test_e2e(dd_agent_check, kueue_replicas):
    aggregator = dd_agent_check({'init_config': {}, 'instances': list(kueue_replicas.instances.values())}, rate=True)

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

    leader_tag = endpoint_tag(kueue_replicas.instances[kueue_replicas.leader])
    aggregator.assert_metric(
        'kueue.cluster_queue.status', value=1, tags=[leader_tag, *CLUSTER_QUEUE_TAGS, 'status:active']
    )
    aggregator.assert_metric('kueue.local_queue.status', value=1, tags=[leader_tag, *LOCAL_QUEUE_TAGS, 'active:True'])
    aggregator.assert_metric('kueue.cluster_queue.status', value=1, tags=[leader_tag, *INACTIVE_CLUSTER_QUEUE_TAGS])

    for follower in kueue_replicas.followers:
        follower_tag = endpoint_tag(kueue_replicas.instances[follower])
        aggregator.assert_metric_has_tag('kueue.go.goroutines', follower_tag)
        follower_role_tags = {
            tag
            for name in aggregator.metric_names
            for metric in aggregator.metrics(name)
            if follower_tag in metric.tags
            for tag in metric.tags
            if tag.startswith('replica_role:')
        }
        assert not follower_role_tags, f'{follower} submitted replica_role-labeled samples: {follower_role_tags}'


@pytest.mark.e2e
def test_e2e_workload_events(dd_agent_check, aggregator, kubectl_env, kueue_replicas):
    checks = create_checks(kueue_replicas)
    run_checks(checks.values())
    assert_scraped_roles(checks, kueue_replicas)

    retry_apply('event-pending-workload.yaml', env=kubectl_env)
    pending_workload = wait_for_job_workload_condition('event-pending-workload', 'QuotaReserved=False', env=kubectl_env)
    assert_workload_event(checks.values(), aggregator, 'pending', pending_workload)

    retry_apply('event-workload.yaml', env=kubectl_env)
    admitted_workload = wait_for_job_workload_condition('event-workload', 'Admitted=True', env=kubectl_env)
    for transition in ('created', 'quota_reserved', 'admitted'):
        assert_workload_event(checks.values(), aggregator, transition, admitted_workload)

    retry_apply('event-finish-workload.yaml', env=kubectl_env)
    finished_workload = wait_for_job_workload_condition('event-finish-workload', 'Finished=True', env=kubectl_env)
    assert_workload_event(checks.values(), aggregator, 'finished', finished_workload)


@pytest.mark.e2e
def test_e2e_workload_events_failover(dd_agent_check, aggregator, kubectl_env, kueue_replicas):
    checks = create_checks(kueue_replicas)
    run_checks(checks.values())
    assert_scraped_roles(checks, kueue_replicas)

    retry_apply('event-workload.yaml', env=kubectl_env)
    admitted_workload = wait_for_job_workload_condition('event-workload', 'Admitted=True', env=kubectl_env)
    for transition in ('created', 'quota_reserved', 'admitted'):
        assert_workload_event(checks.values(), aggregator, transition, admitted_workload)

    # Scale down with the leader marked as cheapest to delete, so that no replacement pod can win the election
    # and the scraped follower has to take over.
    kubectl(
        [
            'annotate',
            'pod',
            kueue_replicas.leader,
            '-n',
            KUEUE_NAMESPACE,
            'controller.kubernetes.io/pod-deletion-cost=-1000',
            '--overwrite',
        ],
        env=kubectl_env,
    )
    scale_kueue_controller(KUEUE_REPLICAS - 1, env=kubectl_env)
    try:
        checks.pop(kueue_replicas.leader)
        wait_for_scraped_leader(checks.values())

        retry_apply('event-finish-workload.yaml', env=kubectl_env)
        finished_workload = wait_for_job_workload_condition('event-finish-workload', 'Finished=True', env=kubectl_env)
        assert_workload_event(checks.values(), aggregator, 'finished', finished_workload)

        for transition in ('created', 'quota_reserved', 'admitted'):
            aggregator.assert_event(workload_event_text(admitted_workload, transition), count=1, exact_match=False)
    finally:
        scale_kueue_controller(KUEUE_REPLICAS, env=kubectl_env)
        wait_for_controller(env=kubectl_env)
        trigger_preemption(env=kubectl_env)


def run_check(check):
    """Run the check the way the Agent does so its initializations are applied."""
    error = check.run()
    assert not error, error


def run_checks(checks: Iterable[KueueCheck]) -> None:
    for check in checks:
        run_check(check)


def create_checks(kueue_replicas: KueueReplicas) -> dict[str, KueueCheck]:
    return {pod: KueueCheck(CHECK_NAME, {}, [instance]) for pod, instance in kueue_replicas.instances.items()}


def scraped_roles(check: KueueCheck) -> set[str]:
    return check.scrapers[check.instance['openmetrics_endpoint']].replica_roles


def assert_scraped_roles(checks: dict[str, KueueCheck], kueue_replicas: KueueReplicas) -> None:
    """Assert the leader reports leader series, and followers only report follower ones.

    A leader promoted by an earlier failover in a reused env also keeps stale follower series.
    """
    assert 'leader' in scraped_roles(checks[kueue_replicas.leader])
    for follower in kueue_replicas.followers:
        assert scraped_roles(checks[follower]) == {'follower'}


def wait_for_scraped_leader(checks: Iterable[KueueCheck]) -> None:
    """Run the checks until one of them scrapes a replica that reports itself as the leader."""
    checks = list(checks)
    for _ in range(FAILOVER_POLL_ATTEMPTS):
        run_checks(checks)
        if any('leader' in scraped_roles(check) for check in checks):
            return
        time.sleep(1)
    raise AssertionError(f'No Kueue replica reported replica_role:leader after {FAILOVER_POLL_ATTEMPTS} attempts')


def live_instance(dd_get_state):
    """Return the instance config that `dd_environment` published for this env."""
    instance = dd_get_state(INSTANCE_STATE_KEY)
    assert instance, f'{INSTANCE_STATE_KEY} was not saved by dd_environment'
    return instance


def endpoint_tag(instance: dict) -> str:
    return f'endpoint:{instance["openmetrics_endpoint"]}'


def workload_event_text(workload_name: str, transition: str) -> str:
    return f'Workload default/{workload_name} {transition.replace("_", " ")}.'


def assert_workload_event(checks: Iterable[KueueCheck], aggregator, transition: str, workload_name: str) -> None:
    """Poll the checks until exactly one event for a workload transition shows up across all replicas."""
    checks = list(checks)
    alert_type = 'warning' if transition == 'pending' else 'info'
    for attempt in range(EVENT_POLL_ATTEMPTS):
        run_checks(checks)
        try:
            aggregator.assert_event(
                workload_event_text(workload_name, transition),
                count=1,
                exact_match=False,
                event_type=f'kueue.workload.{transition}',
                source_type_name='kueue',
                alert_type=alert_type,
            )
            return
        except AssertionError:
            if attempt == EVENT_POLL_ATTEMPTS - 1:
                raise
            time.sleep(1)


@retry(stop=stop_after_attempt(30), wait=wait_fixed(2), reraise=True)
def wait_for_replicas(env: dict[str, str]) -> tuple[list[str], str]:
    """Wait until every Kueue replica is Ready and one of them holds the leader Lease."""
    pods = ready_kueue_pods(env=env)
    leader = kueue_leader_pod(env=env)
    assert len(pods) == KUEUE_REPLICAS, f'Expected {KUEUE_REPLICAS} ready Kueue pods, got {pods}'
    assert leader in pods, f'Leader {leader!r} is not one of the ready Kueue pods {pods}'
    return pods, leader


@pytest.fixture
def kubeconfig_env(dd_get_state) -> Iterator[dict[str, str]]:
    """Yield an env pointing kubectl at the kind cluster."""
    with tempfile.NamedTemporaryFile('w', suffix='.yaml') as kubeconfig:
        yaml.safe_dump(live_instance(dd_get_state)['kube_config_dict'], kubeconfig)
        kubeconfig.flush()
        yield {**os.environ, 'KUBECONFIG': kubeconfig.name}


@pytest.fixture
def kubectl_env(kubeconfig_env) -> Iterator[dict[str, str]]:
    """Yield the kubectl env, cleaning up the event Jobs on both sides."""
    delete_jobs(EVENT_JOBS, env=kubeconfig_env)
    try:
        yield kubeconfig_env
    finally:
        delete_jobs(EVENT_JOBS, env=kubeconfig_env)


@pytest.fixture
def kueue_replicas(dd_get_state, kubeconfig_env) -> Iterator[KueueReplicas]:
    """Yield one instance per Kueue replica, each scraping its pod through a dedicated port-forward.

    The forwards are opened per test because a `kubectl port-forward` is bound to one pod, and the failover
    test deletes the leader pod.
    """
    wait_for_controller(env=kubeconfig_env)
    pods, leader = wait_for_replicas(kubeconfig_env)
    base_instance = live_instance(dd_get_state)
    with ExitStack() as stack:
        instances = {}
        for pod in pods:
            host, port = stack.enter_context(port_forward_pod(pod, kubeconfig_env))
            instances[pod] = {**base_instance, 'openmetrics_endpoint': f'https://{host}:{port}/metrics'}
        yield KueueReplicas(leader, instances)
