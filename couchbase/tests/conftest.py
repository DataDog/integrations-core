# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os
import subprocess
from copy import deepcopy

import pytest
import requests

from datadog_checks.dev import WaitFor, docker_run
from datadog_checks.dev.docker import get_container_ip

from .common import (
    BUCKET_NAME,
    CB_CONTAINER_NAME,
    CUSTOM_TAGS,
    DEFAULT_INSTANCE,
    HERE,
    PASSWORD,
    PORT,
    QUERY_URL,
    SG_URL,
    URL,
    USER,
)


@pytest.fixture
def instance():
    return deepcopy(DEFAULT_INSTANCE)


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


@pytest.fixture
def instance_sg():
    return {
        'server': URL,
        'user': USER,
        'password': PASSWORD,
        'timeout': 0.5,
        'tags': CUSTOM_TAGS,
        'sync_gateway_url': SG_URL,
    }


@pytest.fixture(scope="session")
def dd_environment():
    """
    Spin up and initialize couchbase
    """

    with docker_run(
        compose_file=os.path.join(HERE, 'compose', 'standalone.compose'),
        env_vars={'CB_CONTAINER_NAME': CB_CONTAINER_NAME},
        conditions=[
            WaitFor(couchbase_container),
            WaitFor(couchbase_init),
            WaitFor(couchbase_setup),
            WaitFor(node_stats),
            WaitFor(bucket_stats),
        ],
    ):
        yield DEFAULT_INSTANCE


@pytest.fixture()
def couchbase_container_ip():
    """
    Modular fixture that depends on couchbase being initialized
    """
    return get_container_ip(CB_CONTAINER_NAME)


def couchbase_setup():
    """
    Setup couchbase using its CLI tool
    """

    # Resources used:
    #   https://developer.couchbase.com/documentation/server/5.1/install/init-setup.html

    # create bucket
    create_bucket_args = [
        'docker',
        'exec',
        CB_CONTAINER_NAME,
        'couchbase-cli',
        'bucket-create',
        '-c',
        'localhost:{}'.format(PORT),
        '-u',
        USER,
        '-p',
        PASSWORD,
        '--bucket',
        BUCKET_NAME,
        '--bucket-type',
        'couchbase',
        '--bucket-ramsize',
        '100',
    ]
    subprocess.check_call(create_bucket_args)


def couchbase_container():
    """
    Wait for couchbase to start
    """
    status_args = [
        'docker',
        'exec',
        CB_CONTAINER_NAME,
        'couchbase-cli',
        'server-info',
        '-c',
        'localhost:{}'.format(PORT),
        '-u',
        USER,
        '-p',
        PASSWORD,
    ]
    return subprocess.call(status_args) == 0


def couchbase_init():
    """
    Wait for couchbase to be initialized
    """

    # initialize the database
    init_args = [
        'docker',
        'exec',
        CB_CONTAINER_NAME,
        'couchbase-cli',
        'cluster-init',
        '-c',
        'localhost:{}'.format(PORT),
        '--cluster-username={}'.format(USER),
        '--cluster-password={}'.format(PASSWORD),
        '--services',
        'data,index,fts,query',
        '--cluster-ramsize',
        '256',
        '--cluster-index-ramsize',
        '256',
        '--cluster-fts-ramsize',
        '256',
    ]
    subprocess.check_call(init_args)

    r = requests.get('{}/pools/default'.format(URL), auth=(USER, PASSWORD))
    return r.status_code == requests.codes.ok


def node_stats():
    """
    Wait for couchbase to generate node stats
    """
    r = requests.get('{}/pools/default'.format(URL), auth=(USER, PASSWORD))
    r.raise_for_status()
    stats = r.json()
    return all(len(node_stats['interestingStats']) > 0 for node_stats in stats['nodes'])


def bucket_stats():
    """
    Wait for couchbase to generate bucket stats
    """
    r = requests.get('{}/pools/default/buckets/{}/stats'.format(URL, BUCKET_NAME), auth=(USER, PASSWORD))
    r.raise_for_status()
    stats = r.json()
    return stats['op']['lastTStamp'] != 0
