# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import bmemcached
import pytest

from datadog_checks.dev import TempDir, WaitFor, docker_run
from datadog_checks.mcache import Memcache

from .common import (
    DOCKER_SOCKET_DIR,
    DOCKER_SOCKET_PATH,
    HERE,
    HOST,
    PASSWORD,
    PORT,
    USERNAME,
    platform_supports_sockets,
)
from .utils import get_host_socket_path


def connect_to_mcache(*client_args):
    client = bmemcached.Client(*client_args)

    try:
        client.set('foo', 'bar')
        client.delete('foo')
    finally:
        client.disconnect_all()


@pytest.fixture(scope='session')
def dd_environment(e2e_instance):
    with docker_run(
        os.path.join(HERE, 'compose', 'docker-compose.yaml'),
        service_name='memcached',
        env_vars={'PWD': HERE},
        conditions=[WaitFor(connect_to_mcache, args=(['{}:{}'.format(HOST, PORT)], USERNAME, PASSWORD))],
    ):
        if platform_supports_sockets:
            with TempDir() as temp_dir:
                host_socket_path = os.path.join(temp_dir, 'memcached.sock')

                if not os.path.exists(host_socket_path):
                    os.chmod(temp_dir, 0o777)

                with docker_run(
                    os.path.join(HERE, 'compose', 'docker-compose.yaml'),
                    service_name='memcached_socket',
                    env_vars={
                        'DOCKER_SOCKET_DIR': DOCKER_SOCKET_DIR,
                        'DOCKER_SOCKET_PATH': DOCKER_SOCKET_PATH,
                        'HOST_SOCKET_DIR': temp_dir,
                        'HOST_SOCKET_PATH': host_socket_path,
                    },
                    conditions=[WaitFor(connect_to_mcache, args=(host_socket_path, USERNAME, PASSWORD))],
                    # Don't worry about spinning down since the outermost runner will already do that
                    down=lambda: None,
                ):
                    yield e2e_instance
        else:
            yield e2e_instance


@pytest.fixture(scope='session')
def dd_environment_ipv6(instance_ipv6):
    with docker_run(
        os.path.join(HERE, 'compose', 'docker-compose.yaml'),
        service_name='memcached_ipv6',
        env_vars={'PWD': HERE},
        conditions=[WaitFor(connect_to_mcache, args=(['{}:{}'.format('[2001:db8::2]', PORT)], USERNAME, PASSWORD))],
    ):
        yield instance_ipv6


@pytest.fixture
def client():
    return bmemcached.Client(["{}:{}".format(HOST, PORT)], USERNAME, PASSWORD)


@pytest.fixture
def client_socket():
    return bmemcached.Client(get_host_socket_path(), USERNAME, PASSWORD)


@pytest.fixture
def check():
    return Memcache('mcache', None, {}, [{}])


@pytest.fixture
def instance():
    return {'url': HOST, 'port': PORT, 'tags': ['foo:bar'], 'username': USERNAME, 'password': PASSWORD}


@pytest.fixture(scope='session')
def e2e_instance():
    return {'url': HOST, 'port': PORT, 'tags': ['foo:bar'], 'username': USERNAME, 'password': PASSWORD}


@pytest.fixture
def instance_socket():
    return {'socket': get_host_socket_path(), 'tags': ['foo:bar'], 'username': USERNAME, 'password': PASSWORD}


@pytest.fixture(scope='session')
def instance_ipv6():
    # This IPv6 address is defined in the docker-compose file.
    return {'url': '2001:db8::2', 'port': PORT, 'tags': ['foo:bar'], 'username': USERNAME, 'password': PASSWORD}
