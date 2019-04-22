# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import os

import pytest
from mock import patch

from .common import (
    HERE,
    MR_JOB_COUNTERS_URL,
    MR_JOBS_URL,
    MR_TASKS_URL,
    TEST_PASSWORD,
    TEST_USERNAME,
    YARN_APPS_URL_BASE,
)


@pytest.fixture
def mocked_request():
    with patch("requests.get", new=requests_get_mock):
        yield


@pytest.fixture
def mocked_auth_request():
    with patch("requests.get", new=requests_auth_mock):
        yield


def requests_get_mock(*args, **kwargs):
    class MockResponse:
        def __init__(self, json_data, status_code):
            self.json_data = json_data
            self.status_code = status_code

        def json(self):
            return json.loads(self.json_data)

        def raise_for_status(self):
            return True

    url = args[0]

    # The parameter that creates the query params (kwargs) is an unordered dict,
    #   so the query params can be in any order
    if url.startswith(YARN_APPS_URL_BASE):
        query = url[len(YARN_APPS_URL_BASE) :]
        if query in ["?states=RUNNING&applicationTypes=MAPREDUCE", "?applicationTypes=MAPREDUCE&states=RUNNING"]:
            apps_metrics_file = os.path.join(HERE, "fixtures", "apps_metrics")
            with open(apps_metrics_file, "r") as f:
                body = f.read()
                return MockResponse(body, 200)
        else:
            raise Exception(
                "Apps URL must have the two query parameters: states=RUNNING and applicationTypes=MAPREDUCE"
            )

    elif url == MR_JOBS_URL:
        job_metrics_file = os.path.join(HERE, "fixtures", "job_metrics")
        with open(job_metrics_file, "r") as f:
            body = f.read()
            return MockResponse(body, 200)

    elif url == MR_JOB_COUNTERS_URL:
        job_counter_metrics_file = os.path.join(HERE, "fixtures", "job_counter_metrics")
        with open(job_counter_metrics_file, "r") as f:
            body = f.read()
            return MockResponse(body, 200)

    elif url == MR_TASKS_URL:
        task_metrics_file = os.path.join(HERE, "fixtures", "task_metrics")
        with open(task_metrics_file, "r") as f:
            body = f.read()
            return MockResponse(body, 200)


def requests_auth_mock(*args, **kwargs):
    # Make sure we're passing in authentication
    assert 'auth' in kwargs, "Error, missing authentication"

    # Make sure we've got the correct username and password
    assert kwargs['auth'] == (TEST_USERNAME, TEST_PASSWORD), "Incorrect username or password"

    # Return mocked request.get(...)
    return requests_get_mock(*args, **kwargs)
