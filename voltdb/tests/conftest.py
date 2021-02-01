# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
from typing import Iterator

import pytest

from datadog_checks.dev import docker_run
from datadog_checks.dev.conditions import CheckDockerLogs
from datadog_checks.voltdb.types import Instance

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

    with docker_run(compose_file, conditions=conditions, env_vars=env_vars, mount_logs=True):
        yield instance, e2e_metadata


@pytest.fixture(scope='session')
def instance():
    # type: () -> Instance
    instance = {
        'url': common.VOLTDB_URL,
        'username': 'doggo',
        'password': 'doggopass',  # SHA256: e81255cee7bd2c4fbb4c8d6e9d6ba1d33a912bdfa9901dc9acfb2bd7f3e8eeb1
        'custom_queries': [
            {
                'query': 'HeroStats',
                'columns': [
                    {'name': 'custom.heroes.count', 'type': 'gauge'},
                    {'name': 'custom.heroes.avg_name_length', 'type': 'gauge'},
                ],
                'tags': ['custom:voltdb'],
            },
        ],
        'tags': ['test:voltdb'],
    }  # type: Instance

    if common.TLS_ENABLED:
        instance['tls_cert'] = common.TLS_CERT
        instance['tls_ca_cert'] = common.TLS_CA_CERT

    return instance
