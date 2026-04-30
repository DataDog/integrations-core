# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import os

import pytest

from datadog_checks.dev import WaitFor, run_command

from . import common

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.skipif(not common.AUTODISCOVERY_PROCESS, reason='Requires REDIS_AUTODISCOVERY_PROCESS=true'),
]


def _agent_container_name():
    env = os.environ['HATCH_ENV_ACTIVE']
    return f'dd_redisdb_{env}'


def _redisdb_scheduled_and_running():
    # The short-lived `agent check` subprocess used by `dd_agent_check` cannot
    # be used here: its workloadmeta never finishes initialising before the
    # process listener can match the redis-server process, so it gives up
    # without scheduling any redisdb config. We verify against the long-lived
    # agent's status JSON instead.
    container = _agent_container_name()
    configcheck = run_command(
        ['docker', 'exec', container, 'agent', 'configcheck'],
        capture=True,
        check=True,
    )
    assert 'redisdb' in configcheck.stdout, configcheck.stdout
    assert 'host: 127.0.0.1' in configcheck.stdout, configcheck.stdout
    assert 'port: 6379' in configcheck.stdout, configcheck.stdout

    status = run_command(
        ['docker', 'exec', container, 'agent', 'status', '--json'],
        capture=True,
        check=True,
    )
    checks = json.loads(status.stdout).get('runnerStats', {}).get('Checks', {}).get('redisdb', {})
    assert checks, f'redisdb not in runnerStats: {status.stdout[:500]}'
    info = next(iter(checks.values()))
    assert info['TotalRuns'] >= 1, info
    assert info['TotalErrors'] == 0, info
    assert info['TotalServiceChecks'] >= 1, info


@pytest.fixture
def redisdb_scheduled_and_running():
    WaitFor(_redisdb_scheduled_and_running, attempts=60, wait=2)()


def test_e2e_autodiscovery_process(redisdb_scheduled_and_running):
    # All assertions are in the fixture: configcheck shows the redisdb
    # config was scheduled with `host: 127.0.0.1, port: 6379` (the agent
    # substituted `%%host%%` after matching the redis-server process via
    # the cel://process listener), and the running agent has executed the
    # check at least once with no errors.
    pass
