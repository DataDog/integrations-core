# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy
import json
import os
from contextlib import contextmanager
from time import sleep

import mock
import pytest
import requests
from six import PY2

from datadog_checks.dev import EnvVars, TempDir, docker_run
from datadog_checks.dev._env import get_state, save_state
from datadog_checks.dev.conditions import CheckEndpoints
from datadog_checks.gitlab import GitlabCheck

from .common import (
    ALLOWED_METRICS,
    CUSTOM_TAGS,
    GITLAB_GITALY_PROMETHEUS_ENDPOINT,
    GITLAB_HEALTH_ENDPOINT,
    GITLAB_LIVENESS_ENDPOINT,
    GITLAB_LOCAL_GITALY_PROMETHEUS_PORT,
    GITLAB_LOCAL_PORT,
    GITLAB_LOCAL_PROMETHEUS_PORT,
    GITLAB_PROMETHEUS_ENDPOINT,
    GITLAB_READINESS_ENDPOINT,
    GITLAB_TEST_API_TOKEN,
    GITLAB_TEST_PASSWORD,
    GITLAB_URL,
    HERE,
    HOST,
    PROMETHEUS_ENDPOINT,
)

CONFIG = {
    'init_config': {},
    'instances': [
        {
            'prometheus_url': GITLAB_PROMETHEUS_ENDPOINT,
            'gitlab_url': GITLAB_URL,
            'disable_ssl_validation': True,
            'tags': CUSTOM_TAGS,
        }
    ],
}


@pytest.fixture(scope="session")
def dd_environment():
    """
    Spin up and initialize gitlab
    """

    env = {
        'GITLAB_TEST_PASSWORD': GITLAB_TEST_PASSWORD,
        'GITLAB_LOCAL_PORT': str(GITLAB_LOCAL_PORT),
        'GITLAB_LOCAL_PROMETHEUS_PORT': str(GITLAB_LOCAL_PROMETHEUS_PORT),
        'GITLAB_LOCAL_GITALY_PROMETHEUS_PORT': str(GITLAB_LOCAL_GITALY_PROMETHEUS_PORT),
    }

    conditions = []

    for _ in range(2):
        conditions.extend(
            [
                CheckEndpoints(GITLAB_URL, attempts=100, wait=6),
                CheckEndpoints(GITLAB_PROMETHEUS_ENDPOINT, attempts=100, wait=6),
                CheckEndpoints(PROMETHEUS_ENDPOINT, attempts=100, wait=6),
                CheckEndpoints(GITLAB_GITALY_PROMETHEUS_ENDPOINT, attempts=100, wait=10),
                CheckEndpoints(GITLAB_READINESS_ENDPOINT, attempts=100, wait=10),
                CheckEndpoints(GITLAB_LIVENESS_ENDPOINT, attempts=100, wait=10),
                CheckEndpoints(GITLAB_HEALTH_ENDPOINT, attempts=100, wait=10),
            ]
        )

    with docker_run(
        compose_file=os.path.join(HERE, 'compose', 'docker-compose.yml'),
        env_vars=env,
        conditions=conditions,
        wrappers=[create_log_volumes()],
    ):
        # run pre-test commands
        for _ in range(100):
            requests.get(GITLAB_URL)
        sleep(2)

        yield {
            'init_config': {},
            'instances': [
                {
                    'openmetrics_endpoint': GITLAB_PROMETHEUS_ENDPOINT,
                    'gitaly_server_endpoint': GITLAB_GITALY_PROMETHEUS_ENDPOINT,
                    'gitlab_url': GITLAB_URL,
                    'disable_ssl_validation': True,
                    'tags': CUSTOM_TAGS,
                }
            ],
        }


@pytest.fixture()
def mock_data():
    with mock.patch(
        'requests.get',
        side_effect=mocked_requests_get,
    ):
        yield


def mocked_requests_get(*args, **kwargs):
    url = args[0]

    if url.startswith("http://{}:{}/-/readiness".format(HOST, GITLAB_LOCAL_PORT)):
        f_name = os.path.join(os.path.dirname(__file__), 'fixtures', 'readiness_check.json')
        with open(f_name, 'r') as f:
            text_data = f.read()
            response = mock.MagicMock()
            response.status_code = 200
            response.json.return_value = json.loads(text_data)
            return response

    elif url == "http://{}:{}/-/liveness".format(HOST, GITLAB_LOCAL_PORT) or url == "http://{}:{}/-/health".format(
        HOST, GITLAB_LOCAL_PORT
    ):
        response = mock.MagicMock()
        response.status_code = 200
        return response
    elif url == "http://{}:{}/-/metrics".format(HOST, GITLAB_LOCAL_PORT):
        f_name = os.path.join(os.path.dirname(__file__), 'fixtures', 'metrics.txt')

        with open(f_name, 'r') as f:
            text_data = f.read()
            return mock.MagicMock(
                status_code=200,
                iter_lines=lambda **kwargs: text_data.split("\n"),
                headers={'Content-Type': "text/plain"},
            )
    elif url == "http://{}:{}/metrics".format(HOST, GITLAB_LOCAL_GITALY_PROMETHEUS_PORT):
        f_name = os.path.join(os.path.dirname(__file__), 'fixtures', 'gitaly.txt')

        with open(f_name, 'r') as f:
            text_data = f.read()
            return mock.MagicMock(
                status_code=200,
                iter_lines=lambda **kwargs: text_data.split("\n"),
                headers={'Content-Type': "text/plain"},
            )
    elif url == "http://{}:{}/api/v4/version".format(HOST, GITLAB_LOCAL_PORT) or url == "http://{}:{}/-/health".format(
        HOST, GITLAB_LOCAL_PORT
    ):
        f_name = os.path.join(os.path.dirname(__file__), 'fixtures', 'version.json')
        with open(f_name, 'r') as f:
            text_data = f.read()
            response = mock.MagicMock()
            response.status_code = 200
            response.json.return_value = text_data
            return response

    pytest.fail("url `{}` not registered".format(args[0]))


@pytest.fixture()
def gitlab_check():
    def create_check(config, check_id="test:123"):
        check = GitlabCheck('gitlab', config["init_config"], config["instances"])
        check.check_id = check_id
        return check

    return create_check


@pytest.fixture()
def get_config():
    def _config(use_openmetrics=False):
        config = copy.deepcopy(CONFIG)

        if use_openmetrics:
            return to_omv2_config(config)

        return config

    return _config


@pytest.fixture()
def legacy_config():
    return {
        'init_config': {'allowed_metrics': ALLOWED_METRICS},
        'instances': [
            {
                'prometheus_url': PROMETHEUS_ENDPOINT,
                'gitlab_url': GITLAB_URL,
                'disable_ssl_validation': True,
                'tags': CUSTOM_TAGS,
            }
        ],
    }


@pytest.fixture()
def get_bad_config():
    def _config(use_openmetrics=False):
        config = {
            'init_config': {'allowed_metrics': ALLOWED_METRICS},
            'instances': [
                {
                    'prometheus_url': 'http://{}:1234/-/metrics'.format(HOST),
                    'gitlab_url': 'http://{}:1234/ci'.format(HOST),
                    'disable_ssl_validation': True,
                    'tags': CUSTOM_TAGS,
                }
            ],
        }

        if use_openmetrics:
            return to_omv2_config(config)

        return config

    return _config


@pytest.fixture()
def get_auth_config():
    def _config(use_openmetrics=False):
        config = {
            'init_config': {'allowed_metrics': ALLOWED_METRICS},
            'instances': [
                {
                    'prometheus_url': PROMETHEUS_ENDPOINT,
                    'gitlab_url': GITLAB_URL,
                    'disable_ssl_validation': True,
                    'api_token': GITLAB_TEST_API_TOKEN,
                }
            ],
        }

        if use_openmetrics:
            return to_omv2_config(config)

        return config

    return _config


def to_omv2_config(config):
    new_config = copy.deepcopy(config)
    instance = new_config['instances'][0]
    instance["openmetrics_endpoint"] = instance["prometheus_url"]
    return new_config


@pytest.fixture
def use_openmetrics(request):
    if request.param and PY2:
        pytest.skip('This version of the integration is only available when using Python 3.')

    return request.param


@contextmanager
def create_log_volumes():
    env_vars = {}
    docker_volumes = get_state('docker_volumes', [])

    with TempDir("gitlab-logs") as d:
        os.chmod(d, 0o777)
        docker_volumes.append('{}:/var/log/gitlab'.format(d))
        env_vars["LOGS_FOLDER"] = d

    save_state('logs_config', get_logs_config())
    save_state('docker_volumes', docker_volumes)

    with EnvVars(env_vars):
        yield


def get_logs_config():
    return [
        {
            'type': 'file',
            'path': '/var/log/gitlab/{}/{}'.format(service["name"], service["file"]),
            'source': 'gitlab',
            'service': service["name"],
        }
        for service in [
            {"name": "gitlab-rails", "file": "api_json.log"},
            {"name": "gitlab-rails", "file": "production.log"},
            {"name": "gitlab-rails", "file": "production_json.log"},
            {"name": "gitlab-rails", "file": "integrations_json.log"},
            {"name": "gitlab-rails", "file": "application.log"},
            {"name": "gitlab-rails", "file": "kubernetes.log"},
            {"name": "gitlab-rails", "file": "audit_json.log"},
            {"name": "gitlab-rails", "file": "sidekiq.log"},
            {"name": "gitlab-rails", "file": "gitlab-shell.log"},
            {"name": "gitlab-rails", "file": "graphql_json.log"},
            {"name": "gitlab-rails", "file": "auth.log"},
        ]
    ]
