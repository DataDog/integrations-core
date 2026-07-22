# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
from contextlib import ExitStack, contextmanager

import pytest

from datadog_checks.dev import TempDir, run_command
from datadog_checks.dev.fs import path_join
from datadog_checks.dev.kind import KindLoad, kind_run
from datadog_checks.dev.kube_port_forward import port_forward

from .common import MOCKED_INSTANCE, PORT

HERE = os.path.dirname(os.path.abspath(__file__))
KIND_DIR = os.path.join(HERE, 'kind')


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


def get_instances(velero_host, velero_port, node_agent_host, node_agent_port):
    return {
        'instances': [
            {
                'openmetrics_endpoint': f"http://{velero_host}:{velero_port}/metrics",
                'tags': ['test:tag'],
            },
            {
                'openmetrics_endpoint': f"http://{node_agent_host}:{node_agent_port}/metrics",
                'tags': ['test:tag'],
            },
        ]
    }


@pytest.fixture(scope='session')
def dd_environment():
    kind_config = os.path.join(KIND_DIR, 'kind-config.yaml')
    custom_kubectl_image_tag = "custom-kubectl:latest"

    with TempDir('helm_dir') as helm_dir:
        with kind_run(
            wrappers=[build_and_load_kubectl_image(custom_kubectl_image_tag)],
            conditions=[KindLoad(custom_kubectl_image_tag), setup_velero],
            kind_config=kind_config,
            env_vars={
                "HELM_CACHE_HOME": path_join(helm_dir, 'Caches'),
                "HELM_CONFIG_HOME": path_join(helm_dir, 'Preferences'),
            },
        ) as kubeconfig:
            with ExitStack() as stack:
                ip_ports = [
                    stack.enter_context(port_forward(kubeconfig, 'velero', PORT, ressource, name))
                    for ressource, name in [('service', 'velero'), ('daemonset', 'node-agent')]
                ]

            instances = get_instances(ip_ports[0][0], ip_ports[0][1], ip_ports[1][0], ip_ports[1][1])

            yield instances


@pytest.fixture
def instance():
    return MOCKED_INSTANCE
