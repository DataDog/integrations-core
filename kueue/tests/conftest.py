# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import time
from contextlib import ExitStack

import pytest
import yaml

from datadog_checks.base.stubs import tagger
from datadog_checks.dev import get_here
from datadog_checks.dev.kind import kind_run
from datadog_checks.dev.kube_port_forward import port_forward
from datadog_checks.dev.subprocess import run_command

from .common import MOCKED_INSTANCE

HERE = get_here()
KUEUE_VERSION = os.environ.get('KUEUE_VERSION', 'v0.18.0')
KUEUE_NAMESPACE = 'kueue-system'  # hardcoded in the Kueue manifests


@pytest.fixture(autouse=True)
def reset_tagger():
    tagger.reset()
    yield
    tagger.reset()


def wait_for_controller():
    run_command(
        [
            'kubectl',
            'rollout',
            'status',
            'deployment/kueue-controller-manager',
            '-n',
            KUEUE_NAMESPACE,
            '--timeout=300s',
        ]
    )
    run_command(
        [
            'kubectl',
            'wait',
            'deployment/kueue-controller-manager',
            '--for=condition=Available',
            '-n',
            KUEUE_NAMESPACE,
            '--timeout=300s',
        ]
    )


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

    # Ensure the controller is ready
    wait_for_controller()

    run_command(['kubectl', 'apply', '-f', os.path.join(HERE, 'kind', 'kueue-config.yaml')])
    # Restart the controller to pick up the new config
    run_command(['kubectl', 'rollout', 'restart', 'deployment/kueue-controller-manager', '-n', KUEUE_NAMESPACE])
    wait_for_controller()

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
            KUEUE_NAMESPACE,
            '--timeout=300s',
        ]
    )
    apply_queue_manifests()
    run_command(['kubectl', 'wait', 'clusterqueue/cluster-queue', '--for=condition=Active', '--timeout=300s'])
    run_command(
        ['kubectl', 'wait', 'localqueue/user-queue', '-n', 'default', '--for=condition=Active', '--timeout=300s']
    )
    run_command(['kubectl', 'apply', '-f', os.path.join(HERE, 'kind', 'workloads.yaml')])
    wait_for_job_workload_condition('scheduled-workload', 'Admitted=True')
    wait_for_job_workload_condition('unschedulable-workload', 'QuotaReserved=False')


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


def wait_for_job_workload_condition(job_name: str, condition: str) -> None:
    job_uid = run_command(
        ['kubectl', 'get', 'job', job_name, '-n', 'default', '-o', 'jsonpath={.metadata.uid}'], capture=True
    ).stdout.strip()
    workload_name = ''
    for _ in range(10):
        workload_name = run_command(
            [
                'kubectl',
                'get',
                'workloads.kueue.x-k8s.io',
                '-n',
                'default',
                '-l',
                f'kueue.x-k8s.io/job-uid={job_uid}',
                '-o',
                'jsonpath={.items[0].metadata.name}',
            ],
            capture=True,
        ).stdout.strip()
        if workload_name:
            break
        time.sleep(1)
    if not workload_name:
        raise RuntimeError(f'Failed to find Kueue Workload for Job {job_name}')
    run_command(
        [
            'kubectl',
            'wait',
            f'workload/{workload_name}',
            '-n',
            'default',
            f'--for=condition={condition}',
            '--timeout=300s',
        ]
    )


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
        with open(kubeconfig) as f:
            kubeconfig_content = yaml.safe_load(f)

        kueue_host, kueue_port = stack.enter_context(
            port_forward(kubeconfig, 'kueue-system', 8443, 'service', 'kueue-controller-manager-metrics-service')
        )
        instances = [
            {
                'openmetrics_endpoint': f'https://{kueue_host}:{kueue_port}/metrics',
                'tls_verify': False,
                'extra_headers': {'Authorization': f'Bearer {get_service_account_token()}'},
                'collect_workload_events': True,
                'kube_config_dict': kubeconfig_content,
                'min_collection_interval': 3600,
            }
        ]

        yield {'instances': instances}


@pytest.fixture
def instance():
    return MOCKED_INSTANCE.copy()
