# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import os

import pytest

from datadog_checks.dev import get_here
from datadog_checks.dev._env import get_state, save_state, set_up_env
from datadog_checks.dev.kind import kind_run
from datadog_checks.dev.subprocess import run_command

HERE = get_here()
opj = os.path.join

PROXY_IP_STATE = 'traefik_mesh_proxy_ip'


def setup_traefik_mesh():
    run_command(["kubectl", "create", "namespace", "traefik-mesh"])
    # SMI CRDs are not installed by the Helm chart, so we need to install them manually
    run_command(
        [
            "kubectl",
            "apply",
            "--server-side",
            "--force-conflicts",
            "-k",
            "https://github.com/traefik/mesh-helm-chart/mesh/crds/",
            "-n",
            "traefik-mesh",
        ]
    )
    run_command(["kubectl", "apply", "-f", opj(HERE, "kind", "traefik_mesh.yaml"), "-n", "traefik-mesh"])
    run_command(
        ["kubectl", "wait", "deployments", "--all", "--for=condition=Available", "-n", "traefik-mesh", "--timeout=90s"]
    )
    run_command(
        [
            "kubectl",
            "rollout",
            "status",
            "daemonset/traefik-mesh-proxy",
            "--namespace",
            "traefik-mesh",
            "--timeout=90s",
        ],
        check=True,
    )

    # `setup_traefik_mesh` only runs while the environment is being set up. Later invocations of the
    # `dd_environment` fixture (e.g. during `ddev env stop`) run in a fresh process, and by then the
    # cluster may already be gone, so the pod IP is cached here via `save_state`/`get_state` rather
    # than looked up live.
    save_state(PROXY_IP_STATE, get_traefik_mesh_proxy_pod_ip())


def get_traefik_mesh_proxy_pod_ip() -> str:
    result = run_command(
        [
            "kubectl",
            "get",
            "pods",
            "--namespace",
            "traefik-mesh",
            "--selector",
            "app=maesh,component=maesh-mesh,release=traefik-mesh",
            "--output",
            "json",
        ],
        capture='out',
        check=True,
    )
    pods = json.loads(result.stdout)['items']
    if len(pods) != 1:
        pod_names = [pod['metadata']['name'] for pod in pods]
        raise RuntimeError(f'Expected exactly one traefik-mesh-proxy pod, found {len(pods)}: {pod_names}')

    pod = pods[0]
    pod_ip = pod.get('status', {}).get('podIP')
    if not pod_ip:
        pod_name = pod['metadata']['name']
        pod_phase = pod.get('status', {}).get('phase')
        raise RuntimeError(f'The traefik-mesh-proxy pod {pod_name} has no pod IP (phase: {pod_phase})')

    return pod_ip


@pytest.fixture(scope='session')
def dd_environment():
    with kind_run(conditions=[setup_traefik_mesh]) as kubeconfig:
        proxy_pod_ip = get_state(PROXY_IP_STATE)
        if set_up_env() and not proxy_pod_ip:
            raise RuntimeError(f'No Traefik Mesh proxy pod IP found in the `{PROXY_IP_STATE}` state')

        traefik_proxy_api_endpoint = f'http://{proxy_pod_ip}:8080'
        traefik_proxy_metrics_endpoint = f'{traefik_proxy_api_endpoint}/metrics'
        traefik_controller_api_endpoint = 'http://traefik-mesh-controller.traefik-mesh.svc.cluster.local:9000'

        instance = {
            'openmetrics_endpoint': traefik_proxy_metrics_endpoint,
            'traefik_proxy_api_endpoint': traefik_proxy_api_endpoint,
            'traefik_controller_api_endpoint': traefik_controller_api_endpoint,
        }

        metadata = {'agent_type': 'kubernetes', 'kubernetes': {'kubeconfig': kubeconfig}}

        yield instance, metadata
