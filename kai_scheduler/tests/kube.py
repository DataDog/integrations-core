# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""kubectl helpers for the KAI Scheduler kind environment."""

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
