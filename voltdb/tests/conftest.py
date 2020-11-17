# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import pytest

from datadog_checks.dev import docker_run
from datadog_checks.dev.conditions import CheckDockerLogs
from datadog_checks.voltdb.types import Instance

from . import common
from .utils import CreateSchema, EnsureExpectedMetricsShowUp


@pytest.fixture(scope='session')
def dd_environment(instance):
    compose_filename = 'docker-compose-tls.yaml' if common.TLS_ENABLED else 'docker-compose.yaml'
    compose_file = os.path.join(common.HERE, 'compose', compose_filename)

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
        'VOLTDB_CLIENT_PORT': str(common.VOLTDB_CLIENT_PORT),
        'TLS_OUTPUT_DIR': common.TLS_OUTPUT_DIR,
        'TLS_CONTAINER_LOCALCERT_PATH': common.TLS_CONTAINER_LOCALCERT_PATH,
    }

    with docker_run(compose_file, conditions=conditions, env_vars=env_vars):
        yield instance


@pytest.fixture(scope='session')
def instance():
    # type: () -> Instance
    instance = {
        'url': common.VOLTDB_URL,
        'username': 'doggo',
        'password': 'doggopass',  # SHA256: e81255cee7bd2c4fbb4c8d6e9d6ba1d33a912bdfa9901dc9acfb2bd7f3e8eeb1
    }  # type: Instance

    if common.TLS_ENABLED:
        instance['tls_verify'] = False  # We use self-signed certs.
        instance['tls_cert'] = (common.TLS_CLIENT_CERT, common.TLS_PASSWORD)

    return instance
