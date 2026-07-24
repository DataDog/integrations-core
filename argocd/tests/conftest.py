# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
from copy import deepcopy

import pytest

from datadog_checks.dev import get_here
from datadog_checks.dev.kind import kind_run
from datadog_checks.dev.kube_port_forward import port_forward
from datadog_checks.dev.subprocess import run_command

try:
    from contextlib import ExitStack
except ImportError:
    from contextlib2 import ExitStack


HERE = get_here()
opj = os.path.join


@pytest.fixture
def instance_openmetrics_v2(dd_get_state):
    openmetrics_v2 = deepcopy(dd_get_state('argocd_instance', default={}))
    openmetrics_v2['use_openmetrics'] = 'true'
    return openmetrics_v2


@pytest.fixture
def genresources_instance(dd_get_state):
    # Generic-resources-only instance (no OpenMetrics scrape); endpoint + token are minted per env run.
    return deepcopy(dd_get_state('argocd_genresources_instance', default={}))


def setup_argocd():
    run_command(["kubectl", "create", "ns", "argocd"])
    run_command(["kubectl", "apply", "-f", opj(HERE, 'kind', "argocd_install.yaml"), "-n", "argocd"])
    run_command(
        ["kubectl", "wait", "deployments", "--all", "--for=condition=Available", "-n", "argocd", "--timeout=300s"]
    )
    run_command(["kubectl", "wait", "pods", "--all", "--for=condition=Ready", "--timeout=300s"])
    # Register a sample Application so the generic resources collector has one to poll and stream.
    run_command(["kubectl", "wait", "--for=condition=established", "crd/applications.argoproj.io", "--timeout=60s"])
    run_command(["kubectl", "apply", "-f", opj(HERE, 'kind', "e2e_application.yaml")])


def _argocd_admin_token(kubeconfig, base_url):
    """Log in as the initial admin and return an API bearer token for the generic resources REST calls."""
    import base64
    import subprocess
    import time

    import requests
    import urllib3

    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    password = base64.b64decode(
        subprocess.check_output(
            [
                "kubectl",
                "--kubeconfig",
                kubeconfig,
                "-n",
                "argocd",
                "get",
                "secret",
                "argocd-initial-admin-secret",
                "-o",
                "jsonpath={.data.password}",
            ]
        )
    ).decode()
    last_error = None
    for _ in range(30):
        try:
            response = requests.post(
                base_url + "/api/v1/session",
                json={"username": "admin", "password": password},
                verify=False,
                timeout=10,
            )
            response.raise_for_status()
            return response.json()["token"]
        except Exception as error:  # retry until the port-forward + API server are ready
            last_error = error
            time.sleep(2)
    raise RuntimeError("could not obtain an ArgoCD API token: {}".format(last_error))


@pytest.fixture(scope='session')
def dd_environment(dd_save_state):
    with kind_run(conditions=[setup_argocd]) as kubeconfig:
        with ExitStack() as stack:
            app_controller_host, app_controller_port = stack.enter_context(
                port_forward(kubeconfig, 'argocd', 8082, 'service', 'argocd-metrics')
            )
            appset_controller_host, appset_controller_port = stack.enter_context(
                port_forward(kubeconfig, 'argocd', 8080, 'service', 'argocd-applicationset-controller')
            )
            api_server_host, api_server_port = stack.enter_context(
                port_forward(kubeconfig, 'argocd', 8083, 'service', 'argocd-server-metrics')
            )
            repo_server_host, repo_server_port = stack.enter_context(
                port_forward(kubeconfig, 'argocd', 8084, 'service', 'argocd-repo-server')
            )
            notifications_controller_host, notifications_controller_port = stack.enter_context(
                port_forward(kubeconfig, 'argocd', 9001, 'service', 'argocd-notifications-controller-metrics')
            )
            genresources_host, genresources_port = stack.enter_context(
                port_forward(kubeconfig, 'argocd', 443, 'service', 'argocd-server')
            )
            genresources_endpoint = 'https://{}:{}'.format(genresources_host, genresources_port)
            genresources_token = _argocd_admin_token(kubeconfig, genresources_endpoint)
            app_controller_endpoint = 'http://{}:{}/metrics'.format(app_controller_host, app_controller_port)
            appset_controller_endpoint = 'http://{}:{}/metrics'.format(appset_controller_host, appset_controller_port)
            api_server_endpoint = 'http://{}:{}/metrics'.format(api_server_host, api_server_port)
            repo_server_endpoint = 'http://{}:{}/metrics'.format(repo_server_host, repo_server_port)
            notifications_controller_endpoint = 'http://{}:{}/metrics'.format(
                notifications_controller_host, notifications_controller_port
            )

            instance = {
                'app_controller_endpoint': app_controller_endpoint,
                'appset_controller_endpoint': appset_controller_endpoint,
                'api_server_endpoint': api_server_endpoint,
                'repo_server_endpoint': repo_server_endpoint,
                'notifications_controller_endpoint': notifications_controller_endpoint,
            }

            # save this instance to use for openmetrics_v2 instance, since the endpoint is different each run
            dd_save_state("argocd_instance", instance)
            dd_save_state(
                "argocd_genresources_instance",
                {
                    'collect_openmetrics': False,
                    'collect_genresources': True,
                    'genresources_endpoint': genresources_endpoint,
                    'genresources_auth_token': genresources_token,
                    'genresources_stream_applications_enabled': True,
                    'tls_verify': False,
                    'min_collection_interval': 15,
                },
            )

            yield instance
