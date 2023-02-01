# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import random
import string
from copy import deepcopy

import pytest
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
        'instances': [common.INSTANCE],
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
        # 'custom_queries': request.param.get('custom_queries'),
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


@pytest.fixture
def fixture_query_time_series(request):
    exception = request.param.get('exception')
    if exception:
        return Exception(exception)
    return [
        {
            'metric': f'{request.param["category"]}.{metric}',
            'value': random.uniform(0, 1000),
            'tags': [f'cloudera_{request.param["category"]}:{request.param["name"]}'],
        }
        for metric in request.param["metrics"][request.param["category"]]
    ]
