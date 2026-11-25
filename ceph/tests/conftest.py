# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import json
import os

import pytest

from datadog_checks.dev import docker_run, run_command
from datadog_checks.dev.conditions import WaitFor

from .common import BASIC_CONFIG, HERE

E2E_METADATA = {
    'start_commands': [
        'apt-get update',
        'apt-get install -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" -y docker.io',
    ],
    'docker_volumes': ['/var/run/docker.sock:/var/run/docker.sock'],
}


def ceph(*args: str) -> str:
    return run_command(['docker', 'exec', 'dd-test-ceph', 'ceph', *args], capture='out', check=True).stdout


def wait_for_healthy_cluster() -> None:
    # The cluster reports HEALTH_OK before its placement groups are active, so both are required.
    pg_stat = json.loads(ceph('pg', 'stat', '-fjson'))
    # Newer releases nest the summary under `pg_summary`.
    pg_summary = pg_stat.get('pg_summary', pg_stat)
    total = pg_summary['num_pgs']
    clean = sum(s['num'] for s in pg_summary['num_pg_by_state'] if s['name'] == 'active+clean')
    if total == 0 or clean != total:
        raise Exception('Placement groups are not clean yet: {}/{}'.format(clean, total))

    health = ceph('health')
    if not health.startswith('HEALTH_OK'):
        raise Exception('Cluster is not healthy yet: {}'.format(health))

    # A monitor can be out of quorum before the cluster reports MON_DOWN.
    status = json.loads(ceph('status', '-fjson'))
    if len(status['quorum']) != status['monmap']['num_mons']:
        raise Exception('Monitors are not all in quorum yet: {}'.format(status['quorum_names']))


@pytest.fixture(scope="session")
def dd_environment():
    compose_file = os.path.join(HERE, 'compose', 'docker-compose.yaml')
    with docker_run(
        compose_file=compose_file,
        conditions=[WaitFor(wait_for_healthy_cluster, attempts=60, wait=5)],
        attempts=3,
    ):
        yield BASIC_CONFIG, E2E_METADATA
