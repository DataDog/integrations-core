# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from copy import deepcopy

import pytest

from datadog_checks.base.utils.platform import Platform
from datadog_checks.dev.conditions import WaitFor
from datadog_checks.dev.docker import CheckDockerLogs, docker_run

from .common import COMPOSE_FILE, HOST, INSTANCE, PORT


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

    for _ in range(10):
        client.get(key)

    client.close()


@pytest.fixture(scope='session')
def dd_environment():
    with docker_run(
        COMPOSE_FILE,
        conditions=[CheckDockerLogs(COMPOSE_FILE, ['service ready: soon there will be cake!']), WaitFor(init_db)],
    ):
        yield INSTANCE


@pytest.fixture
def instance():
    return deepcopy(INSTANCE)
