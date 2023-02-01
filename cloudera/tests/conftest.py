# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import random
import string
from copy import deepcopy

import pytest
from cm_client.models.api_event import ApiEvent
from cm_client.models.api_event_attribute import ApiEventAttribute
from cm_client.models.api_event_query_result import ApiEventQueryResult
from cm_client.models.api_time_series import ApiTimeSeries
from cm_client.models.api_time_series_data import ApiTimeSeriesData
from cm_client.models.api_time_series_metadata import ApiTimeSeriesMetadata
from cm_client.models.api_time_series_response import ApiTimeSeriesResponse
from cm_client.models.api_time_series_response_list import ApiTimeSeriesResponseList
from packaging.version import Version

from datadog_checks.cloudera import ClouderaCheck
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
        'instances': [common.INSTANCE_WITH_TAGS],
        'init_config': common.INIT_CONFIG,
    }


@pytest.fixture
def instance(request):
    clusters = request.param.get('clusters')
    tags = request.param.get('tags')
    return {
        'cloudera_client': request.param.get('cloudera_client'),
        'api_url': request.param.get('api_url'),
        'tags': tags if tags else None,
        'clusters': clusters if clusters else None,
    }


@pytest.fixture(scope='session')
def cloudera_check():
    return lambda instance: deepcopy(ClouderaCheck('cloudera', init_config=common.INIT_CONFIG, instances=[instance]))


@pytest.fixture
def cloudera_version(request):
    exception = request.param.get('exception')
    if exception:
        return Exception(exception)
    version = request.param.get('version')
    return Version(version) if version else None


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


@pytest.fixture
def read_clusters(request):
    exception = request.param.get('exception')
    if exception:
        return Exception(exception)
    return [
        {
            'name': f'{prefix}{n}',
            'entity_status': status,
            'tags': [{'name': f'tag_{n}', 'value': f'value_{n}'} for n in range(request.param.get('tags_number', 0))],
        }
        for n in range(request.param['number'])
        for prefix in request.param['prefix']
        for status in request.param['status']
    ]


@pytest.fixture
def list_hosts(request):
    exception = request.param.get('exception')
    if exception:
        return Exception(exception)
    return [
        {
            'host_id': ''.join(random.choices(string.ascii_uppercase + string.digits, k=8)),
            'name': f'{prefix}{n}',
            'entity_status': status,
            'num_cores': 8,
            'num_physical_cores': 8,
            'total_phys_mem_bytes': 33079799808,
            'rack_id': request.param['rack_id'],
            'tags': [{'name': f'tag_{n}', 'value': f'value_{n}'} for n in range(request.param.get('tags_number', 0))],
        }
        for n in range(request.param['number'])
        for prefix in request.param['prefix']
        for status in request.param['status']
    ]


@pytest.fixture
def read_events(request):
    exception = request.param.get('exception')
    if exception:
        return Exception(exception)
    return [
        {
            'msg_text': f'{content}{n}',
        }
        for n in range(request.param['number'])
        for content in request.param['content']
    ]
