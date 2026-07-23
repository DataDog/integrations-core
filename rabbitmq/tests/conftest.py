# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import base64
import os
import subprocess
from urllib import request

import pytest

from datadog_checks.dev import docker_run, temp_dir
from datadog_checks.rabbitmq import RabbitMQ

from .common import CHECK_NAME, CONFIG, HERE, HOST, OPENMETRICS_CONFIG, PORT, RABBITMQ_METRICS_PLUGIN


def basic_auth_header(username: str, password: str) -> str:
    token = base64.b64encode(f'{username}:{password}'.encode('latin1')).decode('ascii')
    return f'Basic {token}'


@pytest.fixture(scope="session")
def dd_environment():
    """
    Start a cluster with one master, one replica and one unhealthy replica and
    stop it after the tests are done.
    If there's any problem executing `docker compose`, let the exception bubble
    up.
    """

    if 'RABBITMQ_VERSION' not in os.environ:
        pytest.exit('RABBITMQ_VERSION not available')

    compose_file = os.path.join(HERE, 'compose', 'docker-compose.yaml')

    with docker_run(compose_file, log_patterns='Server startup complete', conditions=[setup_rabbitmq], sleep=5):
        if RABBITMQ_METRICS_PLUGIN == "prometheus":
            yield OPENMETRICS_CONFIG
        else:
            yield CONFIG


def setup_rabbitmq():
    with temp_dir() as tmpdir:
        url = 'http://{}:{}/cli/rabbitmqadmin'.format(HOST, PORT)
        with request.urlopen(url) as res:
            rabbitmq_admin = res.read().decode()

        rabbitmq_admin_script = os.path.join(tmpdir, 'rabbitmqadmin')
        with open(rabbitmq_admin_script, 'w+') as f:
            f.write(rabbitmq_admin)

        setup_vhosts(rabbitmq_admin_script)
        setup_more(rabbitmq_admin_script)
        setup_more_with_vhosts(rabbitmq_admin_script)

        # Set cluster name
        url = "http://{}:{}/api/cluster-name".format(HOST, PORT)
        req = request.Request(
            url,
            data=b'{"name": "rabbitmqtest"}',
            headers={"Authorization": basic_auth_header("guest", "guest"), "Content-Type": "application/json"},
            method='PUT',
        )
        with request.urlopen(req):
            pass


def setup_vhosts(rabbitmq_admin_script):
    for vhost in ['myvhost', 'myothervhost']:
        cmd = ['python', rabbitmq_admin_script, '-H', HOST, 'declare', 'vhost', 'name={}'.format(vhost)]
        subprocess.check_call(cmd)

        cmd = [
            'python',
            rabbitmq_admin_script,
            '-H',
            HOST,
            'declare',
            'permission',
            'vhost={}'.format(vhost),
            'user=guest',
            'write=.*',
            'read=.*',
            'configure=.*',
        ]
        subprocess.check_call(cmd)


def setup_more(rabbitmq_admin_script):
    for name in ['test1', 'test5', 'tralala']:
        cmd = ['python', rabbitmq_admin_script, '-H', HOST, 'declare', 'queue', 'name={}'.format(name)]
        subprocess.check_call(cmd)

        cmd = ['python', rabbitmq_admin_script, '-H', HOST, 'declare', 'exchange', 'name={}'.format(name), 'type=topic']
        subprocess.check_call(cmd)

        cmd = [
            'python',
            rabbitmq_admin_script,
            '-H',
            HOST,
            'declare',
            'binding',
            'source={}'.format(name),
            'destination_type=queue',
            'destination={}'.format(name),
            'routing_key={}'.format(name),
        ]
        subprocess.check_call(cmd)

        cmd = [
            'python',
            rabbitmq_admin_script,
            '-H',
            HOST,
            'publish',
            'exchange={}'.format(name),
            'routing_key={}'.format(name),
            'payload="hello, world"',
            'properties={"timestamp": 1500000}',
        ]
        subprocess.check_call(cmd)

        cmd = [
            'python',
            rabbitmq_admin_script,
            '-H',
            HOST,
            'publish',
            'exchange={}'.format(name),
            'routing_key=bad_key',
            'payload="unroutable"',
            'properties={"timestamp": 1500000}',
        ]
        subprocess.check_call(cmd)


def setup_more_with_vhosts(rabbitmq_admin_script):
    for name in ['test1', 'test5', 'tralala', 'testaaaaa', 'bbbbbbbb']:
        for vhost in ['myvhost', 'myothervhost']:
            cmd = [
                'python',
                rabbitmq_admin_script,
                '-H',
                HOST,
                '--vhost={}'.format(vhost),
                'declare',
                'queue',
                'name={}'.format(name),
            ]
            subprocess.check_call(cmd)

            cmd = [
                'python',
                rabbitmq_admin_script,
                '-H',
                HOST,
                '--vhost={}'.format(vhost),
                'publish',
                'exchange=amq.default',
                'routing_key={}'.format(name),
                'payload="hello, world"',
                'properties={"timestamp": 1500000}',
            ]
            subprocess.check_call(cmd)


@pytest.fixture
def check():
    return RabbitMQ(CHECK_NAME, {}, [CONFIG])


@pytest.fixture
def instance():
    return CONFIG


# We don't want to maintain compatibility with Py2 in our OpenMetrics tests. If we are testing the management plugin
# which still supports Py2, we don't load the test files at all. Docs for how we do it:
# https://docs.pytest.org/en/7.1.x/example/pythoncollection.html#customizing-test-collection
collect_ignore_glob = []
if RABBITMQ_METRICS_PLUGIN == "management":
    collect_ignore_glob.append("*openmetrics*")
