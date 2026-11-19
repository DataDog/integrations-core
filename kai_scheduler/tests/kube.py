# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""kubectl helpers for the KAI Scheduler kind environment."""

import json
import os
import time

from datadog_checks.dev import get_here
from datadog_checks.dev.subprocess import SubprocessResult, run_command

HERE = get_here()
KAI_NAMESPACE = 'kai-scheduler'
WORKLOAD_NAMESPACE = 'default'
WAIT_TIMEOUT = '300s'
DEPLOYMENT_DISCOVERY_ATTEMPTS = 60
WEBHOOK_RETRY_ATTEMPTS = 10


def manifest_path(name: str) -> str:
    return os.path.join(HERE, 'kind', name)


def kubectl(args: list[str], check: bool = True, **kwargs) -> SubprocessResult:
    """Run kubectl, raising on a non-zero exit code by default so a failed wait cannot pass silently."""
    return run_command(['kubectl', *args], check=check, **kwargs)


def kubectl_output(args: list[str], check: bool = True) -> str:
    return kubectl(args, check=check, capture=True).stdout.strip()


def retry_apply(manifest: str) -> None:
    """Apply a manifest, retrying while the KAI admission and queue webhooks are still starting."""
    last_error = None
    for _ in range(WEBHOOK_RETRY_ATTEMPTS):
        try:
            kubectl(['apply', '-f', manifest_path(manifest)])
            return
        except Exception as e:
            last_error = e
            time.sleep(5)
    raise RuntimeError(f'Failed to apply {manifest} after {WEBHOOK_RETRY_ATTEMPTS} attempts: {last_error}')


def wait_for_deployment(name: str) -> None:
    """Wait for a deployment that the KAI operator creates asynchronously, so it may not exist yet."""
    for _ in range(DEPLOYMENT_DISCOVERY_ATTEMPTS):
        if kubectl(['get', 'deployment', name, '-n', KAI_NAMESPACE], check=False, capture=True).code == 0:
            break
        time.sleep(5)
    else:
        raise RuntimeError(f'The KAI operator did not create deployment {KAI_NAMESPACE}/{name}')

    kubectl(['rollout', 'status', f'deployment/{name}', '-n', KAI_NAMESPACE, f'--timeout={WAIT_TIMEOUT}'])


def wait_for_pod(name: str, condition: str) -> None:
    kubectl(['wait', f'pod/{name}', '-n', WORKLOAD_NAMESPACE, f'--for={condition}', f'--timeout={WAIT_TIMEOUT}'])


def trigger_preemption() -> None:
    """Run a preemptible pod, then a higher-priority pod that only fits in `team-a` by evicting it."""
    retry_apply('preempt-low-pod.yaml')
    wait_for_pod('preempt-low-pod', 'condition=Ready')
    retry_apply('preempt-high-pod.yaml')
    wait_for_pod('preempt-high-pod', 'condition=Ready')


def delete_preemption_pods() -> None:
    kubectl(
        ['delete', 'pod', 'preempt-low-pod', 'preempt-high-pod', '-n', WORKLOAD_NAMESPACE, '--ignore-not-found'],
    )


def podgroup_owned_by(owner: str) -> str:
    """Return the name of the PodGroup that the KAI pod grouper created for a pod or Job."""
    podgroups = json.loads(kubectl_output(['get', 'podgroups', '-n', WORKLOAD_NAMESPACE, '-o', 'json']))['items']
    for podgroup in podgroups:
        if any(reference.get('name') == owner for reference in podgroup['metadata'].get('ownerReferences', [])):
            return podgroup['metadata']['name']
    raise RuntimeError(f'No PodGroup is owned by {WORKLOAD_NAMESPACE}/{owner}')


def run_event_job() -> None:
    retry_apply('event-job.yaml')
    # The Job controller creates the pod asynchronously, and waiting on a selector that matches no pod fails at once.
    kubectl(
        [
            'wait',
            'job/event-job',
            '-n',
            WORKLOAD_NAMESPACE,
            '--for=jsonpath={.status.active}=1',
            f'--timeout={WAIT_TIMEOUT}',
        ]
    )
    kubectl(
        [
            'wait',
            'pod',
            '-l',
            'job-name=event-job',
            '-n',
            WORKLOAD_NAMESPACE,
            '--for=condition=Ready',
            f'--timeout={WAIT_TIMEOUT}',
        ]
    )


def delete_event_job() -> None:
    kubectl(['delete', 'job', 'event-job', '-n', WORKLOAD_NAMESPACE, '--ignore-not-found', '--cascade=foreground'])
