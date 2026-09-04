# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import platform
import tempfile

import pytest

from datadog_checks.dev import get_here
from datadog_checks.dev.kind import ClusterConfig, kind_run
from datadog_checks.dev.subprocess import run_command

HERE = get_here()
CHECK_ROOT = os.path.dirname(HERE)

KUMA_NAMESPACE = 'kuma-system'
KUMA_SERVICE = 'kuma-control-plane'
KUMA_STARTUP_TIMEOUT = 600
KUMA_METRICS_ENDPOINT = f'http://{KUMA_SERVICE}.{KUMA_NAMESPACE}.svc.cluster.local:5680/metrics'
KUMA_VERSION = os.environ.get('KUMA_VERSION', '2.10.6')
KUMA_IMAGES = [f'kumahq/kuma-cp:{KUMA_VERSION}', f'kumahq/kumactl:{KUMA_VERSION}']


class PreloadImages:
    """Side-load locally cached chart images so the kind nodes don't pull them from Docker Hub.

    Images that are not already in the local Docker cache are skipped and pulled by the
    nodes as usual, so this never adds a download. Run `docker pull` on them once to
    speed up subsequent runs.
    """

    def add_cluster_info(self, cluster_config: ClusterConfig):
        self.cluster_name = cluster_config.cluster_name

    def __call__(self):
        # The archive must be single-platform: `kind load docker-image` fails on
        # multi-arch images when Docker uses the containerd image store.
        spec = f'{platform.system().lower()}/{platform.machine()}'
        for image in KUMA_IMAGES:
            if run_command(['docker', 'image', 'inspect', image], capture=True).code != 0:
                continue
            with tempfile.TemporaryDirectory() as tmp_dir:
                archive = os.path.join(tmp_dir, 'image.tar')
                run_command(['docker', 'save', '--platform', spec, image, '-o', archive], check=True)
                run_command(['kind', 'load', 'image-archive', archive, '--name', self.cluster_name], check=True)


def setup_kuma():
    run_command(['kubectl', 'create', 'namespace', KUMA_NAMESPACE], check=True)
    run_command(['helm', 'repo', 'add', 'kuma', 'https://kumahq.github.io/charts'], check=True)
    run_command(['helm', 'repo', 'update'], check=True)
    run_command(
        [
            'helm',
            'upgrade',
            '--install',
            'kuma',
            'kuma/kuma',
            '--version',
            KUMA_VERSION,
            '--create-namespace',
            '-n',
            KUMA_NAMESPACE,
        ],
        check=True,
    )
    run_command(
        [
            'kubectl',
            'rollout',
            'status',
            f'deployment/{KUMA_SERVICE}',
            '-n',
            KUMA_NAMESPACE,
            # The Kuma deployment's readiness probe checks its in-cluster /ready endpoint.
            f'--timeout={KUMA_STARTUP_TIMEOUT}s',
        ],
        check=True,
    )


@pytest.fixture(scope='session')
def dd_environment(dd_save_state):
    with kind_run(conditions=[PreloadImages(), setup_kuma]) as kubeconfig:
        instance = {'openmetrics_endpoint': KUMA_METRICS_ENDPOINT}
        metadata = {
            'agent_type': 'kubernetes',
            'kubernetes': {
                'kubeconfig': kubeconfig,
                'auto_conf': os.path.join(CHECK_ROOT, 'datadog_checks', 'kuma', 'data', 'auto_conf.yaml'),
            },
        }

        dd_save_state('kuma_instance', instance)
        dd_save_state('kuma_kubeconfig', kubeconfig)
        yield instance, metadata


@pytest.fixture(scope='session')
def instance(dd_get_state):
    return dd_get_state(
        'kuma_instance',
        default={
            'openmetrics_endpoint': 'http://localhost:5680/metrics',
        },
    )


@pytest.fixture(scope='session')
def kuma_kubeconfig(dd_get_state):
    return dd_get_state('kuma_kubeconfig')
