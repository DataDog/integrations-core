import getpass
import logging
import os
import subprocess
from copy import deepcopy

import mock
import pytest
import requests

from datadog_checks.dev import TempDir, WaitFor, docker_run
from datadog_checks.haproxy import HAProxy

from .common import (
    CHECK_CONFIG,
    CHECK_CONFIG_OPEN,
    CONFIG_TCPSOCKET,
    HAPROXY_VERSION,
    HERE,
    PASSWORD,
    STATS_URL,
    STATS_URL_OPEN,
    USERNAME,
    platform_supports_sockets,
)

log = logging.getLogger('test_haproxy')


def wait_for_haproxy():
    res = requests.get(STATS_URL, auth=(USERNAME, PASSWORD))
    res.raise_for_status()


def wait_for_haproxy_open():
    res_open = requests.get(STATS_URL_OPEN)
    res_open.raise_for_status()


@pytest.fixture(scope='session')
def dd_environment():
    env = {}
    env['HAPROXY_CONFIG_DIR'] = os.path.join(HERE, 'compose')
    env['HAPROXY_CONFIG_OPEN'] = os.path.join(HERE, 'compose', 'haproxy-open.cfg')
    with docker_run(
        compose_file=os.path.join(HERE, 'compose', 'haproxy.yaml'),
        env_vars=env,
        service_name="haproxy-open",
        conditions=[WaitFor(wait_for_haproxy_open)],
    ):

        if platform_supports_sockets:
            with TempDir() as temp_dir:
                host_socket_path = os.path.join(temp_dir, 'datadog-haproxy-stats.sock')
                env['HAPROXY_CONFIG'] = os.path.join(HERE, 'compose', 'haproxy.cfg')
                if os.environ.get('HAPROXY_VERSION', '1.5.11').split('.')[:2] >= ['1', '6']:
                    env['HAPROXY_CONFIG'] = os.path.join(HERE, 'compose', 'haproxy-1_6.cfg')
                env['HAPROXY_SOCKET_DIR'] = temp_dir

                with docker_run(
                    compose_file=os.path.join(HERE, 'compose', 'haproxy.yaml'),
                    env_vars=env,
                    service_name="haproxy",
                    conditions=[WaitFor(wait_for_haproxy)],
                ):
                    try:
                        # on linux this needs access to the socket
                        # it won't work without access
                        chown_args = []
                        user = getpass.getuser()

                        if user != 'root':
                            chown_args += ['sudo']
                        chown_args += ["chown", user, host_socket_path]
                        subprocess.check_call(chown_args, env=env)
                    except subprocess.CalledProcessError:
                        # it's not always bad if this fails
                        pass
                    config = deepcopy(CHECK_CONFIG)
                    unixsocket_url = 'unix://{0}'.format(host_socket_path)
                    config['unixsocket_url'] = unixsocket_url
                    yield {'instances': [config, CONFIG_TCPSOCKET]}
        else:
            yield deepcopy(CHECK_CONFIG_OPEN)


@pytest.fixture
def check():
    return lambda instance: HAProxy('haproxy', {}, [instance])


@pytest.fixture
def instance():
    instance = deepcopy(CHECK_CONFIG)
    return instance


@pytest.fixture(scope="module")
def haproxy_mock():
    filepath = os.path.join(HERE, 'fixtures', 'mock_data')
    with open(filepath, 'rb') as f:
        data = f.read()
    p = mock.patch('requests.get', return_value=mock.Mock(content=data))
    yield p.start()
    p.stop()


@pytest.fixture(scope="module")
def haproxy_mock_evil():
    filepath = os.path.join(HERE, 'fixtures', 'mock_data_evil')
    with open(filepath, 'rb') as f:
        data = f.read()
    p = mock.patch('requests.get', return_value=mock.Mock(content=data))
    yield p.start()
    p.stop()


@pytest.fixture(scope="session")
def version_metadata():
    # some version has release info
    parts = HAPROXY_VERSION.split('-')
    major, minor, patch = parts[0].split('.')
    if len(parts) > 1:
        release = parts[1]
        return {
            'version.scheme': 'semver',
            'version.major': major,
            'version.minor': minor,
            'version.patch': patch,
            'version.raw': mock.ANY,
            'version.release': release,
        }
    else:
        return {
            'version.scheme': 'semver',
            'version.major': major,
            'version.minor': minor,
            'version.patch': patch,
            'version.raw': mock.ANY,
        }
