# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import platform
import time
from contextlib import ExitStack
from copy import deepcopy

import pytest

from datadog_checks.dev import get_here
from datadog_checks.dev.kind import kind_run
from datadog_checks.dev.kube_port_forward import port_forward
from datadog_checks.dev.subprocess import run_command

HERE = get_here()
VERSION = os.environ.get("ISTIO_VERSION")
MODE = os.environ.get("ISTIO_MODE", "sidecar")
opj = os.path.join


@pytest.fixture
def instance_openmetrics_v2(dd_get_state):
    openmetrics_v2 = deepcopy(dd_get_state('istio_instance', default={}))
    openmetrics_v2['use_openmetrics'] = 'true'
    return openmetrics_v2


def _istio_release_suffix():
    system = platform.system()
    machine = platform.machine().lower()
    if system == "Darwin":
        return "osx-arm64" if machine in ("arm64", "aarch64") else "osx"
    if machine in ("aarch64", "arm64"):
        return "linux-arm64"
    return "linux-amd64"


def _download_istio():
    suffix = _istio_release_suffix()
    run_command(
        [
            "curl",
            "-o",
            "istio.tar.gz",
            "-L",
            "https://github.com/istio/istio/releases/download/{version}/istio-{version}-{suffix}.tar.gz".format(
                version=VERSION, suffix=suffix
            ),
        ]
    )
    run_command(["tar", "xf", "istio.tar.gz"])
    return "istio-{}".format(VERSION)


def setup_istio():
    _download_istio()
    istio = "istio-{}".format(VERSION)
    run_command(["kubectl", "create", "ns", "istio-system"])
    run_command(["kubectl", "apply", "-f", opj(HERE, 'kind', "demo_profile.yaml")])
    run_command(
        ["kubectl", "wait", "deployments", "--all", "--for=condition=Available", "-n", "istio-system", "--timeout=300s"]
    )
    run_command(["kubectl", "label", "namespace", "default", "istio-injection=enabled"])
    run_command(["kubectl", "apply", "-f", opj(istio, "samples", "bookinfo", "platform", "kube", "bookinfo.yaml")])
    run_command(["kubectl", "wait", "pods", "--all", "--for=condition=Ready", "--timeout=300s"])
    run_command(["kubectl", "apply", "-f", opj(istio, "samples", "bookinfo", "networking", "bookinfo-gateway.yaml")])
    run_command(["kubectl", "wait", "pods", "--all", "--for=condition=Ready", "--timeout=300s"])
    os.remove("istio.tar.gz")


def setup_istio_ambient():
    istio = _download_istio()
    istioctl = opj(istio, "bin", "istioctl")
    run_command([istioctl, "install", "--set", "profile=ambient", "--skip-confirmation"])
    run_command(
        ["kubectl", "wait", "deployments", "--all", "--for=condition=Available", "-n", "istio-system", "--timeout=300s"]
    )
    run_command(
        [
            "kubectl",
            "wait",
            "pods",
            "-l",
            "app=ztunnel",
            "--for=condition=Ready",
            "-n",
            "istio-system",
            "--timeout=300s",
        ]
    )
    run_command(["kubectl", "label", "namespace", "default", "istio.io/dataplane-mode=ambient", "--overwrite"])
    run_command(["kubectl", "apply", "-f", opj(istio, "samples", "bookinfo", "platform", "kube", "bookinfo.yaml")])
    run_command(["kubectl", "wait", "pods", "--all", "--for=condition=Ready", "-n", "default", "--timeout=300s"])
    run_command(
        [
            "kubectl",
            "apply",
            "-f",
            "https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.2.1/standard-install.yaml",
        ]
    )
    run_command([istioctl, "waypoint", "apply", "-n", "default", "--name", "waypoint", "--wait"])
    run_command(
        [
            "kubectl",
            "run",
            "traffic-gen",
            "--image=curlimages/curl",
            "--restart=Always",
            "--",
            "sh",
            "-c",
            "while true; do curl -s productpage:9080/productpage > /dev/null; sleep 1; done",
        ]
    )
    time.sleep(15)
    os.remove("istio.tar.gz")


def _get_first_ztunnel_pod(kubeconfig):
    env = os.environ.copy()
    env['KUBECONFIG'] = kubeconfig
    result = run_command(
        [
            "kubectl",
            "get",
            "pods",
            "-n",
            "istio-system",
            "-l",
            "app=ztunnel",
            "-o",
            "jsonpath={.items[0].metadata.name}",
        ],
        capture='stdout',
        env=env,
    )
    return result.stdout.strip()


@pytest.fixture(scope='session')
def dd_environment(dd_save_state):
    setup = setup_istio_ambient if MODE == "ambient" else setup_istio
    with kind_run(conditions=[setup]) as kubeconfig:
        with ExitStack() as stack:
            if MODE == "ambient":
                ztunnel_pod = _get_first_ztunnel_pod(kubeconfig)
                ztunnel_host, ztunnel_port = stack.enter_context(
                    port_forward(kubeconfig, 'istio-system', 15020, 'pod', ztunnel_pod)
                )
                waypoint_host, waypoint_port = stack.enter_context(
                    port_forward(kubeconfig, 'default', 15090, 'deployment', 'waypoint')
                )
                istiod_host, istiod_port = stack.enter_context(
                    port_forward(kubeconfig, 'istio-system', 15014, 'deployment', 'istiod')
                )
                instance = {
                    "istio_mode": "ambient",
                    "ztunnel_endpoint": "http://{}:{}/stats/prometheus".format(ztunnel_host, ztunnel_port),
                    "waypoint_endpoint": "http://{}:{}/stats/prometheus".format(waypoint_host, waypoint_port),
                    "istiod_endpoint": "http://{}:{}/metrics".format(istiod_host, istiod_port),
                    "use_openmetrics": "true",
                }
                dd_save_state("istio_instance", instance)
                yield instance
            elif VERSION == '1.13.3':
                istiod_host, istiod_port = stack.enter_context(
                    port_forward(kubeconfig, 'istio-system', 15014, 'deployment', 'istiod')
                )
                istiod_endpoint = 'http://{}:{}/metrics'.format(istiod_host, istiod_port)
                instance = {'istiod_endpoint': istiod_endpoint, 'use_openmetrics': 'false'}
                dd_save_state("istio_instance", instance)
                yield instance
