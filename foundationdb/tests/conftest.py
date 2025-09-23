# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import os
import time

import pytest

from datadog_checks.dev import WaitFor, docker_run, run_command

from .common import E2E_CONFIG, E2E_METADATA, E2E_TLS_CONFIG, HERE, INSTANCE, PROTOCOL, TLS_INSTANCE


@pytest.fixture(scope='session')
def dd_environment():
    if PROTOCOL == 'tls':
        compose_file = os.path.join(HERE, 'docker', 'docker-compose-tls.yaml')
        with docker_run(compose_file=compose_file, conditions=[WaitFor(create_tls_database)]):
            yield E2E_TLS_CONFIG, E2E_METADATA
    else:
        compose_file = os.path.join(HERE, 'docker', 'docker-compose.yaml')
        with docker_run(compose_file=compose_file, conditions=[WaitFor(create_database)]):
            yield E2E_CONFIG, E2E_METADATA


@pytest.fixture
def instance():
    return INSTANCE


@pytest.fixture
def tls_instance():
    return TLS_INSTANCE


def create_tls_database():
    create_database(True)


def create_database(tls=False):
    if tls:
        status_command = (
            'docker exec fdb-coordinator fdbcli -C /var/fdb/fdb.cluster --tls_certificate_file '
            '/var/fdb/fdb.pem --tls_key_file /var/fdb/private.key --tls_verify_peers Check.Valid=0 '
            '--exec "status json"'
        )
    else:
        status_command = 'docker exec fdb-0 fdbcli --exec "status json"'
    base_status = run_command(status_command, capture=True, check=True)
    status = json.loads(base_status.stdout)
    if not status.get('client').get('database_status').get('available'):
        if tls:
            command = (
                'docker exec fdb-coordinator fdbcli -C /var/fdb/fdb.cluster --tls_certificate_file '
                '/var/fdb/fdb.pem --tls_key_file /var/fdb/private.key --tls_verify_peers Check.Valid=0 '
                '--exec "configure new single memory"'
            )
        else:
            command = 'docker exec fdb-0 fdbcli --exec "configure new single memory"'
        run_command(command, capture=True, check=True)
    i = 0
    is_healthy = False
    has_latency_stats = False
    # Wait for 1 minute for the database to become available for testing
    while i < 60 and not (is_healthy and has_latency_stats):
        time.sleep(1)
        base_status = run_command(status_command, capture=True, check=True)
        status = json.loads(base_status.stdout)
        is_healthy = status.get('cluster').get('data').get('state').get('name') == 'healthy'
        has_latency_stats = False
        for _, process in status.get('cluster').get('processes').items():
            for role in process.get('roles'):
                if "commit_latency_statistics" in role:
                    has_latency_stats = True
        i += 1
    if not tls:
        test_data_fill_command = (
            'docker exec fdb-0 fdbcli --exec "writemode on; set basket_size 10; set temperature 37; writemode off"'
        )
        data_committed = run_command(test_data_fill_command, capture=True, check=True)
        assert 'Committed' in data_committed.stdout
