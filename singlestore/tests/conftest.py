# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import csv
import json
import os
import re

import mock
import pytest

from datadog_checks.dev import docker_run, get_docker_hostname, get_here

TABLE_EXTRACTION_PATTERN = re.compile(r'SELECT .* FROM \w+\.(\w+)')
HERE = get_here()


def _mock_execute(query):
    table = TABLE_EXTRACTION_PATTERN.search(query).groups()[0].lower()
    file = os.path.join(HERE, 'fixtures', table + '.csv')
    with open(file, 'r') as f:
        reader = csv.reader(f)
        for line in reader:
            yield line


@pytest.fixture(scope='session')
def dd_environment():
    compose_file = os.path.join(HERE, 'compose', 'docker-compose.yaml')
    license_key = os.environ.get('SINGLESTORE_LICENSE')
    if not license_key:
        raise Exception("Please set SINGLESTORE_LICENSE environment variable to a valid base64-encoded license.")

    with docker_run(compose_file, env_vars={'LICENSE_KEY': license_key}, log_patterns=r'Listening on 0\.0\.0\.0'):
        yield {
            'host': get_docker_hostname(),
            'username': 'root',
            'password': 'password',
            'collect_system_metrics': True,
        }


@pytest.fixture()
def mock_cursor():
    with mock.patch('datadog_checks.singlestore.check.pymysql') as pymysql:
        cursor = mock.MagicMock(name='cursor')
        connect = mock.MagicMock(name='connect', cursor=lambda: cursor)
        pymysql.connect.return_value = connect
        cursor.execute = lambda x: setattr(cursor, 'mock_last_query', x)  # noqa
        cursor.rowcount = float('+inf')
        cursor.fetchall = lambda: _mock_execute(cursor.mock_last_query)
        yield


@pytest.fixture()
def expected_default_metrics():
    file_names = ['aggregators.json', 'leaves.json', 'mv_global_status.json']
    metrics = []
    for file_name in file_names:
        with open(os.path.join(HERE, 'results', file_name), 'r') as f:
            metrics.extend(json.load(f))
    return metrics


@pytest.fixture()
def expected_system_metrics():
    file_names = ['mv_sysinfo.json']
    metrics = []
    for file_name in file_names:
        with open(os.path.join(HERE, 'results', file_name), 'r') as f:
            metrics.extend(json.load(f))
    return metrics


@pytest.fixture
def instance():
    return {'host': "localhost", 'username': 'admin', 'tags': ['foo:bar']}
