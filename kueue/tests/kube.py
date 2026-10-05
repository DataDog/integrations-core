# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""kubectl helpers shared by the Kueue kind environment setup and the e2e tests."""

import os
import time

from datadog_checks.dev import get_here
from datadog_checks.dev.subprocess import SubprocessResult, run_command

HERE = get_here()
NAMESPACE = 'default'
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


def delete_jobs(job_names: list[str], env: dict[str, str] | None = None) -> None:
    """Delete Jobs and their Workloads, tolerating any that are already gone."""
    kubectl(
        ['delete', 'job', *job_names, '-n', NAMESPACE, '--ignore-not-found', f'--timeout={WAIT_TIMEOUT}'],
        env=env,
    )
