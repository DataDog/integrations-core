# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import os
from typing import Iterator  # noqa: F401

import mock
import pytest

from datadog_checks.dev import docker_run
from datadog_checks.dev.conditions import CheckDockerLogs
from datadog_checks.voltdb.types import Instance  # noqa: F401

from . import common
from .utils import CreateSchema, EnsureExpectedMetricsShowUp


@pytest.fixture(scope='session')
def dd_environment(instance):
    # type: (Instance) -> Iterator
    compose_file = os.path.join(common.HERE, 'compose', 'docker-compose.yaml')

    schema_file = os.path.join(common.HERE, 'compose', 'schema.sql')
    with open(schema_file) as f:
        schema = f.read()

    conditions = [
        CheckDockerLogs(
            compose_file,
            patterns=['Server completed initialization'],
            service='voltdb0',
        ),
        CheckDockerLogs(
            compose_file,
            patterns=['Server completed initialization'],
            service='voltdb1',
        ),
        CheckDockerLogs(
            compose_file,
            patterns=['Server completed initialization'],
            service='voltdb2',
        ),
        CreateSchema(compose_file, schema, container_name='voltdb0'),
        EnsureExpectedMetricsShowUp(instance),
    ]

    env_vars = {
        'VOLTDB_IMAGE': common.VOLTDB_IMAGE,
        'VOLTDB_DEPLOYMENT': common.VOLTDB_DEPLOYMENT,
        'VOLTDB_CLIENT_PORT': str(common.VOLTDB_CLIENT_PORT),
    }

    if common.TLS_ENABLED:
        # Must refer to a path within the Agent container.
        instance = instance.copy()
        instance['ssl_config_file'] = '/tmp/voltdb-certs/ca.pem'
        e2e_metadata = {'docker_volumes': ['{}:/tmp/voltdb-certs'.format(common.TLS_CERTS_DIR)]}
    else:
        e2e_metadata = {}

    with docker_run(
        compose_file,
        conditions=conditions,
        env_vars=env_vars,
        mount_logs=True,
        attempts=2,
    ):
        yield instance, e2e_metadata


@pytest.fixture(scope='session')
def instance():
    # type: () -> Instance
    instance = common.BASE_INSTANCE.copy()
    instance['custom_queries'] = [
        {
            'query': 'HeroStats',
            'columns': [
                {'name': 'custom.heroes.count', 'type': 'gauge'},
                {'name': 'custom.heroes.avg_name_length', 'type': 'gauge'},
            ],
            'tags': ['custom:voltdb'],
        },
    ]

    if common.TLS_ENABLED:
        instance['use_ssl'] = True
        instance['ssl_config_file'] = common.TLS_CONFIG_FILE

    return instance


@pytest.fixture(scope='session')
def instance_all(instance):
    # type: (Instance) -> Instance
    instance = common.BASE_INSTANCE.copy()
    instance['statistics_components'] = [
        'COMMANDLOG',
        'CPU',
        'EXPORT',
        'GC',
        'IDLETIME',
        'IMPORT',
        'INDEX',
        'IOSTATS',
        'LATENCY',
        'MEMORY',
        'PROCEDURE',
        'PROCEDUREOUTPUT',
        'PROCEDUREPROFILE',
        'QUEUE',
        'SNAPSHOTSTATUS',
        'TABLE',
    ]

    return instance

    # Column headers for each `@Statistics` component, matching the positional
    # layout of rows in tests/fixtures/mock_results.json. Used by the mock to expose
    # `VoltTable.columns` so that the check can look up values by name.


MOCK_COLUMN_HEADERS = {
    'CPU': ['TIMESTAMP', 'HOST_ID', 'HOSTNAME', 'PERCENT_USED'],
    'MEMORY': [
        'TIMESTAMP',
        'HOST_ID',
        'HOSTNAME',
        'RSS',
        'JAVAUSED',
        'JAVAUNUSED',
        'TUPLEDATA',
        'TUPLEALLOCATED',
        'INDEXMEMORY',
        'STRINGMEMORY',
        'TUPLECOUNT',
        'POOLEDMEMORY',
        'PHYSICALMEMORY',
        'JAVAMAXHEAP',
    ],
    'SNAPSHOTSTATUS': [
        'TIMESTAMP',
        'HOST_ID',
        'HOSTNAME',
        'TABLE',
        'PATH',
        'FILENAME',
        'NONCE',
        'TXNID',
        'START_TIME',
        'END_TIME',
        'SIZE',
        'DURATION',
        'THROUGHPUT',
        'RESULT',
        'TYPE',
    ],
    'COMMANDLOG, 1': [
        'TIMESTAMP',
        'HOST_ID',
        'HOSTNAME',
        'OUTSTANDING_BYTES',
        'OUTSTANDING_TXNS',
        'IN_USE_SEGMENT_COUNT',
        'SEGMENT_COUNT',
        'FSYNC_INTERVAL',
    ],
    'PROCEDURE, 1': [
        'TIMESTAMP',
        'HOST_ID',
        'HOSTNAME',
        'SITE_ID',
        'PARTITION_ID',
        'PROCEDURE',
        'INVOCATIONS',
        'TIMED_INVOCATIONS',
        'MIN_EXECUTION_TIME',
        'MAX_EXECUTION_TIME',
        'AVG_EXECUTION_TIME',
        'MIN_RESULT_SIZE',
        'MAX_RESULT_SIZE',
        'AVG_RESULT_SIZE',
        'MIN_PARAMETER_SET_SIZE',
        'MAX_PARAMETER_SET_SIZE',
        'AVG_PARAMETER_SET_SIZE',
        'ABORTS',
        'FAILURES',
        'TRANSACTIONAL',
    ],
    'LATENCY': [
        'TIMESTAMP',
        'HOST_ID',
        'HOSTNAME',
        'INTERVAL',
        'COUNT',
        'TPS',
        'P50',
        'P95',
        'P99',
        'P99.9',
        'P99.99',
        'P99.999',
        'MAX',
    ],
    'GC, 1': [
        'TIMESTAMP',
        'HOST_ID',
        'HOSTNAME',
        'NEWGEN_GC_COUNT',
        'NEWGEN_AVG_GC_TIME',
        'OLDGEN_GC_COUNT',
        'OLDGEN_AVG_GC_TIME',
    ],
    'IOSTATS, 1': [
        'TIMESTAMP',
        'HOST_ID',
        'HOSTNAME',
        'CONNECTION_ID',
        'CONNECTION_HOSTNAME',
        'BYTES_READ',
        'MESSAGES_READ',
        'BYTES_WRITTEN',
        'MESSAGES_WRITTEN',
    ],
    'TABLE, 1': [
        'TIMESTAMP',
        'HOST_ID',
        'HOSTNAME',
        'SITE_ID',
        'PARTITION_ID',
        'TABLE_NAME',
        'TABLE_TYPE',
        'TUPLE_COUNT',
        'TUPLE_ALLOCATED_MEMORY',
        'TUPLE_DATA_MEMORY',
        'STRING_DATA_MEMORY',
        'TUPLE_LIMIT',
        'PERCENT_FULL',
    ],
    'INDEX, 1': [
        'TIMESTAMP',
        'HOST_ID',
        'HOSTNAME',
        'SITE_ID',
        'PARTITION_ID',
        'INDEX_NAME',
        'TABLE_NAME',
        'INDEX_TYPE',
        'IS_UNIQUE',
        'IS_COUNTABLE',
        'ENTRY_COUNT',
        'MEMORY_ESTIMATE',
    ],
    'EXPORT, 1': [
        'TIMESTAMP',
        'HOST_ID',
        'HOSTNAME',
        'SITE_ID',
        'PARTITION_ID',
        'SOURCE',
        'TARGET',
        'ACTIVE',
        'TUPLE_COUNT',
        'TUPLE_PENDING',
        'LAST_QUEUED_TIMESTAMP',
        'LAST_ACKED_TIMESTAMP',
        'AVERAGE_LATENCY',
        'MAX_LATENCY',
        'QUEUE_GAP',
        'STATUS',
    ],
    'IMPORT, 1': [
        'TIMESTAMP',
        'HOST_ID',
        'HOSTNAME',
        'SITE_ID',
        'IMPORTER_NAME',
        'PROCEDURE_NAME',
        'SUCCESSES',
        'FAILURES',
        'OUTSTANDING_REQUESTS',
        'RETRIES',
    ],
    'QUEUE, 1': [
        'TIMESTAMP',
        'HOST_ID',
        'HOSTNAME',
        'SITE_ID',
        'CURRENT_DEPTH',
        'POLL_COUNT',
        'AVG_WAIT',
        'MAX_WAIT',
    ],
    'IDLETIME, 1': [
        'TIMESTAMP',
        'HOST_ID',
        'HOSTNAME',
        'SITE_ID',
        'COUNT',
        'PERCENT',
        'AVG',
        'MIN',
        'MAX',
        'STDDEV',
    ],
    'PROCEDUREOUTPUT': [
        'TIMESTAMP',
        'PROCEDURE',
        'WEIGHTED_PERC',
        'INVOCATIONS',
        'MIN_RESULT_SIZE',
        'MAX_RESULT_SIZE',
        'AVG_RESULT_SIZE',
        'TOTAL_RESULT_SIZE_MB',
    ],
    'PROCEDUREPROFILE': [
        'TIMESTAMP',
        'PROCEDURE',
        'WEIGHTED_PERC',
        'INVOCATIONS',
        'AVG',
        'MIN',
        'MAX',
        'ABORTS',
        'FAILURES',
    ],
}


def _mock_columns(header_names):
    columns = []
    for name in header_names:
        col = mock.MagicMock()
        col.name = name
        columns.append(col)
    return columns


@pytest.fixture(scope='session')
def mock_results():
    # type: () -> Iterator
    with open(os.path.join(common.HERE, 'fixtures', 'mock_results.json'), 'r') as f:
        mocked_data = json.load(f)

    def mocked_response(rows, header_names):
        table = mock.MagicMock()
        table.tuples = rows
        table.columns = _mock_columns(header_names)
        resp = mock.MagicMock()
        resp.status = 1  # Client.SUCCESS
        resp.statusString = None
        resp.tables = [table]
        return resp

    def mocked_call_procedure(procedure, params=None):
        params = params or []
        if procedure == '@SystemInformation' and params == ['OVERVIEW']:
            return mocked_response([['host-0', 'VERSION', '8.4']], ['HOST_ID', 'KEY', 'VALUE'])
        if procedure != '@Statistics':
            raise Exception('Bad procedure name: %s' % procedure)
            # @Statistics params look like ['CPU'] or ['COMMANDLOG', 1].
        if len(params) == 1:
            key = params[0]
        else:
            key = '{}, {}'.format(params[0], params[1])
        if key not in mocked_data:
            raise Exception('Invalid parameter %s' % key)
        return mocked_response(mocked_data[key], MOCK_COLUMN_HEADERS[key])

    with mock.patch('datadog_checks.voltdb.check.Client') as m:
        client = m.return_value
        client.SUCCESS = 1
        client.call_procedure = mocked_call_procedure
        client.raise_for_status = lambda r: None
        client.close = lambda: None
        yield
