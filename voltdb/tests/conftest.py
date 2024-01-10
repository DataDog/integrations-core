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
        CheckDockerLogs(compose_file, patterns=['Server completed initialization']),
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
        instance['tls_cert'] = '/tmp/voltdb-certs/client.pem'
        instance['tls_ca_cert'] = '/tmp/voltdb-certs/ca.pem'
        e2e_metadata = {'docker_volumes': ['{}:/tmp/voltdb-certs'.format(common.TLS_CERTS_DIR)]}
    else:
        e2e_metadata = {}

    with docker_run(compose_file, conditions=conditions, env_vars=env_vars, mount_logs=True, attempts=2):
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
        instance['tls_cert'] = common.TLS_CERT
        instance['tls_ca_cert'] = common.TLS_CA_CERT

    return instance


@pytest.fixture(scope='session')
def instance_all(instance):
    # type: (Instance) -> Instance
    instance = common.BASE_INSTANCE.copy()
    instance['statistics_components'] = [
        "COMMANDLOG",
        "CPU",
        "EXPORT",
        "GC",
        "IDLETIME",
        "IMPORT",
        "INDEX",
        "IOSTATS",
        "LATENCY",
        "MEMORY",
        "PROCEDURE",
        "PROCEDUREOUTPUT",
        "PROCEDUREPROFILE",
        "QUEUE",
        "SNAPSHOTSTATUS",
        "TABLE",
    ]

    return instance


@pytest.fixture(scope='session')
def mock_results():
    # type: () -> Iterator
    with open(os.path.join(common.HERE, 'fixtures', 'mock_results.json'), 'r') as f:
        mocked_data = json.load(f)

    def mocked_response(data):
        m = mock.MagicMock()
        m.json = lambda: {"results": [{"data": data}]}
        return m

    def mocked_request(procedure, parameters=None):
        if procedure == '@SystemInformation' and parameters == ['OVERVIEW']:
            return mocked_response([["host-0", "VERSION", "8.4"]])
        if procedure != '@Statistics':
            raise Exception("Bad procedure name")
        parameters = parameters.strip('[').strip(']')
        if parameters not in mocked_data:
            raise Exception("Invalid parameter %s" % parameters)

        return mocked_response(mocked_data[parameters])

    with mock.patch('datadog_checks.voltdb.check.Client') as m:
        m.return_value.request = mocked_request
        yield
