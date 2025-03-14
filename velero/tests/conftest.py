# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import time
from contextlib import ExitStack

import pytest

from datadog_checks.dev import run_command
from datadog_checks.dev.kind import kind_run
from datadog_checks.dev.kube_port_forward import port_forward

from .common import MOCKED_INSTANCE, PORT

HERE = os.path.dirname(os.path.abspath(__file__))
KIND_DIR = os.path.join(HERE, 'kind')


def setup_velero():
    """Set up Velero and MinIO in the Kind cluster."""
    run_command(['kubectl', 'create', 'namespace', 'velero'], check=True)

    # Deploy MinIO
    run_command(['kubectl', 'apply', '-f', os.path.join(KIND_DIR, 'minio.yaml')], check=True)

    for attempt in range(12):
        try:
            run_command(
                ['kubectl', 'wait', '--for=condition=ready', 'pod', '-l', 'app=minio', '-n', 'velero', '--timeout=60s'],
                check=True,
            )
            break
        except Exception:
            if attempt == 11:
                raise Exception("Timed out waiting for MinIO pod to exist")
            time.sleep(5)

    # Install Velero
    run_command(
        [
            'velero',
            'install',
            '--provider',
            'aws',
            '--plugins',
            'velero/velero-plugin-for-aws:v1.7.1',
            '--bucket',
            'velero',
            '--secret-file',
            os.path.join(KIND_DIR, 'credentials-velero'),
            '--use-volume-snapshots=false',
            '--use-node-agent',
            '--backup-location-config',
            'region=minio,s3ForcePathStyle=true,s3Url=http://minio.velero.svc:9000',
        ],
        check=True,
    )

    for attempt in range(12):
        try:
            run_command(
                [
                    'kubectl',
                    'wait',
                    '--for=condition=ready',
                    'pod',
                    '-l',
                    'deploy=velero',
                    '-n',
                    'velero',
                    '--timeout=60s',
                ],
                check=True,
            )
            break
        except Exception:
            if attempt == 11:
                raise Exception("Timed out waiting for Velero pod to exist")
            time.sleep(5)


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

    with kind_run(
        conditions=[setup_velero],
        kind_config=kind_config,
    ) as kubeconfig:
        with ExitStack() as stack:
            ip_ports = [
                stack.enter_context(port_forward(kubeconfig, 'velero', PORT, ressource, name))
                for ressource, name in [('deployment', 'velero'), ('daemonset', 'node-agent')]
            ]

        instances = get_instances(ip_ports[0][0], ip_ports[0][1], ip_ports[1][0], ip_ports[1][1])

        yield instances


@pytest.fixture
def instance():
    return MOCKED_INSTANCE
