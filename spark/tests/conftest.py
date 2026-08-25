# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import time

import pytest
import requests
from datadog_test_libs.utils.mock_dns import mock_local

from datadog_checks.dev import docker_run
from datadog_checks.dev.conditions import CheckEndpoints, WaitFor
from datadog_checks.dev.kind import kind_run
from datadog_checks.dev.subprocess import run_command

from .common import (
    HERE,
    HOST,
    HOSTNAME_TO_PORT_MAPPING,
    INSTANCE_DRIVER_K8S,
    INSTANCE_STANDALONE,
    K8S_SPARK_DRIVER_SERVICE,
    K8S_SPARK_NAMESPACE,
)

KIND_MANIFEST = os.path.join(HERE, 'kind', 'spark-tests.yaml')
CHECK_ROOT = os.path.dirname(HERE)
SPARK_DRIVER_READY_TIMEOUT = 300  # seconds


@pytest.fixture(scope='session')
def dd_environment(dd_save_state):
    if os.environ.get('SPARK_PLATFORM') == 'k8s':
        with kind_run(conditions=[setup_spark_k8s]) as kubeconfig:
            metadata = {
                'agent_type': 'kubernetes',
                'kubernetes': {
                    'kubeconfig': kubeconfig,
                    'auto_conf': os.path.join(CHECK_ROOT, 'datadog_checks', 'spark', 'data', 'auto_conf.yaml'),
                },
            }
            dd_save_state('spark_kubeconfig', kubeconfig)
            yield INSTANCE_DRIVER_K8S, metadata
    else:
        with docker_run(
            compose_file=os.path.join(HERE, 'docker', 'docker-compose.yaml'),
            build=True,
            conditions=[
                CheckEndpoints(
                    [
                        'http://{}:4040/api/v1/applications'.format(HOST),
                        'http://{}:4050/api/v1/applications'.format(HOST),
                        'http://{}:4050/metrics/json'.format(HOST),
                    ]
                ),
                WaitFor(check_metrics_available, wait=5),
                WaitFor(check_executors_registered, wait=5, attempts=60),
            ],
            attempts=2,
        ):
            yield INSTANCE_STANDALONE, {'custom_hosts': get_custom_hosts()}


@pytest.fixture(scope='session')
def spark_kubeconfig(dd_get_state):
    return dd_get_state('spark_kubeconfig')


# --------------------------------------------------------------------------- #
# Kubernetes setup                                                            #
# --------------------------------------------------------------------------- #


def setup_spark_k8s():
    """Deploy Spark driver + words-sender on the disposable kind cluster."""
    run_command(['kubectl', 'apply', '-f', KIND_MANIFEST], check=True)

    # Wait for the words-sender to be ready before the Spark driver tries to
    # connect to it.
    run_command(
        [
            'kubectl',
            'wait',
            'deployment',
            'words-sender',
            '--namespace',
            K8S_SPARK_NAMESPACE,
            '--for=condition=Available',
            '--timeout=120s',
        ],
        check=True,
    )

    # Wait for the spark-driver deployment to be available (container running).
    run_command(
        [
            'kubectl',
            'wait',
            'deployment',
            'spark-driver',
            '--namespace',
            K8S_SPARK_NAMESPACE,
            '--for=condition=Available',
            '--timeout=300s',
        ],
        check=True,
    )

    # The deployment being Available only means the container is running, not
    # that the Spark UI is ready to serve requests.  Poll the API endpoint from
    # a temporary pod until it responds.
    _wait_for_spark_ui()


def _wait_for_spark_ui():
    """Poll the Spark driver UI until it responds."""
    deadline = time.monotonic() + SPARK_DRIVER_READY_TIMEOUT
    last_output = ''
    while time.monotonic() < deadline:
        result = run_command(
            [
                'kubectl',
                'run',
                'spark-ui-check',
                '--namespace',
                K8S_SPARK_NAMESPACE,
                '--image=curlimages/curl',
                '--restart=Never',
                '--attach',
                '--rm',
                '--quiet',
                '--',
                'curl',
                '-sf',
                'http://{}:4040/api/v1/applications'.format(K8S_SPARK_DRIVER_SERVICE),
            ],
            capture='both',
            check=False,
        )
        if result.code == 0:
            return
        last_output = result.stderr or result.stdout or ''
        time.sleep(5)

    raise RuntimeError(
        'Spark driver UI did not become ready within {}s. Last output: {}'.format(
            SPARK_DRIVER_READY_TIMEOUT, last_output
        )
    )


# --------------------------------------------------------------------------- #
# Docker (standalone) helpers                                                 #
# --------------------------------------------------------------------------- #


def check_metrics_available():
    endpoint = 'http://{}:4050/metrics/json'.format(HOST)
    r = requests.get(endpoint)
    return r.text.count("driver.spark.streaming") >= 6


def check_executors_registered():
    # Spark standalone executors are separate JVMs spawned by workers; they take time
    # to register with the driver after the application starts. Until at least one
    # non-driver executor appears, the /executors endpoint returns only the driver and
    # `spark.executor.*` metrics are never emitted, causing flaky integration tests.
    # The cluster runs a single worker with one core (SPARK_WORKER_CORES=1), so only one
    # of the two apps can own a non-driver executor at a time; either app having one is
    # enough for `test_integration_standalone` to observe executor metrics.
    for port in (4040, 4050):
        apps = requests.get('http://{}:{}/api/v1/applications'.format(HOST, port)).json()
        if not apps:
            continue
        app_id = apps[0]['id']
        executors = requests.get('http://{}:{}/api/v1/applications/{}/executors'.format(HOST, port, app_id)).json()
        if any(executor.get('id') != 'driver' for executor in executors):
            return True
    return False


def get_custom_hosts():
    return [(host, '127.0.0.1') for host in HOSTNAME_TO_PORT_MAPPING]


@pytest.fixture(scope='session', autouse=True)
def mock_local_tls_dns():
    # The mock DNS fixture is only needed for the Docker-based standalone tests
    # where the host process needs to resolve container hostnames.  In k8s mode
    # the Agent pod runs inside the cluster and uses Kubernetes DNS.
    if os.environ.get('SPARK_PLATFORM') == 'k8s':
        yield
        return

    with mock_local(HOSTNAME_TO_PORT_MAPPING):
        yield
