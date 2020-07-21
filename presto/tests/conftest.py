# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
from copy import deepcopy

import prestodb
import pytest

from datadog_checks.dev import docker_run, get_here
from datadog_checks.dev.conditions import CheckDockerLogs, WaitFor
from datadog_checks.dev.utils import load_jmx_config


@pytest.fixture(scope='session')
def dd_environment(instance):

    compose_file = os.path.join(get_here(), 'docker', 'docker-compose.yaml')
    with docker_run(compose_file, conditions=[WaitFor(make_query), CheckDockerLogs(compose_file, 'SERVER STARTED')]):
        yield instance, {'use_jmx': True}


def make_query():
    # make a query so that all metrics are emitted in the e2e test
    conn = prestodb.dbapi.connect(host='localhost', port=8080, user='test', catalog='test', schema='test',)
    cur = conn.cursor()
    cur.execute('SELECT * FROM system.runtime.nodes')
    cur.fetchall()


@pytest.fixture(scope='session', autouse=True)
@pytest.mark.usefixtures('dd_environment')
def instance():
    inst = load_jmx_config()
    # Add presto coordinator to the configuration
    inst.get('instances').append(deepcopy(inst.get('instances')[0]))
    inst['instances'][0]['port'] = 9997

    return inst
