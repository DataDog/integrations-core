# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy
import os
from time import sleep

import mock
import pytest
import requests
from six import PY2

from datadog_checks.dev import docker_run
from datadog_checks.dev.conditions import CheckEndpoints
from datadog_checks.gitlab import GitlabCheck

from .common import (
    ALLOWED_METRICS,
    CUSTOM_TAGS,
    GITLAB_LOCAL_PORT,
    GITLAB_LOCAL_PROMETHEUS_PORT,
    GITLAB_PROMETHEUS_ENDPOINT,
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
            'prometheus_endpoint': GITLAB_PROMETHEUS_ENDPOINT,
            'gitlab_url': GITLAB_URL,
            'send_distribution_counts_as_monotonic': True,
            'send_monotonic_counter': True,
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
    }

    with docker_run(
        compose_file=os.path.join(HERE, 'compose', 'docker-compose.yml'),
        env_vars=env,
        conditions=[
            CheckEndpoints(GITLAB_URL, attempts=100, wait=6),
            CheckEndpoints(GITLAB_PROMETHEUS_ENDPOINT, attempts=100, wait=6),
        ],
    ):
        # run pre-test commands
        for _ in range(100):
            requests.get(GITLAB_URL)
        sleep(2)

        yield CONFIG


@pytest.fixture()
def mock_data():
    f_name = os.path.join(os.path.dirname(__file__), 'fixtures', 'metrics.txt')
    with open(f_name, 'r') as f:
        text_data = f.read()
    with mock.patch(
        'requests.get',
        return_value=mock.MagicMock(
            status_code=200, iter_lines=lambda **kwargs: text_data.split("\n"), headers={'Content-Type': "text/plain"}
        ),
    ):
        yield


@pytest.fixture()
def gitlab_check():
    def create_check(config, check_id="test:123"):
        check = GitlabCheck('gitlab', config["init_config"], config["instances"])
        check.check_id = check_id
        return check

    return create_check


@pytest.fixture()
def config():
    return copy.deepcopy(CONFIG)


@pytest.fixture()
def legacy_config():
    return {
        'init_config': {'allowed_metrics': ALLOWED_METRICS},
        'instances': [
            {
                'prometheus_endpoint': PROMETHEUS_ENDPOINT,
                'gitlab_url': GITLAB_URL,
                'disable_ssl_validation': True,
                'tags': CUSTOM_TAGS,
            }
        ],
    }


@pytest.fixture()
def bad_config():
    return {
        'init_config': {'allowed_metrics': ALLOWED_METRICS},
        'instances': [
            {
                'prometheus_endpoint': 'http://{}:1234/-/metrics'.format(HOST),
                'gitlab_url': 'http://{}:1234/ci'.format(HOST),
                'disable_ssl_validation': True,
                'tags': CUSTOM_TAGS,
            }
        ],
    }


@pytest.fixture()
def auth_config():
    return {
        'init_config': {'allowed_metrics': ALLOWED_METRICS},
        'instances': [
            {
                'prometheus_endpoint': PROMETHEUS_ENDPOINT,
                'gitlab_url': GITLAB_URL,
                'disable_ssl_validation': True,
                'api_token': GITLAB_TEST_API_TOKEN,
            }
        ],
    }

@pytest.fixture
def use_openmetrics(request):
    if request.param and PY2:
        pytest.skip('This version of the integration is only available when using Python 3.')

    return request.param
