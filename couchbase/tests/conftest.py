# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os
import subprocess
from time import sleep

import pytest
import requests

from common import (
    HERE, HOST, PORT, DATA_PORT, SYSTEM_VITALS_PORT,
    URL, TAGS, BUCKET_NAME,
    USER, PASSWORD
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


@pytest.fixture
def couchbase_query_config():
    return {
            'server': URL,
            'user': USER,
            'password': PASSWORD,
            'timeout': 0.5,
            'tags': TAGS,
            'query_monitoring_url': 'http://{0}:{1}'.format(HOST, SYSTEM_VITALS_PORT)
    }


def setup_couchbase():
    '''
    Initialize couchbase using its CLI tool
    '''

    # Resources used:
    #   https://developer.couchbase.com/documentation/server/5.1/install/init-setup.html
    args = [
        'docker', 'exec',
        'couchbase-standalone'
    ]

    # initialize the database
    init_args = args + [
        'couchbase-cli', 'cluster-init', '-c', 'localhost:{0}'.format(PORT),
        '--cluster-username={0}'.format(USER), '--cluster-password={0}'.format(PASSWORD),
        '--services', 'data,index,fts,query',
        '--cluster-ramsize', '256', '--cluster-index-ramsize', '256', '--cluster-fts-ramsize', '256'
    ]
    subprocess.check_call(init_args)
    if not wait_for_couchbase_init():
        raise Exception("couchbase initialization timed out!")

    # create bucket
    create_bucket_args = args + [
        'couchbase-cli', 'bucket-create', '-c', 'localhost:{0}'.format(PORT),
        '-u', USER, '-p', PASSWORD,
        '--bucket', BUCKET_NAME, '--bucket-type', 'couchbase', '--bucket-ramsize', '100'
    ]
    subprocess.check_call(create_bucket_args)
    if not wait_for_bucket(BUCKET_NAME):
        raise Exception("couchbase bucket creation timed out!")

    # time for couchbase to generate stats that we can collect
    sleep(30)


def wait_for_couchbase_container():
    '''
    Wait for couchbase to start
    '''
    for i in xrange(80):
        status_args = [
            'docker', 'exec',
            'couchbase-standalone',
            'couchbase-cli', 'server-info', '-c', 'localhost:{0}'.format(PORT),
            '-u', USER, '-p', PASSWORD
        ]

        if subprocess.call(status_args) == 0:
            print("Container started after {0} seconds".format(str(i)))
            return True
        else:
            sleep(1)

    return False


def wait_for_couchbase_init():
    '''
    Wait for couchbase to be initialized
    '''
    for i in xrange(100):
        r = requests.get('{0}/pools/default'.format(URL), auth=(USER, PASSWORD))
        if r.status_code == requests.codes.ok:
            return True
        else:
            sleep(1)

    return False


def wait_for_bucket(bucket_name):
    '''
    Wait for couchbase bucket to be created
    '''
    for i in xrange(80):
        status_args = [
            'docker', 'exec',
            'couchbase-standalone',
            'cbstats', 'localhost:{0}'.format(DATA_PORT),
            '-b', bucket_name,
            'uuid', '-u', USER, '-p', PASSWORD
        ]

        if subprocess.call(status_args) == 0:
            return True
        else:
            sleep(1)

    return False
