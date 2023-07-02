# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import os
import time

import pytest
import requests

from datadog_checks.dev import get_here
from datadog_checks.dev.kind import kind_run
from datadog_checks.dev.kube_port_forward import port_forward
from datadog_checks.dev.subprocess import run_command
from datadog_checks.weaviate.check import DEFAULT_LIVENESS_ENDPOINT

from .common import USE_AUTH, BATCH_OBJECTS

try:
    from contextlib import ExitStack
except ImportError:
    from contextlib2 import ExitStack


HERE = get_here()
opj = os.path.join


def setup_weaviate():
    run_command(["kubectl", "create", "ns", "weaviate"])

    if USE_AUTH:
        run_command(["kubectl", "apply", "-f", opj(HERE, 'kind', "weaviate_auth.yaml"), "-n", "weaviate"])
    else:
        run_command(["kubectl", "apply", "-f", opj(HERE, 'kind', "weaviate_install.yaml"), "-n", "weaviate"])
    run_command(["kubectl", "rollout", "status", "statefulset/weaviate", "-n", "weaviate"])
    run_command(["kubectl", "wait", "pods", "--all", "-n", "weaviate", "--for=condition=Ready", "--timeout=600s"])


@pytest.fixture(scope='session')
def dd_environment():
    with kind_run(conditions=[setup_weaviate]) as kubeconfig:

        with ExitStack() as stack:
            weaviate_host, weaviate_port = stack.enter_context(
                port_forward(kubeconfig, 'weaviate', 2112, 'statefulset', 'weaviate')
            )
            weaviate_host, weaviate_api_port = stack.enter_context(
                port_forward(kubeconfig, 'weaviate', 8080, 'statefulset', 'weaviate')
            )

            instance = {
                "openmetrics_endpoint": f"http://{weaviate_host}:{weaviate_port}/metrics",
                "weaviate_api_endpoint": f"http://{weaviate_host}:{weaviate_api_port}",
            }
            if USE_AUTH:
                instance["headers"] = {"Authorization": "Bearer test123"}

            make_weaviate_request(instance)
            yield instance


def make_weaviate_request(instance):
    weaviate_api_endpoint = instance.get('weaviate_api_endpoint')
    weaviate_batch_endpoint = f"{weaviate_api_endpoint}/v1/batch/objects"
    headers = {'content-type': 'application/json'}

    if instance.get('headers'):
        headers.update(instance['headers'])

    if ready_check(weaviate_api_endpoint, 300):
        requests.post(weaviate_batch_endpoint, headers=headers, data=json.dumps(BATCH_OBJECTS))



def ready_check(endpoint, timeout=300):
    stop_time = time.time() + timeout
    endpoint = f"{endpoint}{DEFAULT_LIVENESS_ENDPOINT}"
    while time.time() < stop_time:
        try:
            response = requests.get(endpoint, timeout=5)
            if response.ok:
                return True
        except requests.RequestException as e:
            print(f"Request failed: {e}")

        time.sleep(1)

    return False
