# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import os
import os.path
import tempfile

import pytest

from datadog_checks.dev import run_command
from datadog_checks.dev._env import get_state, save_state
from datadog_checks.dev.http import MockResponse
from datadog_checks.dev.kind import kind_run
from datadog_checks.strimzi import StrimziCheck

from .common import HERE, KUBERNETES_VERSION, STRIMZI_VERSION

NAMESPACE = "kafka"
CLUSTER_OPERATOR_DEPLOYMENT = "strimzi-cluster-operator"
ENTITY_OPERATOR_DEPLOYMENT = "my-cluster-entity-operator"

CLUSTER_OPERATOR_POD_IP_STATE = "strimzi_cluster_operator_pod_ip"
ENTITY_OPERATOR_POD_IP_STATE = "strimzi_entity_operator_pod_ip"


def setup_strimzi():
    run_command(["kubectl", "create", "namespace", NAMESPACE], check=True)
    run_command(
        [
            "kubectl",
            "create",
            "-f",
            os.path.join(HERE, "kind", STRIMZI_VERSION, "strimzi_install.yaml"),
            "-n",
            NAMESPACE,
        ],
        check=True,
    )
    run_command(
        [
            "kubectl",
            "apply",
            "-f",
            os.path.join(HERE, "kind", STRIMZI_VERSION, "kafka.yaml"),
            "-n",
            NAMESPACE,
        ],
        check=True,
    )
    run_command(
        [
            "kubectl",
            "wait",
            "kafka/my-cluster",
            "--for=condition=Ready",
            "--timeout=600s",
            "-n",
            NAMESPACE,
        ],
        check=True,
    )

    for file in ("topic.yaml", "user.yaml", "connect.yaml", "connectors.yaml"):
        run_command(
            [
                "kubectl",
                "apply",
                "-f",
                os.path.join(HERE, "kind", STRIMZI_VERSION, file),
                "-n",
                NAMESPACE,
            ],
            check=True,
        )

    save_state(
        CLUSTER_OPERATOR_POD_IP_STATE,
        get_deployment_pod_ip(CLUSTER_OPERATOR_DEPLOYMENT),
    )
    save_state(ENTITY_OPERATOR_POD_IP_STATE, get_deployment_pod_ip(ENTITY_OPERATOR_DEPLOYMENT))


def get_deployment_pod_ip(deployment: str) -> str:
    # Look up the deployment's pod selector, then use it to find the pod.
    result = run_command(
        [
            "kubectl",
            "get",
            "deployment",
            deployment,
            "--namespace",
            NAMESPACE,
            "--output",
            "json",
        ],
        capture="out",
        check=True,
    )
    selector = json.loads(result.stdout)["spec"]["selector"]["matchLabels"]
    selector_str = ",".join(f"{k}={v}" for k, v in selector.items())

    result = run_command(
        [
            "kubectl",
            "get",
            "pods",
            "--namespace",
            NAMESPACE,
            "--selector",
            selector_str,
            "--output",
            "json",
        ],
        capture="out",
        check=True,
    )
    pods = json.loads(result.stdout)["items"]
    if len(pods) != 1 or not pods[0].get("status", {}).get("podIP"):
        pod_names = [pod["metadata"]["name"] for pod in pods]
        raise RuntimeError(f"Expected exactly one {deployment} pod, found {len(pods)}: {pod_names}")
    return pods[0]["status"]["podIP"]


def render_kind_config(kubernetes_version):
    template_config_path = os.path.join(HERE, "kind", "kind-config.yaml")
    with open(template_config_path, "r") as f:
        kind_config_content = f.read().replace("%%KUBERNETES_VERSION%%", kubernetes_version)
    return kind_config_content


@pytest.fixture(scope="session")
def dd_environment():
    if not KUBERNETES_VERSION:
        pytest.fail("KUBERNETES_VERSION is not set")
    if not STRIMZI_VERSION:
        pytest.fail("STRIMZI_VERSION is not set")

    kind_config_content = render_kind_config(KUBERNETES_VERSION)
    with tempfile.NamedTemporaryFile("w", suffix=".yaml") as kind_config:
        kind_config.write(kind_config_content)
        kind_config.flush()

        with kind_run(conditions=[setup_strimzi], kind_config=kind_config.name) as kubeconfig:
            cluster_operator_ip = get_state(CLUSTER_OPERATOR_POD_IP_STATE)
            entity_operator_ip = get_state(ENTITY_OPERATOR_POD_IP_STATE)

            instance = {
                "cluster_operator_endpoint": f"http://{cluster_operator_ip}:8080/metrics",
                "topic_operator_endpoint": f"http://{entity_operator_ip}:8080/metrics",
                "user_operator_endpoint": f"http://{entity_operator_ip}:8081/metrics",
            }

            metadata = {
                "agent_type": "kubernetes",
                "kubernetes": {"kubeconfig": kubeconfig},
            }

            yield instance, metadata


@pytest.fixture()
def check():
    return lambda instance: StrimziCheck("strimzi", {}, [instance])


def mock_http_responses(url, **_params):
    mapping = {
        "http://cluster-operator:8080/metrics": "cluster_operator_metrics.txt",
        "http://entity-operator:8080/metrics": "topic_operator_metrics.txt",
        "http://entity-operator:8081/metrics": "user_operator_metrics.txt",
    }

    metrics_file = mapping.get(url)

    if not metrics_file:
        pytest.fail(f"url `{url}` not registered")

    with open(os.path.join(HERE, "fixtures", STRIMZI_VERSION, metrics_file)) as f:
        return MockResponse(content=f.read())
