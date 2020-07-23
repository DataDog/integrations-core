# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os
import subprocess

import pytest
import requests

from datadog_checks.dev import docker_run, temp_dir
from datadog_checks.rabbitmq import RabbitMQ

from .common import CHECK_NAME, CONFIG, HERE, HOST, PORT


@pytest.fixture(scope="session")
def dd_environment():
    """
    Start a cluster with one master, one replica and one unhealthy replica and
    stop it after the tests are done.
    If there's any problem executing docker-compose, let the exception bubble
    up.
    """

    env = {}

    if 'RABBITMQ_VERSION' not in os.environ:
        pytest.exit('RABBITMQ_VERSION not available')

    compose_file = os.path.join(HERE, 'compose', 'docker-compose.yaml')

    with docker_run(
        compose_file, log_patterns='Server startup complete', env_vars=env, conditions=[setup_rabbitmq], sleep=5
    ):
        yield CONFIG


def setup_rabbitmq():
    with temp_dir() as tmpdir:
        url = 'http://{}:{}/cli/rabbitmqadmin'.format(HOST, PORT)
        res = requests.get(url)
        res.raise_for_status()

        rabbitmq_admin_script = os.path.join(tmpdir, 'rabbitmqadmin')
        with open(rabbitmq_admin_script, 'w+') as f:
            f.write(res.text)

        setup_vhosts(rabbitmq_admin_script)
        setup_more(rabbitmq_admin_script)
        setup_more_with_vhosts(rabbitmq_admin_script)

        # Set cluster name
        url = "http://{}:{}/api/cluster-name".format(HOST, PORT)
        res = requests.put(
            url, data='{"name": "rabbitmqtest"}', auth=("guest", "guest"), headers={"Content-Type": "application/json"}
        )
        res.raise_for_status()


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
