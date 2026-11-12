# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""kubectl helpers shared by the Kueue kind environment setup and the e2e tests."""

import json
import os
import socket
import subprocess
import time
from collections.abc import Iterator
from contextlib import contextmanager

import yaml

from datadog_checks.dev import get_here
from datadog_checks.dev.subprocess import SubprocessResult, run_command
from datadog_checks.dev.utils import find_free_port, get_ip

HERE = get_here()
NAMESPACE = 'default'
KUEUE_NAMESPACE = 'kueue-system'  # hardcoded in the Kueue manifests
KUEUE_REPLICAS = 2
KUEUE_POD_SELECTOR = 'control-plane=controller-manager'
KUEUE_METRICS_PORT = 8443
PORT_FORWARD_ATTEMPTS = 30
PREEMPTION_JOBS = ['preempt-low-workload', 'preempt-high-workload']
# Setup and the e2e tests wait on the same controller, so they get the same budget rather than the two
# different ones they used to use: a reconcile can take tens of seconds on a cold single-node cluster.
WAIT_TIMEOUT = '300s'
WORKLOAD_DISCOVERY_ATTEMPTS = 60
WEBHOOK_RETRY_ATTEMPTS = 10


def manifest_path(name: str) -> str:
    return os.path.join(HERE, 'kind', name)


def kubectl(args: list[str], env: dict[str, str] | None = None, check: bool = True, **kwargs) -> SubprocessResult:
    """Run kubectl, raising on a non-zero exit code by default so a failed wait cannot pass silently."""
    return run_command(['kubectl', *args], env=env, check=check, **kwargs)


def kubectl_output(args: list[str], env: dict[str, str] | None = None, check: bool = True) -> str:
    return kubectl(args, env=env, check=check, capture=True).stdout.strip()


def wait_for_controller(env: dict[str, str] | None = None) -> None:
    kubectl(
        [
            'rollout',
            'status',
            'deployment/kueue-controller-manager',
            '-n',
            KUEUE_NAMESPACE,
            f'--timeout={WAIT_TIMEOUT}',
        ],
        env=env,
    )
    kubectl(
        [
            'wait',
            'deployment/kueue-controller-manager',
            '--for=condition=Available',
            '-n',
            KUEUE_NAMESPACE,
            f'--timeout={WAIT_TIMEOUT}',
        ],
        env=env,
    )


def scale_kueue_controller(replicas: int, env: dict[str, str] | None = None) -> None:
    kubectl(['scale', 'deployment/kueue-controller-manager', '-n', KUEUE_NAMESPACE, f'--replicas={replicas}'], env=env)


def ready_kueue_pods(env: dict[str, str] | None = None) -> list[str]:
    """Return the names of the Kueue controller pods that are Ready and not terminating."""
    pods = json.loads(
        kubectl_output(['get', 'pods', '-n', KUEUE_NAMESPACE, '-l', KUEUE_POD_SELECTOR, '-o', 'json'], env=env)
    )['items']
    return sorted(
        pod['metadata']['name']
        for pod in pods
        if 'deletionTimestamp' not in pod['metadata']
        and any(
            condition['type'] == 'Ready' and condition['status'] == 'True'
            for condition in pod['status'].get('conditions', [])
        )
    )


def kueue_leader_pod(env: dict[str, str] | None = None) -> str:
    """Return the name of the pod holding the Kueue leader election Lease."""
    holder = kubectl_output(
        ['get', 'lease', kueue_lease_name(), '-n', KUEUE_NAMESPACE, '-o', 'jsonpath={.spec.holderIdentity}'], env=env
    )
    return holder.split('_')[0]


def kueue_lease_name() -> str:
    """Return the leader election Lease name that kind/kueue-config.yaml configures."""
    with open(manifest_path('kueue-config.yaml')) as f:
        config_map = yaml.safe_load(f)
    manager_config = yaml.safe_load(config_map['data']['controller_manager_config.yaml'])
    return manager_config['leaderElection']['resourceName']


@contextmanager
def port_forward_pod(pod: str, env: dict[str, str]) -> Iterator[tuple[str, int]]:
    """Forward the Kueue metrics port of a single pod, reachable from the host and the Agent container."""
    ip = get_ip()
    port = find_free_port(ip)
    process = subprocess.Popen(
        [
            'kubectl',
            'port-forward',
            '--address',
            f'localhost,{ip}',
            '-n',
            KUEUE_NAMESPACE,
            f'pod/{pod}',
            f'{port}:{KUEUE_METRICS_PORT}',
        ],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        wait_for_port(ip, port, process)
        yield ip, port
    finally:
        process.terminate()
        process.wait(timeout=10)


def wait_for_port(ip: str, port: int, process: subprocess.Popen) -> None:
    for _ in range(PORT_FORWARD_ATTEMPTS):
        if process.poll() is not None:
            raise RuntimeError(f'kubectl port-forward to {ip}:{port} exited with code {process.returncode}')
        try:
            with socket.create_connection((ip, port), timeout=1):
                return
        except OSError:
            time.sleep(1)
    raise RuntimeError(f'kubectl port-forward to {ip}:{port} did not start listening')


def retry_apply(manifest: str, env: dict[str, str] | None = None) -> None:
    """Apply a manifest, retrying while the Kueue webhook is still propagating its certificate."""
    last_error = None
    for _ in range(WEBHOOK_RETRY_ATTEMPTS):
        try:
            kubectl(['apply', '-f', manifest_path(manifest)], env=env)
            return
        except Exception as e:
            last_error = e
            time.sleep(5)
    raise RuntimeError(f'Failed to apply {manifest} after {WEBHOOK_RETRY_ATTEMPTS} attempts: {last_error}')


def find_job_workload(job_name: str, env: dict[str, str] | None = None) -> str:
    """Return the name of the Workload that Kueue's job controller created for a Job."""
    job_uid = kubectl_output(['get', 'job', job_name, '-n', NAMESPACE, '-o', 'jsonpath={.metadata.uid}'], env=env)
    for _ in range(WORKLOAD_DISCOVERY_ATTEMPTS):
        workload_name = kubectl_output(
            [
                'get',
                'workloads.kueue.x-k8s.io',
                '-n',
                NAMESPACE,
                '-l',
                f'kueue.x-k8s.io/job-uid={job_uid}',
                '-o',
                'jsonpath={.items[0].metadata.name}',
            ],
            env=env,
            check=False,
        )
        if workload_name:
            return workload_name
        time.sleep(1)
    raise RuntimeError(f'Failed to find Kueue Workload for Job {job_name}')


def wait_for_job_workload_condition(job_name: str, condition: str, env: dict[str, str] | None = None) -> str:
    """Wait for the Workload backing a Job to reach a condition, returning the Workload name."""
    workload_name = find_job_workload(job_name, env=env)
    kubectl(
        [
            'wait',
            f'workload/{workload_name}',
            '-n',
            NAMESPACE,
            f'--for=condition={condition}',
            f'--timeout={WAIT_TIMEOUT}',
        ],
        env=env,
    )
    return workload_name


def trigger_preemption(env: dict[str, str] | None = None) -> None:
    """Admit a low-priority workload, then a higher-priority one that preempts it, for preemption/eviction metrics.

    This runs at env-start so the counters are already non-zero when the metrics test scrapes, and again after
    the failover test, because the new leader starts its counters from zero. It does not give the check an
    observable Evicted *transition*: Kueue clears that condition as soon as it requeues the preempted workload,
    well inside a collection interval.
    """
    delete_jobs(PREEMPTION_JOBS, env=env)
    retry_apply('preempt-low-workload.yaml', env=env)
    wait_for_job_workload_condition('preempt-low-workload', 'Admitted=True', env=env)
    retry_apply('preempt-high-workload.yaml', env=env)
    wait_for_job_workload_condition('preempt-high-workload', 'Admitted=True', env=env)


def delete_jobs(job_names: list[str], env: dict[str, str] | None = None) -> None:
    """Delete Jobs and their Workloads, tolerating any that are already gone."""
    kubectl(
        ['delete', 'job', *job_names, '-n', NAMESPACE, '--ignore-not-found', f'--timeout={WAIT_TIMEOUT}'],
        env=env,
    )
