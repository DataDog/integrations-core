# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import os
from contextlib import contextmanager

import pytest

from datadog_checks.dev import TempDir, run_command
from datadog_checks.dev._env import get_state, save_state
from datadog_checks.dev.fs import path_join
from datadog_checks.dev.kind import KindLoad, kind_run

from .common import MOCKED_INSTANCE, PORT

HERE = os.path.dirname(os.path.abspath(__file__))
CHECK_ROOT = os.path.dirname(HERE)
KIND_DIR = os.path.join(HERE, 'kind')
NODE_AGENT_IP_STATE = 'velero_node_agent_ip'


@contextmanager
def build_and_load_kubectl_image(image_tag: str):
    print("Building custom kubectl image...")
    dockerfile_path = os.path.join(KIND_DIR, 'kubectl.Dockerfile')

    # Build the custom kubectl image
    run_command(
        ['docker', 'build', '-t', image_tag, '-f', dockerfile_path, '.'],
        check=True,
    )
    yield


def setup_velero():
    """Set up Velero, MinIO and Nginx in the Kind cluster."""
    # Apply MinIO deployment
    run_command(['kubectl', 'apply', '-f', os.path.join(KIND_DIR, 'minio.yaml'), '--wait'], check=True)

    # Apply Nginx deployment
    run_command(['kubectl', 'apply', '-f', os.path.join(KIND_DIR, 'nginx.yaml'), '--wait'], check=True)

    # Add Velero Helm repo
    run_command(['helm', 'repo', 'add', 'vmware-tanzu', 'https://vmware-tanzu.github.io/helm-charts'], check=True)

    # Install Velero using Helm
    run_command(
        [
            'helm',
            'install',
            'velero',
            'vmware-tanzu/velero',
            '--namespace',
            'velero',
            '--values',
            os.path.join(KIND_DIR, 'velero-values.yaml'),
            '--wait',
        ],
        check=True,
    )
    save_state(NODE_AGENT_IP_STATE, get_node_agent_ip())


def get_node_agent_ip():
    result = run_command(
        ['kubectl', 'get', 'pods', '--namespace', 'velero', '--output', 'json'],
        capture='out',
        check=True,
    )
    node_agent_pods = [
        pod
        for pod in json.loads(result.stdout)['items']
        if any(
            owner.get('kind') == 'DaemonSet' and owner.get('name') == 'node-agent'
            for owner in pod['metadata'].get('ownerReferences', [])
        )
    ]
    if len(node_agent_pods) != 1 or not node_agent_pods[0].get('status', {}).get('podIP'):
        raise RuntimeError(f'Expected one ready Velero node-agent pod, found {len(node_agent_pods)}')
    return node_agent_pods[0]['status']['podIP']


def get_instances(node_agent_ip):
    return {
        'instances': [
            {
                'openmetrics_endpoint': f"http://velero.velero.svc.cluster.local:{PORT}/metrics",
                'tags': ['test:tag'],
            },
            {
                'openmetrics_endpoint': f"http://{node_agent_ip}:{PORT}/metrics",
                'tags': ['test:tag'],
            },
        ]
    }


@pytest.fixture(scope='session')
def dd_environment():
    custom_kubectl_image_tag = "custom-kubectl:latest"

    with TempDir('helm_dir') as helm_dir:
        with kind_run(
            wrappers=[build_and_load_kubectl_image(custom_kubectl_image_tag)],
            conditions=[KindLoad(custom_kubectl_image_tag), setup_velero],
            env_vars={
                "HELM_CACHE_HOME": path_join(helm_dir, 'Caches'),
                "HELM_CONFIG_HOME": path_join(helm_dir, 'Preferences'),
            },
        ) as kubeconfig:
            instances = get_instances(get_state(NODE_AGENT_IP_STATE))
            metadata = {
                'agent_type': 'kubernetes',
                'kubernetes': {
                    'kubeconfig': kubeconfig,
                    'auto_conf': os.path.join(CHECK_ROOT, 'datadog_checks', 'velero', 'data', 'auto_conf.yaml'),
                },
            }

            yield instances, metadata


@pytest.fixture
def instance():
    return MOCKED_INSTANCE
