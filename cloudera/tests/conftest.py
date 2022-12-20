# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import os

import pytest
from cm_client.models.api_time_series import ApiTimeSeries
from cm_client.models.api_time_series_data import ApiTimeSeriesData
from cm_client.models.api_time_series_metadata import ApiTimeSeriesMetadata
from cm_client.models.api_time_series_response import ApiTimeSeriesResponse
from cm_client.models.api_time_series_response_list import ApiTimeSeriesResponseList

from datadog_checks.cloudera import ClouderaCheck
from datadog_checks.cloudera.metrics import TIMESERIES_METRICS
from datadog_checks.dev import docker_run
from datadog_checks.dev.conditions import CheckDockerLogs

from . import common


@pytest.fixture(scope='session')
def dd_environment():
    compose_file = common.COMPOSE_FILE
    conditions = [
        CheckDockerLogs(identifier='cloudera', patterns=['server running']),
    ]
    with docker_run(compose_file, conditions=conditions):
        yield common.INSTANCE


@pytest.fixture
def instance():
    return common.INSTANCE


@pytest.fixture(scope='session')
def cloudera_check():
    return lambda instance: ClouderaCheck('cloudera', {}, [instance])


@pytest.fixture
def api_response():
    def _response(filename):
        with open(os.path.join(common.HERE, "api_responses", f'{filename}.json'), 'r') as f:
            return json.load(f)

    return _response


def get_timeseries_resource():
    return [
        ApiTimeSeriesResponseList(
            items=[
                ApiTimeSeriesResponse(
                    time_series=[
                        ApiTimeSeries(
                            data=[
                                ApiTimeSeriesData(value=49.7),
                            ],
                            metadata=ApiTimeSeriesMetadata(attributes={'category': category}, alias=metric),
                        )
                        for metric in metrics
                    ]
                ),
            ],
        )
        for category, metrics in TIMESERIES_METRICS.items()
    ]
