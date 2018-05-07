# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os
import subprocess
from time import sleep

import pytest
import requests

from common import (
    HERE, HOST, DATA_PORT, URL, TAGS, USER, PASSWORD, BUCKET_NAME
)


@pytest.fixture
def aggregator():
    from datadog_checks.stubs import aggregator
    aggregator.reset()
    return aggregator


@pytest.fixture(scope="session")
def couchbase_metrics():
    args = [
        'docker-compose',
        '-f', os.path.join(HERE, 'compose', 'standalone.compose')
    ]

    subprocess.check_call(args + ['up', '-d'])

    # wait for couchbase to be up
    if not wait_for_couchbase_container():
        raise Exception("couchbase container boot timed out!")

    # set up couchbase through its cli
    setup_couchbase()

    yield

    subprocess.check_call(args + ["down"])


@pytest.fixture
def couchbase_config():
    return {
            'server': URL,
            'user': USER,
            'password': PASSWORD,
            'timeout': 0.5,
            'tags': TAGS
    }


# set up couchbase through couchbase-cli
def setup_couchbase():
    # Resources used:
    #   https://developer.couchbase.com/documentation/server/5.1/install/init-setup.html
    args = [
        'docker', 'exec',
        'couchbase-standalone'
    ]

    # initialize the database
    init_args = args + [
        'couchbase-cli', 'cluster-init', '-c', URL,
        '--cluster-username={0}'.format(USER), '--cluster-password={0}'.format(PASSWORD),
        '--services', 'data,index,fts,query',
        '--cluster-ramsize', '256', '--cluster-index-ramsize', '256', '--cluster-fts-ramsize', '256'
    ]
    subprocess.check_call(init_args)
    if not wait_for_couchbase_init():
        raise Exception("couchbase initialization timed out!")

    # create bucket
    create_bucket_args = args + [
        'couchbase-cli', 'bucket-create', '-c', URL,
        '-u', USER, '-p', PASSWORD,
        '--bucket', BUCKET_NAME, '--bucket-type', 'couchbase', '--bucket-ramsize', '100'
    ]
    subprocess.check_call(create_bucket_args)
    if not wait_for_bucket(BUCKET_NAME):
        raise Exception("couchbase bucket creation timed out!")

    # time for couchbase to generate stats that we can collect
    sleep(45)


# wait for couchbase to start
def wait_for_couchbase_container():
    for i in xrange(60):
        status_args = [
            'docker', 'exec',
            'couchbase-standalone',
            'couchbase-cli', 'server-info', '-c', URL,
            '-u', USER, '-p', PASSWORD
        ]

        if subprocess.call(status_args) == 0:
            return True
        else:
            sleep(1)

    return False


# wait for couchbase to initialize
def wait_for_couchbase_init():
    for i in xrange(60):
        r = requests.get('{0}/pools/default'.format(URL), auth=(USER, PASSWORD))
        if r.status_code == requests.codes.ok:
            return True
        else:
            sleep(1)

    return False


# wait for couchbase to create the 'default' bucket
def wait_for_bucket(bucket_name):
    for i in xrange(60):
        status_args = [
            'docker', 'exec',
            'couchbase-standalone',
            'cbstats', '{0}:{1}'.format(HOST, DATA_PORT),
            '-b', bucket_name,
            'uuid', '-u', USER, '-p', PASSWORD
        ]

        if subprocess.call(status_args) == 0:
            return True
        else:
            sleep(1)

    return False
