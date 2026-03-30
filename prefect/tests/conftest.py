# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from pathlib import Path
from typing import Callable

import pytest

from datadog_checks.dev.conditions import CheckDockerLogs, CheckEndpoints
from datadog_checks.dev.docker import docker_run, get_docker_hostname
from datadog_checks.dev.utils import find_free_port
from datadog_checks.prefect import PrefectCheck

COMPOSE_FILE_E2E = Path(__file__).parent / "docker" / "docker-compose.yml"
PREFECT_URL = "http://localhost:4200/api"
E2E_METADATA = {
    'env_vars': {'DD_LOGS_ENABLED': 'true'},
}


@pytest.fixture(scope='session')
def dd_environment(instance: Callable[[str], dict[str, str | dict[str, list[str]] | None | bool | int]]):
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
            {"instances": [instance(prefect_url)]},
            E2E_METADATA,
        )


@pytest.fixture
def check(instance: Callable[..., dict[str, str | dict[str, list[str]] | None | bool | int]]) -> PrefectCheck:
    check = PrefectCheck(
        "prefect",
        {},
        [
            instance(
                PREFECT_URL,
                work_pool_names={"exclude": ["^not_included_"]},
                work_queue_names={"exclude": ["^not_included_"]},
                deployment_names={"exclude": ["^not_included_"]},
                event_names={
                    "include": [
                        r"^prefect\.task-run\..*$",
                        r"^prefect\.flow-run\..*$",
                        r"^prefect\.[a-z-]+\.(ready|not-ready)$",
                    ]
                },
            )
        ],
    )

    return check


@pytest.fixture(scope='session')
def instance() -> Callable[[str], dict[str, str | dict[str, list[str]] | None | bool | int]]:
    def builder(
        prefect_url: str,
        work_pool_names: dict[str, list[str]] | None = None,
        work_queue_names: dict[str, list[str]] | None = None,
        deployment_names: dict[str, list[str]] | None = None,
        event_names: dict[str, list[str]] | None = None,
        collect_events: bool = True,
        min_collection_interval: int = 600,
    ) -> dict[str, str | dict[str, list[str]] | None | bool | int]:
        return {
            "prefect_url": prefect_url,
            "work_pool_names": work_pool_names,
            "work_queue_names": work_queue_names,
            "deployment_names": deployment_names,
            "event_names": event_names,
            "collect_events": collect_events,
            "min_collection_interval": min_collection_interval,
        }

    return builder


def _load_fixture(filename: str) -> dict:
    import json

    fixtures_path = Path(__file__).parent / "fixtures" / filename
    with open(fixtures_path) as f:
        return json.load(f)


@pytest.fixture
def mock_prefect_client(mocker):
    from json import JSONDecodeError
    from unittest.mock import create_autospec

    from requests.exceptions import ConnectionError, HTTPError, InvalidURL, Timeout

    from datadog_checks.prefect.check import PrefectClient

    get_responses = _load_fixture("get_metrics.json")
    post_responses = _load_fixture("post_metrics.json")

    mock_client = create_autospec(PrefectClient, instance=True)
    mock_client.http_exceptions = (HTTPError, InvalidURL, ConnectionError, Timeout, JSONDecodeError)

    mock_client.get.side_effect = lambda endpoint, **kwargs: get_responses[endpoint]
    mock_client.paginate_filter.side_effect = lambda endpoint, payload=None: post_responses[endpoint]
    mock_client.paginate_events.side_effect = lambda endpoint, payload=None: post_responses[endpoint].get("events", [])

    mocker.patch("datadog_checks.prefect.check.PrefectClient", return_value=mock_client)
    return mock_client
