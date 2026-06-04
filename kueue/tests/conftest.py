# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import time
from contextlib import ExitStack

import pytest

from datadog_checks.dev import get_here
from datadog_checks.dev.kind import kind_run
from datadog_checks.dev.kube_port_forward import port_forward
from datadog_checks.dev.subprocess import run_command

from .common import MOCKED_INSTANCE

HERE = get_here()
KUEUE_VERSION = os.environ.get('KUEUE_VERSION', 'v0.18.0')


def setup_kueue():
    run_command(
        [
            'kubectl',
            'apply',
            '--server-side',
            '-f',
            f'https://github.com/kubernetes-sigs/kueue/releases/download/{KUEUE_VERSION}/manifests.yaml',
        ]
    )
    run_command(
        [
            'kubectl',
            'wait',
            'deployment/kueue-controller-manager',
            '--for=condition=Available',
            '-n',
            'kueue-system',
            '--timeout=300s',
        ]
    )
    run_command(['kubectl', 'apply', '-f', os.path.join(HERE, 'kind', 'metrics-reader.yaml')])
    # The deployment can be `Available` before the webhook server is actually serving, so wait until the
    # webhook service has ready endpoints before applying resources that go through the mutating webhooks.
    run_command(
        [
            'kubectl',
            'wait',
            '--for=jsonpath={.subsets[*].addresses[*].ip}',
            'endpoints/kueue-webhook-service',
            '-n',
            'kueue-system',
            '--timeout=300s',
        ]
    )
    apply_queue_manifests()
    run_command(['kubectl', 'wait', 'clusterqueue/cluster-queue', '--for=condition=Active', '--timeout=300s'])
    run_command(
        ['kubectl', 'wait', 'localqueue/user-queue', '-n', 'default', '--for=condition=Active', '--timeout=300s']
    )


def apply_queue_manifests():
    # The webhook can still reject calls for a short window after its endpoints become ready (cert
    # propagation), so retry the apply a few times before giving up.
    queue_manifest = os.path.join(HERE, 'kind', 'queue.yaml')
    last_error = None
    for _ in range(10):
        try:
            run_command(['kubectl', 'apply', '-f', queue_manifest], check=True)
            return
        except Exception as e:
            last_error = e
            time.sleep(5)
    raise RuntimeError(f'Failed to apply queue manifests after retries: {last_error}')


def get_service_account_token():
    result = run_command(
        ['kubectl', 'create', 'token', 'kueue-metrics-reader', '-n', 'default'],
        capture=True,
    )
    return result.stdout.strip()


@pytest.fixture(scope='session')
def dd_environment():
    kind_config = os.path.join(HERE, 'kind', 'kind-config.yaml')
    with kind_run(conditions=[setup_kueue], kind_config=kind_config, sleep=10) as kubeconfig, ExitStack() as stack:
        kueue_host, kueue_port = stack.enter_context(
            port_forward(kubeconfig, 'kueue-system', 8443, 'service', 'kueue-controller-manager-metrics-service')
        )
        instances = [
            {
                'openmetrics_endpoint': f'https://{kueue_host}:{kueue_port}/metrics',
                'tls_verify': False,
                'extra_headers': {'Authorization': f'Bearer {get_service_account_token()}'},
            }
        ]

        yield {'instances': instances}


@pytest.fixture
def instance():
    return MOCKED_INSTANCE.copy()
