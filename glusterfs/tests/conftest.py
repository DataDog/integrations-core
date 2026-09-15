# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy
import os
import pathlib
from unittest import mock

import pytest

from datadog_checks.base.utils.common import get_docker_hostname
from datadog_checks.dev import WaitFor, docker_run, run_command
from datadog_checks.glusterfs.metrics import BRICK_STATS

from .common import CONFIG, INSTANCE

HERE = os.path.dirname(os.path.abspath(__file__))
HOST = get_docker_hostname()

E2E_METADATA = {
    'start_commands': [
        'apt-get update',
        'apt-get install -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" -y docker.io',
    ],
    'docker_volumes': ['/var/run/docker.sock:/var/run/docker.sock'],
}

FIXTURES_DIR = os.path.join(HERE, 'fixtures', 'gluster')


@pytest.fixture(scope='session')
def dd_environment():
    compose_file = os.path.join(HERE, 'docker', 'docker-compose.yaml')
    with docker_run(
        compose_file=compose_file,
        conditions=[WaitFor(create_volume), WaitFor(gluster_ready)],
        down=delete_volume,
    ):
        yield CONFIG, E2E_METADATA


@pytest.fixture
def instance():
    return copy.deepcopy(INSTANCE)


@pytest.fixture
def config():
    return copy.deepcopy(CONFIG)


@pytest.fixture()
def mock_gluster_xml():
    """Feed the check XML fixtures instead of shelling out to ``gluster``."""
    fixtures = {
        ('volume', 'info'): 'volume_info.xml',
        ('volume', 'status', 'all', 'detail'): 'volume_status.xml',
        ('pool', 'list'): 'pool_list.xml',
        ('volume', 'heal', 'gv0', 'info'): 'heal_info.xml',
    }

    def fake_run_gluster(*args, xml=True):
        if args == ('--version',):
            return pathlib.Path(os.path.join(FIXTURES_DIR, 'version.txt')).read_text()
        key = tuple(args)
        filename = fixtures.get(key)
        if filename is None:
            # Fall back to matching heal info for any volume name.
            if len(args) == 4 and args[0] == 'volume' and args[1] == 'heal' and args[3] == 'info':
                filename = 'heal_info.xml'
            else:
                raise AssertionError(f"Unexpected gluster command in test: {args}")
        return pathlib.Path(os.path.join(FIXTURES_DIR, filename)).read_text()

    with mock.patch('datadog_checks.glusterfs.check.GlusterfsCheck._run_gluster', side_effect=fake_run_gluster):
        yield


def create_volume():
    # The image for some reason doesn't actually start glusterd. So the below two lines will start it manually.
    # Tried also adding the command to the Dockerfile, but that didn't work either. So leaving this here for now.
    run_command(
        "docker exec gluster-node-2 /usr/sbin/glusterd -p /var/run/glusterd.pid --log-level INFO",
        capture=True,
        check=False,
    )
    run_command(
        "docker exec gluster-node-1 /usr/sbin/glusterd -p /var/run/glusterd.pid --log-level INFO",
        capture=True,
        check=False,
    )

    commands = [
        "node-2 mkdir -p /export-test",
        "node-1 mkdir -p /export-test",
        "node-1 gluster peer probe gluster-node-2",
        "node-1 gluster volume create gv0 replica 2 gluster-node-1:/export-test gluster-node-2:/export-test force",
        "node-1 gluster volume start gv0",
    ]

    for command in commands:
        run_command(f"docker exec gluster-{command}", capture=True, check=True)


def gluster_ready():
    # Wait until gluster reports the volume's bricks online with filesystem-derived
    # stats populated. The check skips 'N/A' values, so an unpopulated brick would
    # never emit some metrics and the E2E assertions would fail.
    result = run_command(
        "docker exec gluster-node-1 gluster --xml --mode=script volume status all detail",
        capture=True,
        check=True,
    )
    stdout = result.stdout
    if not stdout.lstrip().startswith('<'):
        raise Exception("gluster volume status did not return XML yet")

    from datadog_checks.glusterfs.gluster_xml import parse_volume_info, parse_volume_status

    volumes = parse_volume_info(
        run_command(
            "docker exec gluster-node-1 gluster --xml --mode=script volume info",
            capture=True,
            check=True,
        ).stdout
    )
    volumes = parse_volume_status(stdout, volumes)
    if not volumes:
        raise Exception("No volume data from gluster yet")

    for vol in volumes:
        for subvol in vol.get('subvols', []):
            bricks = subvol.get('bricks', [])
            if not bricks:
                raise Exception("No brick data yet")
            for brick in bricks:
                if not brick.get('online'):
                    raise Exception(f"Brick {brick.get('name')} is not online yet")
                unpopulated = [field for field in BRICK_STATS if str(brick.get(field)).lower() in ('none', 'n/a')]
                if unpopulated:
                    raise Exception(f"Brick {brick.get('name')} stats not populated yet: {unpopulated}")

    # Wait until self-heal info is available for started volumes. The E2E
    # assertions include heal metrics, so the cluster must be able to answer
    # ``volume heal <vol> info`` before the test runs. This is bounded so a
    # genuinely broken self-heal daemon fails fast instead of hanging the suite.
    import subprocess

    for vol in volumes:
        if vol['status'].lower() != 'started':
            continue
        try:
            subprocess.run(
                [
                    'docker',
                    'exec',
                    'gluster-node-1',
                    'gluster',
                    '--xml',
                    '--mode=script',
                    'volume',
                    'heal',
                    vol['name'],
                    'info',
                ],
                capture_output=True,
                text=True,
                timeout=30,
                check=True,
            )
        except subprocess.TimeoutExpired:
            raise Exception(f"Self-heal info for volume {vol['name']} is not responding yet")
        except subprocess.CalledProcessError as e:
            raise Exception(f"Self-heal info for volume {vol['name']} failed: {e.stderr or e.stdout}")


def delete_volume():
    run_command("docker exec gluster-node-1 gluster volume stop gv0 force", capture=True, check=False)
    run_command("docker exec gluster-node-1 gluster volume delete gv0", capture=True, check=True)
