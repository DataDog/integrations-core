# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from copy import deepcopy

import aerospike
import pytest

from datadog_checks.dev.conditions import CheckEndpoints, WaitFor
from datadog_checks.dev.docker import CheckDockerLogs, docker_run
from .common import COMPOSE_FILE, HOST, INSTANCE, PORT


def init_db():
    # sample Aerospike Python Client code
    # https://www.aerospike.com/docs/client/python/usage/kvs/write.html
    client = aerospike.client({'hosts': [(HOST, 3000)]}).connect()

    key = ('test', 'characters', 'bender')
    bins = {
        'name': 'Bender',
        'serialnum': 2716057,
        'lastsentence': {
            'BBS': "Well, we're boned",
            'TBwaBB': 'I love you, meatbags!',
            'BG': 'Whip harder, Professor!',
            'ltWGY': 'Into the breach, meatbags. Or not, whatever'},
        'composition': ['40% zinc', '40% titanium', '30% iron', '40% dolomite'],
        'apartment': bytearray(b'\x24'),
        'quote_cnt': 47
    }
    client.put(key, bins)
    client.close()


@pytest.fixture(scope='session')
def dd_environment():
    with docker_run(
        COMPOSE_FILE,
        conditions=[
            CheckEndpoints(['http://{}:{}'.format(HOST, PORT)]),
            CheckDockerLogs(COMPOSE_FILE, ['service ready: soon there will be cake!']),
            WaitFor(init_db),
        ],
    ):
        yield INSTANCE


@pytest.fixture
def instance():
    return deepcopy(INSTANCE)
