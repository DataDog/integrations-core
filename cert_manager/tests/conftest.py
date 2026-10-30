# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import os

import pytest

from datadog_checks.dev import run_command
from datadog_checks.dev.kind import kind_run


HERE = os.path.dirname(os.path.abspath(__file__))
PORT = 9402


def setup_cert_manager():
    # Deploy Cert Manager
    run_command(
        [
            "kubectl",
            "apply",
            "-f",
            "https://github.com/jetstack/cert-manager/releases/download/v1.6.0/cert-manager.yaml",
        ]
    )
    run_command(
        ["kubectl", "wait", "deployments", "--all", "--for=condition=Available", "-n", "cert-manager", "--timeout=300s"]
    )
    run_command(["kubectl", "wait", "pods", "-n", "cert-manager", "--all", "--for=condition=Ready", "--timeout=300s"])

    # Issue self-signed certs
    config = os.path.join(HERE, 'kubernetes', 'selfsigned.yaml')
    run_command(["kubectl", "create", "-f", config])
    run_command(
        [
            "kubectl",
            "wait",
            "certificates",
            "-n",
            "cert-manager-test",
            "--all",
            "--for=condition=Ready",
            "--timeout=300s",
        ]
    )

    # Deploy Pebble
    config = os.path.join(HERE, 'kubernetes', 'pebble.yaml')
    run_command(["kubectl", "create", "-f", config])

    # Deploy Nginx
    config = os.path.join(HERE, 'kubernetes', 'nginx.yaml')
    run_command(["kubectl", "create", "-f", config])

    # Wait for deployments
    run_command(["kubectl", "wait", "deployments", "--all", "--for=condition=Available", "--timeout=300s"])

    # Issue acme certs
    config = os.path.join(HERE, 'kubernetes', 'acme.yaml')
    run_command(["kubectl", "create", "-f", config])
    run_command(
        [
            "kubectl",
            "wait",
            "certificates",
            "-n",
            "acme-test",
            "--all",
            "--for=condition=Ready",
            "--timeout=300s",
        ]
    )


@pytest.fixture(scope='session')
def dd_environment():
    with kind_run(conditions=[setup_cert_manager]) as kubeconfig:
        pods = []
        for selector in ('app.kubernetes.io/component=controller', 'app=cert-manager'):
            result = run_command(
                [
                    "kubectl",
                    "get",
                    "pods",
                    "--namespace",
                    "cert-manager",
                    "--selector",
                    selector,
                    "--output",
                    "json",
                ],
                capture='out',
                check=True,
            )
            pods = json.loads(result.stdout)['items']
            if pods:
                break

        if len(pods) != 1 or not pods[0].get('status', {}).get('podIP'):
            raise RuntimeError(f'Expected exactly one ready cert-manager controller pod, found {len(pods)}')

        controller_ip = pods[0]['status']['podIP']
        instances = {
            'instances': [
                {'openmetrics_endpoint': f'http://{controller_ip}:{PORT}/metrics'},
            ]
        }
        metadata = {'agent_type': 'kubernetes', 'kubernetes': {'kubeconfig': kubeconfig}}

        yield instances, metadata


@pytest.fixture
def instance():
    return {}
