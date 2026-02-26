# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Callable

import pytest

from datadog_checks.dev.conditions import CheckDockerLogs, CheckEndpoints
from datadog_checks.dev.docker import docker_run, get_docker_hostname
from datadog_checks.dev.utils import find_free_port
from datadog_checks.prefect import PrefectCheck

if TYPE_CHECKING:
    from datadog_checks.dev.http import MockResponse

COMPOSE_FILE_E2E = Path(__file__).parent / "docker" / "docker-compose.yml"
PREFECT_URL = "http://localhost:4200/api"
E2E_METADATA = {
    'env_vars': {'DD_LOGS_ENABLED': 'true'},
}


@pytest.fixture(scope='session')
def dd_environment():
    port = find_free_port(get_docker_hostname())
    prefect_url = f"http://{get_docker_hostname()}:{port}/api"

    conditions = [
        CheckEndpoints(f"{prefect_url}/ready", attempts=120, wait=2),
        CheckEndpoints(f"{prefect_url}/health", attempts=120, wait=2),
        CheckDockerLogs(
            COMPOSE_FILE_E2E, patterns=["Finished in state Completed()"], service="prefect-worker", attempts=120, wait=1
        ),
        CheckDockerLogs(
            COMPOSE_FILE_E2E, patterns=["Finished all tasks"], service="prefect-worker", attempts=120, wait=1
        ),
        CheckDockerLogs(COMPOSE_FILE_E2E, patterns=["Retried"], service="prefect-worker", attempts=120, wait=1),
    ]

    with docker_run(
        compose_file=str(COMPOSE_FILE_E2E),
        conditions=conditions,
        env_vars={"PREFECT_PORT": str(port)},
        waith_for_health=True,
        mount_logs=True,
    ):
        yield (
            {
                "instances": [{"prefect_url": prefect_url, "min_collection_interval": 300}],
            },
            E2E_METADATA,
        )


@pytest.fixture
def check(instance: Callable[[str], dict[str, str]]) -> PrefectCheck:
    check = PrefectCheck(
        "prefect",
        {},
        [instance(PREFECT_URL)],
    )

    return check


@pytest.fixture
def instance() -> Callable[[str], dict[str, str | dict[str, list[str]] | None]]:
    def builder(
        prefect_url: str,
        work_pool_names: dict[str, list[str]] | None = None,
        work_queue_names: dict[str, list[str]] | None = None,
        deployment_names: dict[str, list[str]] | None = None,
        event_names: dict[str, list[str]] | None = None,
    ) -> dict[str, str | dict[str, list[str]] | None]:
        return {
            "prefect_url": prefect_url,
            "work_pool_names": work_pool_names,
            "work_queue_names": work_queue_names,
            "deployment_names": deployment_names,
            "event_names": event_names,
        }

    return builder


def apply_mock_from_file(filename: str) -> dict[str, MockResponse]:
    import json

    from datadog_checks.dev.http import MockResponse

    mocked_responses_path = Path(__file__).parent / "fixtures" / filename
    with open(mocked_responses_path) as f:
        mocks = json.load(f)

    processed_metrics: dict[str, MockResponse] = {}
    for endpoint, metrics in mocks.items():
        processed_metrics[f"{PREFECT_URL}{endpoint}"] = [MockResponse(json_data=metrics, status_code=200)]

    return processed_metrics


@pytest.fixture()
def mock_http_responses(mock_http_response_per_endpoint: Callable) -> None:
    mock_http_response_per_endpoint(apply_mock_from_file("get_metrics.json"))
    mock_http_response_per_endpoint(apply_mock_from_file("post_metrics.json"), method="requests.Session.post")
