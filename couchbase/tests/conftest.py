# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os
import subprocess
from time import sleep

import pytest
import requests

from datadog_checks.dev.docker import get_container_ip

from .common import HERE, HOST, PORT, QUERY_PORT, BUCKET_NAME, CUSTOM_TAGS

URL = 'http://{}:{}'.format(HOST, PORT)
QUERY_URL = 'http://{}:{}'.format(HOST, QUERY_PORT)
CB_CONTAINER_NAME = 'couchbase-standalone'
USER = 'Administrator'
PASSWORD = 'password'


@pytest.fixture
def instance():
    return {
        'server': URL,
        'user': USER,
        'password': PASSWORD,
        'timeout': 0.5,
        'tags': CUSTOM_TAGS,
    }


@pytest.fixture
def instance_query():
    return {
        'server': URL,
        'user': USER,
        'password': PASSWORD,
        'timeout': 0.5,
        'tags': CUSTOM_TAGS,
        'query_monitoring_url': QUERY_URL,
    }


@pytest.fixture(scope="session")
def couchbase_service(request):
    """
    Spin up and initialize couchbase
    """

    # specify couchbase container name
    env = os.environ
    env['CB_CONTAINER_NAME'] = CB_CONTAINER_NAME

    args = [
        'docker-compose',
        '-f', os.path.join(HERE, 'compose', 'standalone.compose')
    ]

    # always stop and remove the container even if there's an exception at setup
    def teardown():
        subprocess.check_call(args + ["down"], env=env)
    request.addfinalizer(teardown)

    # spin up the docker container
    subprocess.check_call(args + ['up', '-d'], env=env)

    # wait for couchbase to be up
    if not wait_for_couchbase_container(CB_CONTAINER_NAME):
        raise Exception("couchbase container boot timed out!")

    # set up couchbase through its cli
    setup_couchbase()

    # we need to wait for couchbase to generate stats
    if not wait_for_node_stats():
        raise Exception("couchbase node stats timed out!")

    if not wait_for_bucket_stats(BUCKET_NAME):
        raise Exception("couchbase bucket stats timed out!")

    yield


@pytest.fixture()
def couchbase_container_ip(couchbase_service):
    """
    Modular fixture that depends on couchbase being initialized
    """
    return get_container_ip(CB_CONTAINER_NAME)


def setup_couchbase():
    """
    Initialize couchbase using its CLI tool
    """

    # Resources used:
    #   https://developer.couchbase.com/documentation/server/5.1/install/init-setup.html
    args = [
        'docker', 'exec', CB_CONTAINER_NAME
    ]

    # initialize the database
    init_args = args + [
        'couchbase-cli', 'cluster-init', '-c', 'localhost:{}'.format(PORT),
        '--cluster-username={}'.format(USER), '--cluster-password={}'.format(PASSWORD),
        '--services', 'data,index,fts,query',
        '--cluster-ramsize', '256', '--cluster-index-ramsize', '256', '--cluster-fts-ramsize', '256'
    ]
    subprocess.check_call(init_args)

    if not wait_for_couchbase_init():
        raise Exception("couchbase initialization timed out!")

    # create bucket
    create_bucket_args = args + [
        'couchbase-cli', 'bucket-create', '-c', 'localhost:{}'.format(PORT),
        '-u', USER, '-p', PASSWORD,
        '--bucket', BUCKET_NAME, '--bucket-type', 'couchbase', '--bucket-ramsize', '100'
    ]
    subprocess.check_call(create_bucket_args)


def wait_for_couchbase_container(container_name):
    """
    Wait for couchbase to start
    """

    for i in xrange(15):
        status_args = [
            'docker', 'exec', container_name,
            'couchbase-cli', 'server-info', '-c', 'localhost:{}'.format(PORT),
            '-u', USER, '-p', PASSWORD
        ]

        if subprocess.call(status_args) == 0:
            return True
        else:
            sleep(1)

    return False


def wait_for_couchbase_init():
    """
    Wait for couchbase to be initialized
    """

    for i in xrange(15):
        r = requests.get('{}/pools/default'.format(URL), auth=(USER, PASSWORD))
        if r.status_code == requests.codes.ok:
            return True

    return False


def wait_for_node_stats():
    """
    Wait for couchbase to generate node stats
    """
    for i in xrange(15):
        try:
            r = requests.get('{}/pools/default'.format(URL), auth=(USER, PASSWORD))
            r.raise_for_status()
            stats = r.json()
            if all(len(node_stats['interestingStats']) > 0 for node_stats in stats['nodes']):
                return True
        except Exception:
            pass

        sleep(1)

    return False


def wait_for_bucket_stats(bucket_name):
    """
    Wait for couchbase to generate bucket stats
    """
    for i in xrange(15):
        try:
            r = requests.get('{}/pools/default/buckets/{}/stats'.format(URL, bucket_name), auth=(USER, PASSWORD))
            r.raise_for_status()
            stats = r.json()
            if stats['op']['lastTStamp'] != 0:
                return True
        except Exception:
            pass

        sleep(1)

    return False
