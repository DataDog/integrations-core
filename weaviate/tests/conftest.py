# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import os

import pytest

from datadog_checks.dev import get_here
from datadog_checks.dev._env import get_state, save_state
from datadog_checks.dev.kind import kind_run
from datadog_checks.dev.subprocess import run_command

from .common import BATCH_OBJECTS, USE_AUTH

HERE = get_here()
opj = os.path.join

NAMESPACE = 'weaviate'
# No Service targets the StatefulSet's metrics port, only the API port (see weaviate_install.yaml /
# weaviate_auth.yaml), so the API endpoint uses Service DNS while metrics fall back to the pod IP.
WEAVIATE_API_ENDPOINT = f'http://weaviate.{NAMESPACE}.svc.cluster.local:80'
POD_IP_STATE = 'weaviate_pod_ip'


def setup_weaviate():
    run_command(['kubectl', 'create', 'ns', 'weaviate'], check=True)

    if USE_AUTH:
        run_command(['kubectl', 'apply', '-f', opj(HERE, 'kind', 'weaviate_auth.yaml'), '-n', 'weaviate'], check=True)
    else:
        run_command(
            ['kubectl', 'apply', '-f', opj(HERE, 'kind', 'weaviate_install.yaml'), '-n', 'weaviate'], check=True
        )

    # Tries to ensure that the Kubernetes resources are deployed and ready before we do anything else
    run_command(['kubectl', 'rollout', 'status', 'statefulset/weaviate', '-n', 'weaviate'], check=True)
    run_command(
        ['kubectl', 'wait', 'pods', '--all', '-n', 'weaviate', '--for=condition=Ready', '--timeout=600s'],
        check=True,
    )

    # `setup_weaviate` only runs once, on the initial `ddev env start`. Later invocations of the
    # `dd_environment` fixture (e.g. during `ddev env stop`) run in a fresh process after the cluster
    # is torn down, so the pod IP is cached here via `save_state`/`get_state` rather than looked up live.
    save_state(POD_IP_STATE, get_weaviate_pod_ip())

    make_weaviate_request()


def get_weaviate_pod_ip() -> str:
    result = run_command(
        ['kubectl', 'get', 'pods', '--namespace', NAMESPACE, '--selector', 'app=weaviate', '--output', 'json'],
        capture='out',
        check=True,
    )
    pods = json.loads(result.stdout)['items']
    if len(pods) != 1 or not pods[0].get('status', {}).get('podIP'):
        raise RuntimeError(f'Expected one ready Weaviate pod, found {len(pods)}')
    return pods[0]['status']['podIP']


def make_weaviate_request():
    # This helps seed some dummy data in to Weaviate to make some metrics available. Run from a
    # temporary pod since the host cannot reach the cluster directly.
    weaviate_batch_endpoint = f'{WEAVIATE_API_ENDPOINT}/v1/batch/objects'

    command = [
        'kubectl',
        'run',
        'weaviate-seed-data',
        '--namespace',
        NAMESPACE,
        '--image=curlimages/curl',
        '--restart=Never',
        '--attach',
        '--rm',
        '--quiet',
        '--',
        'curl',
        '-sf',
        '-X',
        'POST',
        weaviate_batch_endpoint,
        '-H',
        'Content-Type: application/json',
    ]
    if USE_AUTH:
        command.extend(['-H', 'Authorization: Bearer test123'])
    command.extend(['-d', json.dumps(BATCH_OBJECTS)])

    run_command(command, capture='both', check=True)


@pytest.fixture(scope='session')
def dd_environment():
    with kind_run(conditions=[setup_weaviate]) as kubeconfig:
        weaviate_metrics_port = 2112

        instance = {
            'openmetrics_endpoint': f'http://{get_state(POD_IP_STATE)}:{weaviate_metrics_port}/metrics',
            'weaviate_api_endpoint': WEAVIATE_API_ENDPOINT,
        }
        if USE_AUTH:
            instance['headers'] = {'Authorization': 'Bearer test123'}

        metadata = {'agent_type': 'kubernetes', 'kubernetes': {'kubeconfig': kubeconfig}}

        yield instance, metadata
