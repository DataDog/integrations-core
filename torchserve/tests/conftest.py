# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy
import json
import os
from contextlib import contextmanager

import pytest

from datadog_checks.dev import EnvVars, TempDir, docker_run, get_here
from datadog_checks.dev._env import get_state, save_state
from datadog_checks.dev.conditions import CheckEndpoints, WaitFor
from datadog_checks.torchserve import TorchserveCheck

from .common import (
    E2E_METADATA,
    HERE,
    INFERENCE_API_URL,
    INFERENCE_INSTANCE,
    MANAGEMENT_API_URL,
    MANAGEMENT_INSTANCE,
    MOCKED_INFERENCE_INSTANCE,
    MOCKED_MANAGEMENT_INSTANCE,
    MOCKED_OPENMETRICS_INSTANCE,
    OPENMETRICS_ENDPOINT,
    OPENMETRICS_INSTANCE,
)
from .torchserve_api import register_model, run_prediction, set_model_default_version, update_workers


@pytest.fixture(scope='session')
def dd_environment():
    conditions = [
        CheckEndpoints(f"{INFERENCE_API_URL}/ping"),
        CheckEndpoints(f"{MANAGEMENT_API_URL}/models"),
        CheckEndpoints(OPENMETRICS_ENDPOINT),
        WaitFor(register_model, args=("linear_regression_1_1.mar",)),
        WaitFor(update_workers, args=("linear_regression_1_1", 2, 4)),
        WaitFor(run_prediction, args=("linear_regression_1_1",)),
        WaitFor(run_prediction, args=("linear_regression_1_2",)),
        WaitFor(run_prediction, args=("linear_regression_2_2",)),
        WaitFor(run_prediction, args=("linear_regression_2_3",)),
        WaitFor(run_prediction, args=("linear_regression_3_2",)),
        WaitFor(set_model_default_version, args=("linear_regression_1_2", "3")),
    ]

    with docker_run(
        compose_file=os.path.join(
            get_here(),
            "docker",
            "docker-compose.yaml",
        ),
        conditions=conditions,
        sleep=10,
        wrappers=[create_log_volumes()],
    ):
        for _ in range(10):
            for model in (
                "linear_regression_1_1",
                "linear_regression_1_2",
                "linear_regression_2_2",
                "linear_regression_2_3",
                "linear_regression_3_2",
            ):
                run_prediction(model)

        yield (
            {
                "init_config": {
                    "service": "my_torchserve",
                },
                "instances": [
                    OPENMETRICS_INSTANCE,
                    INFERENCE_INSTANCE,
                    MANAGEMENT_INSTANCE,
                ],
            },
            E2E_METADATA,
        )


@pytest.fixture
def openmetrics_instance():
    return copy.deepcopy(OPENMETRICS_INSTANCE)


@pytest.fixture
def inference_instance():
    return copy.deepcopy(INFERENCE_INSTANCE)


@pytest.fixture
def management_instance():
    return copy.deepcopy(MANAGEMENT_INSTANCE)


@pytest.fixture
def mocked_openmetrics_instance():
    return copy.deepcopy(MOCKED_OPENMETRICS_INSTANCE)


@pytest.fixture
def mocked_inference_instance():
    return copy.deepcopy(MOCKED_INFERENCE_INSTANCE)


@pytest.fixture
def mocked_management_instance():
    return copy.deepcopy(MOCKED_MANAGEMENT_INSTANCE)


@pytest.fixture
def check():
    return lambda instance: TorchserveCheck('torchserve', {}, [instance])


@pytest.fixture
def http_responses(fake_http, fake_http_response):
    expected = []

    def register(
        instance: dict,
        all_models_file: str = 'management/models.json',
        expected_models: list[str] | None = None,
        failed_models: tuple[str, ...] = (),
    ) -> None:
        def response(endpoint: str, filename: str, **options) -> dict | list | None:
            with open(os.path.join(HERE, 'fixtures', filename), 'rb') as f:
                content = f.read()
            result = json.loads(content) if filename.endswith('.json') else None
            fake_http_response(endpoint, content, json_result=result, **options)
            expected.append(('GET', endpoint))
            return result

        if 'inference_api_url' in instance:
            response(instance['inference_api_url'] + '/ping', 'inference/healthy.json')
        elif 'openmetrics_endpoint' in instance:
            response(instance['openmetrics_endpoint'], 'openmetrics/metrics.txt')
        else:
            base = instance['management_api_url']
            models = response(base + '/models', all_models_file, match_options={'params': {'limit': 100}})
            for model in models.get('models', []):
                name = model['modelName']
                if expected_models is not None and name not in expected_models:
                    continue
                response(
                    f'{base}/models/{name}/all',
                    f'management/models/{name}.json',
                    status_code=500 if name in failed_models else 200,
                )

    yield register
    fake_http.assert_all_responses_consumed()
    assert [(r.method, r.url) for r in fake_http.requests] == expected


@contextmanager
def create_log_volumes():
    # By default, for the container the logs are in ~/logs
    # I can't easily create the /var/log/torchserve folder because we are not root
    # So I create a volume and I mount it so the folder is created

    env_vars = {}
    docker_volumes = get_state("docker_volumes", [])

    with TempDir("torchserve") as d:
        os.chmod(d, 0o777)
        docker_volumes.append(f"{d}:/var/log/torchserve")
        env_vars["TORCHSERVE_LOG_FOLDER"] = d

        config = [
            {
                "type": "file",
                "path": f"/var/log/torchserve/{file}",
                "source": "torchserve",
                "service": "torchserve",
            }
            for file in ["model_log.log", "ts_log.log", "access_log.log"]
        ]

        save_state("logs_config", config)
        save_state("docker_volumes", docker_volumes)

        with EnvVars(env_vars):
            yield
