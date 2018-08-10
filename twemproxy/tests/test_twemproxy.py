from datadog_checks.utils.common import get_docker_hostname

import os
import subprocess
import pytest

from datadog_checks.twemproxy import Twemproxy

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))


@pytest.fixture
def check():
    check = Twemproxy('twemproxy', {}, {})
    return check


@pytest.fixture(scope="session")
def spin_up_twemproxy():
    """
    Start a cluster with one master, one replica and one unhealthy replica and
    stop it after the tests are done.
    If there's any problem executing docker-compose, let the exception bubble
    up.
    """

    env = os.environ

    compose_file = os.path.join(HERE, 'compose', 'docker-compose.yaml')

    env['DOCKER_COMPOSE_FILE'] = compose_file
    env['DOCKER_ADDR'] = get_docker_hostname()

    args = [
        "docker-compose",
        "-f", compose_file
    ]

    try:
        subprocess.check_call(args + ["up", "-d"], env=env)
        # setup_twempoxy(env=env)
    except Exception:
        # cleanup_twemproxy(args, env)
        raise

    yield
    # cleanup_twemproxy(args, env)


def test_check(check, spin_up_twemproxy):
    pass
