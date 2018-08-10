# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import subprocess
import os
import tempfile
import shutil
import time
import pytest
import bmemcached
from bmemcached.exceptions import MemcachedException

from datadog_checks.mcache import Memcache

from common import (HERE, PORT, HOST, USERNAME, PASSWORD, DOCKER_SOCKET_DIR, DOCKER_SOCKET_PATH)


@pytest.fixture(scope="session")
def memcached():
    """
    Start a standalone Memcached server.
    """
    env = os.environ
    env['PWD'] = HERE
    docker_compose_file = os.path.join(HERE, 'compose', 'docker-compose.yaml')

    subprocess.check_call(["docker-compose", "-f", docker_compose_file, "up", "-d", "memcached"], env=env)
    attempts = 0
    while True:
        if attempts > 10:
            raise Exception("Memcached boot timed out!")

        mc = bmemcached.Client(["{}:{}".format(HOST, PORT)], USERNAME, PASSWORD)
        try:
            mc.set("foo", "bar")
        except MemcachedException:
            attempts += 1
            time.sleep(1)
        else:
            mc.delete("foo")
            mc.disconnect_all()
            break

    yield

    subprocess.check_call(["docker-compose", "-f", docker_compose_file, "down"])


@pytest.fixture(scope="session")
def memcached_socket():
    """
    Start a standalone Memcached server.
    """
    try:
        host_socket_dir = os.path.realpath(tempfile.mkdtemp())
        host_socket_path = os.path.join(host_socket_dir, 'memcached.sock')
        os.chmod(host_socket_dir, 0o777)

        env = os.environ
        env['PWD'] = HERE
        env['DOCKER_SOCKET_DIR'] = DOCKER_SOCKET_DIR
        env['DOCKER_SOCKET_PATH'] = DOCKER_SOCKET_PATH
        env['HOST_SOCKET_DIR'] = host_socket_dir

        docker_compose_file = os.path.join(HERE, 'compose', 'docker-compose.yaml')
        subprocess.check_call(["docker-compose", "-f", docker_compose_file, "down"])
        subprocess.check_call(["docker-compose", "-f", docker_compose_file, "up", "-d", "memcached_socket"], env=env)

        attempts = 0
        while True:
            if attempts > 10:
                raise Exception("Memcached boot timed out!")

            mc = bmemcached.Client(host_socket_path, USERNAME, PASSWORD)
            try:
                mc.set("foo", "bar")
            except MemcachedException:
                attempts += 1
                time.sleep(1)
            else:
                mc.delete("foo")
                mc.disconnect_all()
                break

        yield host_socket_dir, host_socket_path

        subprocess.check_call(["docker-compose", "-f", docker_compose_file, "down"])
    finally:
        shutil.rmtree(host_socket_dir, ignore_errors=True)


@pytest.fixture
def client():
    return bmemcached.Client(["{}:{}".format(HOST, PORT)], USERNAME, PASSWORD)


@pytest.fixture
def client_socket(memcached_socket):
    return bmemcached.Client(memcached_socket[1], USERNAME, PASSWORD)


@pytest.fixture
def check():
    return Memcache('mcache', None, {}, [{}])


@pytest.fixture
def instance():
    return {
        'url': "{}".format(HOST),
        'port': PORT,
        'tags': ["foo:bar"],
        'username': USERNAME,
        'password': PASSWORD,
    }


@pytest.fixture
def instance_socket(memcached_socket):
    return {
        'socket': memcached_socket[1],
        'tags': ["foo:bar"],
        'username': USERNAME,
        'password': PASSWORD,
    }


@pytest.fixture
def aggregator():
    from datadog_checks.stubs import aggregator
    aggregator.reset()
    return aggregator
