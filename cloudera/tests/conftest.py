# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import os
from copy import deepcopy

import pytest
from cm_client.models.api_cluster_ref import ApiClusterRef
from cm_client.models.api_event import ApiEvent
from cm_client.models.api_event_attribute import ApiEventAttribute
from cm_client.models.api_event_query_result import ApiEventQueryResult
from cm_client.models.api_host import ApiHost
from cm_client.models.api_host_list import ApiHostList
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
        yield {
            'instances': [common.INSTANCE],
            'init_config': common.INIT_CONFIG,
        }


@pytest.fixture
def config():
    return {
        'instances': [common.INSTANCE],
        'init_config': common.INIT_CONFIG,
    }


@pytest.fixture
def instance():
    return common.INSTANCE


@pytest.fixture
def init_config():
    return common.INIT_CONFIG


@pytest.fixture(scope='session')
def cloudera_check():
    return lambda instance: deepcopy(ClouderaCheck('cloudera', init_config=common.INIT_CONFIG, instances=[instance]))


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


@pytest.fixture
def list_hosts_resource():
    return ApiHostList(
        items=[
            ApiHost(
                host_id='host_1',
                cluster_ref=ApiClusterRef(
                    cluster_name="cod--qfdcinkqrzw",
                    display_name="cod--qfdcinkqrzw",
                ),
                num_cores=8,
                num_physical_cores=4,
                total_phys_mem_bytes=33079799808,
            )
        ],
    )


@pytest.fixture
def read_events_resource():
    content = (
        'Interceptor for {http://yarn.extractor.cdx.cloudera.com/}YarnHistoryClient has thrown exception, unwinding now'
    )
    dummy_event = ApiEvent(
        time_occurred='2022-11-30T21:06:39.870Z',
        severity='IMPORTANT',
        content=content,
        category='LOG_EVENT',
        attributes=[
            ApiEventAttribute(name='ROLE', values=['TELEMETRYPUBLISHER']),
            ApiEventAttribute(name='CLUSTER', values=['cod--qfdcinkqrzw']),
            ApiEventAttribute(name='ROLE_DISPLAY_NAME', values=['Telemetry Publisher (cod--qfdcinkqrzw-gateway0)']),
        ],
    )
    return ApiEventQueryResult(items=[dummy_event])


@pytest.fixture
def get_custom_timeseries_resource():
    return ApiTimeSeriesResponseList(
        items=[
            ApiTimeSeriesResponse(
                time_series=[
                    ApiTimeSeries(
                        data=[
                            ApiTimeSeriesData(value=49.7, timestamp="2023-01-18T18:41:09.449Z"),
                        ],
                        metadata=ApiTimeSeriesMetadata(
                            attributes={'category': "cluster"},
                            alias="foo",
                            entity_name="foo",
                        ),
                    )
                ]
            )
        ],
    )
