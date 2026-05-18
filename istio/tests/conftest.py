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

ZTUNNEL_METRICS_SERVICE = "ztunnel-metrics"
ZTUNNEL_METRICS_PORT = 15020
WAYPOINT_METRICS_PORT = 15090
ISTIOD_METRICS_PORT = 15014


@pytest.fixture
def instance_openmetrics_v2(dd_get_state):
    openmetrics_v2 = deepcopy(dd_get_state('istio_instance', default={}))
    openmetrics_v2['use_openmetrics'] = 'true'
    return openmetrics_v2


def _istio_release_suffix():
    system = platform.system()
    machine = platform.machine().lower()
    if system == "Darwin":
        return "osx-arm64" if machine in ("arm64", "aarch64") else "osx-amd64"
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
    istio = _download_istio()
    istioctl = opj(istio, "bin", "istioctl")
    run_command([istioctl, "install", "--set", "profile=demo", "--skip-confirmation"])
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
    # Expose ztunnel's stats endpoint via a Service so the port-forward target name is stable
    # (the underlying DaemonSet's pod name has a random suffix that would break port-forward
    # teardown name lookup in CI). kubectl expose does not support DaemonSets, so apply a
    # Service manifest directly.
    run_command(["kubectl", "apply", "-f", opj(HERE, 'kind', "ztunnel_service.yaml")])
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
    _wait_for_ztunnel_traffic()
    os.remove("istio.tar.gz")


def _wait_for_ztunnel_traffic(timeout_seconds=300, interval_seconds=3):
    """Block until ztunnel reports at least one TCP connection on its /stats/prometheus endpoint.

    The traffic-generator pod takes a variable amount of time to pull its image, get scheduled,
    and start hitting the productpage service. A fixed sleep can either be too short on a slow
    CI agent (test fails with a misleading "metric not found") or too long on a fast one.
    Poll the actual readiness signal instead, bounded by the same 300s timeout used elsewhere
    in this setup. Ztunnel itself runs a minimal Rust binary with no shell or curl, so the
    poll is issued from the traffic-gen pod (curlimages/curl) against the ztunnel-metrics
    Service applied earlier in setup."""
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        result = run_command(
            [
                "kubectl",
                "exec",
                "-n",
                "default",
                "traffic-gen",
                "--",
                "curl",
                "-sm",
                "5",
                "ztunnel-metrics.istio-system.svc:15020/stats/prometheus",
            ],
            capture=True,
        )
        if result.code == 0 and _ztunnel_has_traffic(result.stdout):
            return
        time.sleep(interval_seconds)
    raise RuntimeError("ztunnel did not record TCP traffic within {}s".format(timeout_seconds))


def _ztunnel_has_traffic(metrics_text):
    """Return True if `istio_tcp_connections_opened_total` reports any non-zero sample."""
    for line in metrics_text.splitlines():
        if not line.startswith("istio_tcp_connections_opened_total"):
            continue
        value = line.rsplit(" ", 1)[-1]
        try:
            if float(value) > 0:
                return True
        except ValueError:
            continue
    return False


@pytest.fixture(scope='session')
def dd_environment(dd_save_state):
    setup = setup_istio_ambient if MODE == "ambient" else setup_istio
    with kind_run(conditions=[setup]) as kubeconfig:
        with ExitStack() as stack:
            if MODE == "ambient":
                ztunnel_host, ztunnel_port = stack.enter_context(
                    port_forward(kubeconfig, 'istio-system', ZTUNNEL_METRICS_PORT, 'service', ZTUNNEL_METRICS_SERVICE)
                )
                waypoint_host, waypoint_port = stack.enter_context(
                    port_forward(kubeconfig, 'default', WAYPOINT_METRICS_PORT, 'deployment', 'waypoint')
                )
                istiod_host, istiod_port = stack.enter_context(
                    port_forward(kubeconfig, 'istio-system', ISTIOD_METRICS_PORT, 'deployment', 'istiod')
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
            else:
                istiod_host, istiod_port = stack.enter_context(
                    port_forward(kubeconfig, 'istio-system', ISTIOD_METRICS_PORT, 'deployment', 'istiod')
                )
                istiod_endpoint = 'http://{}:{}/metrics'.format(istiod_host, istiod_port)
                instance = {'istiod_endpoint': istiod_endpoint, 'use_openmetrics': 'false'}
                dd_save_state("istio_instance", instance)
                yield instance
