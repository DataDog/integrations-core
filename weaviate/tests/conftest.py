# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import os
import time
from contextlib import ExitStack
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import pytest

from datadog_checks.dev import get_here
from datadog_checks.dev.kind import kind_run
from datadog_checks.dev.kube_port_forward import port_forward
from datadog_checks.dev.subprocess import run_command
from datadog_checks.weaviate.check import DEFAULT_LIVENESS_ENDPOINT

from .common import BATCH_OBJECTS, USE_AUTH

HERE = get_here()
opj = os.path.join


def post_json(url: str, headers: dict[str, str], payload: object) -> None:
    try:
        with urlopen(
            Request(url, data=json.dumps(payload).encode('utf-8'), headers=headers, method='POST')
        ) as response:
            response.read()
    except HTTPError as e:
        with e:
            e.read()


def endpoint_ok(url: str, timeout: int) -> bool:
    try:
        with urlopen(url, timeout=timeout) as response:
            return response.status < 400
    except HTTPError as e:
        e.close()
        return False


def setup_weaviate():
    run_command(['kubectl', 'create', 'ns', 'weaviate'])

    if USE_AUTH:
        run_command(['kubectl', 'apply', '-f', opj(HERE, 'kind', 'weaviate_auth.yaml'), '-n', 'weaviate'])
    else:
        run_command(['kubectl', 'apply', '-f', opj(HERE, 'kind', 'weaviate_install.yaml'), '-n', 'weaviate'])

    # Tries to ensure that the Kubernetes resources are deployed and ready before we do anything else
    run_command(['kubectl', 'rollout', 'status', 'statefulset/weaviate', '-n', 'weaviate'])
    run_command(['kubectl', 'wait', 'pods', '--all', '-n', 'weaviate', '--for=condition=Ready', '--timeout=600s'])


@pytest.fixture(scope='session')
def dd_environment():
    with kind_run(conditions=[setup_weaviate]) as kubeconfig, ExitStack() as stack:
        weaviate_host, weaviate_port = stack.enter_context(
            port_forward(kubeconfig, 'weaviate', 2112, 'statefulset', 'weaviate')
        )
        weaviate_host, weaviate_api_port = stack.enter_context(
            port_forward(kubeconfig, 'weaviate', 8080, 'statefulset', 'weaviate')
        )

        instance = {
            'openmetrics_endpoint': f'http://{weaviate_host}:{weaviate_port}/metrics',
            'weaviate_api_endpoint': f'http://{weaviate_host}:{weaviate_api_port}',
        }
        if USE_AUTH:
            instance['headers'] = {'Authorization': 'Bearer test123'}

        make_weaviate_request(instance)
        yield instance


def make_weaviate_request(instance):
    # This helps seed some dummy data in to Weaviate to make some metrics available
    weaviate_api_endpoint = instance.get('weaviate_api_endpoint')
    weaviate_batch_endpoint = f'{weaviate_api_endpoint}/v1/batch/objects'
    headers = {'content-type': 'application/json'}

    if instance.get('headers'):
        headers.update(instance['headers'])

    if ready_check(weaviate_api_endpoint, 300):
        post_json(weaviate_batch_endpoint, headers, BATCH_OBJECTS)


def ready_check(endpoint, timeout=300):
    # Sometimes the API endpoint isn't ready when the cluster is ready. This will try to ensure the
    # API is ready for HTTP calls before we seed some dummy data.
    stop_time = time.time() + timeout
    endpoint = f'{endpoint}{DEFAULT_LIVENESS_ENDPOINT}'
    while time.time() < stop_time:
        try:
            if endpoint_ok(endpoint, timeout=5):
                return True
        except (URLError, TimeoutError) as e:
            print(f'Request failed: {e}')

        time.sleep(1)

    return False
