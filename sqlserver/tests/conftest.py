# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import pytest
from datadog_checks.dev import docker_run, get_docker_hostname

CHECK_NAME = 'sqlserver'
HOST = get_docker_hostname()
PORT = 1443
HERE = os.path.dirname(os.path.abspath(__file__))
URL = "http://{}:{}".format(HOST, PORT)
EXPECTED_METRICS = [
    'sqlserver.buffer.cache_hit_ratio',
    'sqlserver.buffer.page_life_expectancy',
    'sqlserver.stats.batch_requests',
    'sqlserver.stats.sql_compilations',
    'sqlserver.stats.sql_recompilations',
    'sqlserver.stats.connections',
    'sqlserver.stats.lock_waits',
    'sqlserver.access.page_splits',
    'sqlserver.stats.procs_blocked',
    'sqlserver.buffer.checkpoint_pages',
]


@pytest.fixture
def get_config():
    return {
        'init_config': {
            'custom_metrics': [
                {
                    'name': 'sqlserver.clr.execution',
                    'type': 'gauge',
                    'counter_name': 'CLR Execution',
                },
                {
                    'name': 'sqlserver.exec.in_progress',
                    'type': 'gauge',
                    'counter_name': 'OLEDB calls',
                    'instance_name': 'Cumulative execution time (ms) per second',
                },
                {
                    'name': 'sqlserver.db.commit_table_entries',
                    'type': 'gauge',
                    'counter_name': 'Log Flushes/sec',
                    'instance_name': 'ALL',
                    'tag_by': 'db',
                },
            ],
        }
    }


@pytest.fixture
def get_sql2008_instance():
    return {
        'host': '({})\SQL2008R2SP2'.format(HOST),
        'username': 'sa',
        'password': 'Password12!',
    }


@pytest.fixture
def get_sql2012_instance():
    return {
        'host': '({})\SQL2012SP1'.format(HOST),
        'username': 'sa',
        'password': 'Password12!',
    }


@pytest.fixture
def get_sql2014_instance():
    return {
        'host': '({})\SQL2014'.format(HOST),
        'username': 'sa',
        'password': 'Password12!',
    }


@pytest.fixture
def get_linux_instance():
    return {
        'host': HOST,
        'username': 'sa',
        'password': 'dd-ci',
    }


@pytest.fixture(scope='session', autouse=True)
def spin_up_sqlserver():
    with docker_run(
        compose_file=os.path.join(HERE, 'compose', 'sqlserver.yaml'),
    ):
        yield
