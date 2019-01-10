import pytest
import os
import subprocess
import requests
import time
import logging
import mock
import getpass

from copy import deepcopy

from datadog_checks.dev import TempDir, WaitFor, docker_run
from datadog_checks.dev.utils import create_file, file_exists
from datadog_checks.haproxy import HAProxy

from .common import HERE, CHECK_CONFIG, USERNAME, PASSWORD, STATS_URL, STATS_URL_OPEN

log = logging.getLogger('test_haproxy')


def wait_for_haproxy():
    res = None
    res_open = None
    try:
        auth = (USERNAME, PASSWORD)
        res = requests.get(STATS_URL, auth=auth)
        res.raise_for_status()
        res_open = requests.get(STATS_URL_OPEN)
        res_open.raise_for_status()
        return
    except Exception as e:
        log.info("exception: {0} res: {1} res_open: {2}".format(e, res, res_open))

    return False


@pytest.fixture(scope='session')
def dd_environment():
    env = os.environ
    with TempDir() as d:
        host_socket_path = os.path.join(d, 'datadog-haproxy-stats.sock')

        if not file_exists(host_socket_path):
            os.chmod(d, 0o770)
            create_file(host_socket_path)
            os.chmod(host_socket_path, 0o640)

        env['HAPROXY_CONFIG_DIR'] = os.path.join(HERE, 'compose')
        env['HAPROXY_CONFIG'] = os.path.join(HERE, 'compose', 'haproxy.cfg')
        if os.environ.get('HAPROXY_VERSION', '1.5.11').split('.')[:2] >= ['1', '7']:
            env['HAPROXY_CONFIG'] = os.path.join(HERE, 'compose', 'haproxy-1_7.cfg')
        env['HAPROXY_CONFIG_OPEN'] = os.path.join(HERE, 'compose', 'haproxy-open.cfg')
        env['HAPROXY_SOCKET_DIR'] = d

        with docker_run(
            compose_file=os.path.join(HERE, 'compose', 'haproxy.yaml'),
            env_vars=env,
            conditions=[WaitFor(wait_for_haproxy)],
        ):
            try:
                # on linux this needs access to the socket
                # it won't work without access
                chown_args = []
                user = getpass.getuser()
                chown_args += ["chown", user, host_socket_path]
                subprocess.check_call(chown_args, env=env)
            except subprocess.CalledProcessError:
                # it's not always bad if this fails
                pass
            time.sleep(20)
            config = deepcopy(CHECK_CONFIG)
            unixsocket_url = 'unix://{0}'.format(host_socket_path)
            config['url'] = unixsocket_url
            yield config


@pytest.fixture
def check():
    return HAProxy('haproxy', {}, {})


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
