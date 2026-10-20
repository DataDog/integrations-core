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


def read_fixture(path):
    with open(os.path.join(HERE, 'fixtures', path), 'rb') as f:
        return f.read()


def register_management_responses(fake_http_response, models_file='management/models.json', models=None, failing=()):
    """Register the responses of one management check run: the models list, then the versions of each model.

    `models` restricts the per-model calls to the ones the check is expected to make, defaulting to every listed model.
    """
    models_list = json.loads(read_fixture(models_file))
    fake_http_response('http://torchserve:8081/models', json_data=models_list)
    if models is None:
        models = [model['modelName'] for model in models_list.get('models', [])]
    for model in models:
        url = f'http://torchserve:8081/models/{model}/all'
        if model in failing:
            fake_http_response(url, status_code=500)
        else:
            fake_http_response(url, json_data=json.loads(read_fixture(f'management/models/{model}.json')))


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
