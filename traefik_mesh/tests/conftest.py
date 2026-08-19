# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import os
from copy import deepcopy

import pytest

from datadog_checks.dev import get_here
from datadog_checks.dev._env import get_state, save_state
from datadog_checks.dev.kind import kind_run
from datadog_checks.dev.subprocess import run_command

HERE = get_here()
opj = os.path.join

PROXY_IP_STATE = 'traefik_mesh_proxy_ip'


@pytest.fixture
def instance_openmetrics_v2(dd_get_state):
    openmetrics_v2 = deepcopy(dd_get_state('traefik_instance', default={}))
    openmetrics_v2['use_openmetrics'] = 'true'
    return openmetrics_v2


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
    # The proxy DaemonSet is what the Agent scrapes, and its pod gets an IP as soon as it is scheduled,
    # before Traefik listens on port 8080, so wait for the rollout to report the pod as ready.
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

    # This only runs once, when the Kind cluster is created, so the resolved pod IP is cached here
    # rather than re-resolved by `dd_environment` on every invocation.
    save_state(PROXY_IP_STATE, get_traefik_mesh_proxy_pod_ip())


def get_traefik_mesh_proxy_pod_ip() -> str:
    # There is no Service for the Traefik Mesh proxy, so the pod IP is fetched directly.
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
    if len(pods) != 1 or not pods[0].get('status', {}).get('podIP'):
        raise RuntimeError(f'Expected exactly one traefik-mesh-proxy pod with a pod IP, found {len(pods)}')
    return pods[0]['status']['podIP']


@pytest.fixture(scope='session')
def dd_environment(dd_save_state):
    with kind_run(conditions=[setup_traefik_mesh]) as kubeconfig:
        proxy_pod_ip = get_state(PROXY_IP_STATE)
        traefik_proxy_endpoint = f'http://{proxy_pod_ip}:8080/metrics'
        traefik_controller_api_endpoint = 'http://traefik-mesh-controller.traefik-mesh.svc.cluster.local:9000'

        instance = {
            'openmetrics_endpoint': traefik_proxy_endpoint,
            'traefik_proxy_api_endpoint': traefik_proxy_endpoint,
            'traefik_controller_api_endpoint': traefik_controller_api_endpoint,
        }

        dd_save_state("traefik_instance", instance)
        metadata = {'agent_type': 'kubernetes', 'kubernetes': {'kubeconfig': kubeconfig}}

        yield instance, metadata
