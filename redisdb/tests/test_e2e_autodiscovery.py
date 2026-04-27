# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import os

import pytest

from datadog_checks.dev import WaitFor, run_command
from datadog_checks.redisdb import Redis

from . import common

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.skipif(not common.AUTODISCOVERY, reason='Requires REDIS_AUTODISCOVERY=true'),
]


def _agent_container_name():
    env = os.environ['HATCH_ENV_ACTIVE']
    return f'dd_redisdb_{env}'


def _autodiscovery_ready():
    result = run_command(
        ['docker', 'exec', _agent_container_name(), 'agent', 'configcheck'],
        capture=True,
        check=True,
    )
    assert 'redisdb' in result.stdout, result.stdout


@pytest.fixture
def autodiscovery_ready():
    WaitFor(_autodiscovery_ready, attempts=30, wait=2)()


def test_e2e_autodiscovery_default_port(dd_agent_check, autodiscovery_ready):
    aggregator = dd_agent_check(
        {'init_config': {}, 'instances': []},
        rate=True,
        discovery_min_instances=1,
        discovery_timeout=30,
    )
    aggregator.assert_service_check(
        'redis.can_connect',
        status=Redis.OK,
        tags=['redis_port:6379'],
        at_least=1,
    )
