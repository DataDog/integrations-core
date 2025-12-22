# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
from copy import deepcopy

import pytest

from datadog_checks.base.utils.platform import Platform
from datadog_checks.dev.conditions import CheckCommandOutput, WaitFor
from datadog_checks.dev.docker import CheckDockerLogs, docker_run

from .common import COMPOSE_FILE, HOST, INSTANCE, OPENMETRICS_V2_INSTANCE, PORT


def init_db():
    # exit if we are not on linux
    # that's the only platform where the client successfully installs for version 3.10
    if not Platform.is_linux():
        return

    import aerospike

    # sample Aerospike Python Client code
    # https://www.aerospike.com/docs/client/python/usage/kvs/write.html
    client = aerospike.client({'hosts': [(HOST, PORT)]}).connect()

    key = ('test', 'characters', 'bender')
    bins = {
        'name': 'Bender',
        'serialnum': 2716057,
        'lastsentence': {
            'BBS': "Well, we're boned",
            'TBwaBB': 'I love you, meatbags!',
            'BG': 'Whip harder, Professor!',
            'ltWGY': 'Into the breach, meatbags. Or not, whatever',
        },
        'composition': ['40% zinc', '40% titanium', '30% iron', '40% dolomite'],
        'apartment': bytearray(b'\x24'),
        'quote_cnt': 47,
    }
    client.put(key, bins)
    # Create at an index
    client.index_string_create('test', 'characters', 'name', 'idx_characters_name')

    batch_keys = []
    for i in range(10):
        client.get(key)
        batch_key = ('test', 'demo', 'key' + str(i))
        batch_keys.append(batch_key)
    client.get_many(batch_keys)

    client.close()


def _get_conditions():
    conditions = [
        CheckDockerLogs(COMPOSE_FILE, ['service ready: soon there will be cake!']),
        WaitFor(init_db),
    ]

    # Wait for Aerospike to calculate latency/throughput metrics (only needed for versions <= 5.0)
    # We use the output of this docker exec command line for checking instead with the client,
    # because this is the command used to retrieve the metric and we know its output format.
    aerospike_version = os.environ.get('AEROSPIKE_VERSION', '')
    if aerospike_version:
        parts = aerospike_version.split('.')[:2]
        major_minor = (int(parts[0]), int(parts[1]))
    else:
        major_minor = (0, 0)
    if major_minor <= (5, 0):
        conditions.append(
            CheckCommandOutput(
                ['docker', 'exec', 'aerospike', 'asinfo', '-v', 'throughput:'],
                patterns=[r'\{test\}-(read|write)'],
                attempts=30,
                wait=1,
            )
        )

    return conditions


@pytest.fixture(scope='session')
def dd_environment():
    with docker_run(
        COMPOSE_FILE,
        conditions=_get_conditions(),
        attempts=2,
    ):
        yield OPENMETRICS_V2_INSTANCE


@pytest.fixture
def instance():
    return deepcopy(INSTANCE)


@pytest.fixture
def instance_openmetrics_v2():
    return deepcopy(OPENMETRICS_V2_INSTANCE)
