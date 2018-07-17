import pytest
import os
import subprocess
import requests
import time
import logging
import mock
import tempfile
import shutil
import getpass

import common

log = logging.getLogger('test_haproxy')


@pytest.fixture
def aggregator():
    from datadog_checks.stubs import aggregator
    aggregator.reset()
    return aggregator


@pytest.fixture(scope="module")
def haproxy_mock():
    filepath = os.path.join(common.HERE, 'fixtures', 'mock_data')
    with open(filepath, 'r') as f:
        data = f.read()
    p = mock.patch('requests.get', return_value=mock.Mock(content=data))
    yield p.start()
    p.stop()


@pytest.fixture(scope="module")
def haproxy_mock_evil():
    filepath = os.path.join(common.HERE, 'fixtures', 'mock_data_evil')
    with open(filepath, 'r') as f:
        data = f.read()
    p = mock.patch('requests.get', return_value=mock.Mock(content=data))
    yield p.start()
    p.stop()


def wait_for_haproxy():
    for _ in xrange(0, 100):
        res = None
        res_open = None
        try:
            auth = (common.USERNAME, common.PASSWORD)
            res = requests.get(common.STATS_URL, auth=auth)
            res.raise_for_status()
            res_open = requests.get(common.STATS_URL_OPEN)
            res_open.raise_for_status()
            return
        except Exception as e:
            log.info("exception: {0} res: {1} res_open: {2}".format(e, res, res_open))
            time.sleep(2)
    raise Exception("Cannot start up apache")


@pytest.fixture(scope="session")
def haproxy_container():
    try:
        env = os.environ
        host_socket_dir = os.path.realpath(tempfile.mkdtemp())
        host_socket_path = os.path.join(host_socket_dir, 'datadog-haproxy-stats.sock')

        env['HAPROXY_CONFIG_DIR'] = os.path.join(common.HERE, 'compose')
        env['HAPROXY_CONFIG'] = os.path.join(common.HERE, 'compose', 'haproxy.cfg')
        env['HAPROXY_CONFIG_OPEN'] = os.path.join(common.HERE, 'compose', 'haproxy-open.cfg')
        env['HAPROXY_SOCKET_DIR'] = host_socket_dir

        args = [
            "docker-compose",
            "-f", os.path.join(common.HERE, 'compose', 'haproxy.yaml')
        ]
        subprocess.check_call(args + ["down"], env=env)
        subprocess.check_call(args + ["up", "-d"], env=env)
        wait_for_haproxy()
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
        time.sleep(20)
        yield host_socket_path
        subprocess.check_call(args + ["down"], env=env)
    finally:
        shutil.rmtree(host_socket_dir, ignore_errors=True)
