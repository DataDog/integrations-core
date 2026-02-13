# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os
import subprocess
import time
from copy import deepcopy

import pytest
import requests

from datadog_checks.couchbase import Couchbase
from datadog_checks.dev import WaitFor, docker_run
from datadog_checks.dev.docker import get_container_ip
from datadog_checks.dev.http import MockResponse

from .common import (
    BUCKET_NAME,
    CB_CONTAINER_NAME,
    COUCHBASE_MAJOR_VERSION,
    COUCHBASE_METRIC_SOURCE,
    COUCHBASE_MINOR_VERSION,
    COUCHBASE_SYNCGW_MAJOR_VERSION,
    COUCHBASE_SYNCGW_MINOR_VERSION,
    DEFAULT_INSTANCE,
    HERE,
    INDEX_STATS_URL,
    PASSWORD,
    PORT,
    PROMETHEUS_INSTANCE,
    QUERY_URL,
    SG_URL,
    URL,
    USER,
)


@pytest.fixture
def instance():
    if COUCHBASE_METRIC_SOURCE == "prometheus":
        return deepcopy(PROMETHEUS_INSTANCE)
    return deepcopy(DEFAULT_INSTANCE)


@pytest.fixture
def rest_instance():
    return deepcopy(DEFAULT_INSTANCE)


@pytest.fixture
def prometheus_instance():
    return deepcopy(PROMETHEUS_INSTANCE)


@pytest.fixture
def instance_query(rest_instance):
    rest_instance['query_monitoring_url'] = QUERY_URL
    return rest_instance


@pytest.fixture
def instance_sg(rest_instance):
    rest_instance['sync_gateway_url'] = SG_URL
    return rest_instance


@pytest.fixture
def instance_index_stats(rest_instance):
    rest_instance['index_stats_url'] = INDEX_STATS_URL
    return rest_instance


@pytest.fixture
def check():
    return lambda instance: Couchbase('couchbase', {}, [instance])


@pytest.fixture(scope="session")
def dd_environment():
    """
    Spin up and initialize couchbase
    """
    conditions = [
        WaitFor(couchbase_container),
        WaitFor(couchbase_init),
        WaitFor(couchbase_setup),
        WaitFor(node_stats),
        WaitFor(bucket_stats),
        WaitFor(load_sample_bucket),
        WaitFor(create_syncgw_database),
    ]
    with docker_run(
        compose_file=os.path.join(HERE, 'compose', 'docker-compose.yaml'),
        env_vars={
            'CB_CONTAINER_NAME': CB_CONTAINER_NAME,
            'CB_USERNAME': USER,
            'CB_PASSWORD': PASSWORD,
        },
        conditions=conditions,
        sleep=15,
    ):
        if COUCHBASE_METRIC_SOURCE == "prometheus":
            yield deepcopy(PROMETHEUS_INSTANCE)
        else:
            yield deepcopy(DEFAULT_INSTANCE)


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

    with open(os.devnull, 'w') as FNULL:
        subprocess.check_call(create_bucket_args, stdout=FNULL)


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

    with open(os.devnull, 'w') as FNULL:
        return subprocess.call(status_args, stdout=FNULL) == 0


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
        '512',
        '--cluster-index-ramsize',
        '256',
        '--cluster-fts-ramsize',
        '256',
    ]
    subprocess.check_call(init_args)

    r = requests.get('{}/pools/default'.format(URL), auth=(USER, PASSWORD))
    return r.status_code == requests.codes.ok


def load_sample_bucket():
    """
    Load sample data bucket
    """

    # Resources used:
    # https://docs.couchbase.com/server/current/manage/manage-settings/install-sample-buckets.html

    r = requests.post(
        '{}/sampleBuckets/install'.format(URL),
        auth=(USER, PASSWORD),
        json=["gamesim-sample"],
    )
    if r.status_code == 400:
        if "Sample bucket gamesim-sample is already loaded" in r.text:
            return True
        return False

    r.raise_for_status()
    result = r.json()

    if COUCHBASE_MAJOR_VERSION == 7 and COUCHBASE_MINOR_VERSION > 6:
        # Couchbase versions > 7.6 return an empty list on completion.
        return len(result) == 0

    # Couchbase version 7.6 returns a task ID that we have to check for
    # completion.
    task_id = None
    for task in result["tasks"]:
        if task["sample"] == "gamesim-sample":
            task_id = task["taskId"]

    while True:
        # Loop until the task ID is gone, meaning the task is done.
        task_is_done = False

        r = requests.get(
            '{}/pools/default/tasks'.format(URL),
            auth=(USER, PASSWORD),
        )
        r.raise_for_status()
        result = r.json()

        for task in result:
            if task.get("task_id", "") == task_id:
                task_is_done = True

        if task_is_done:
            break

        time.sleep(1)

    return True


def create_syncgw_database():
    """
    Create sample database
    """

    # Resources used:
    # https://docs.couchbase.com/sync-gateway/current/configuration/configuration-schema-database.html

    payload = {
        "bucket": "gamesim-sample",
        "num_index_replicas": 0,
    }

    # The payload format is different between Sync Gateway versions: The
    # num_index_replicas field was deprecated in favor of index.num_replicas in
    # version 3.3.0.
    if COUCHBASE_SYNCGW_MAJOR_VERSION == 3 and COUCHBASE_SYNCGW_MINOR_VERSION >= 3:
        payload["index"] = {"num_replicas": payload["num_index_replicas"]}
        del payload["num_index_replicas"]

    r = requests.put(
        '{}/sync_gateway/'.format(SG_URL),
        auth=(USER, PASSWORD),
        json=payload,
    )
    r.raise_for_status()


def node_stats():
    """
    Wait for couchbase to generate node stats
    """
    r = requests.get('{}/pools/default'.format(URL), auth=(USER, PASSWORD))
    r.raise_for_status()
    stats = r.json()
    return all(len(stats['interestingStats']) > 0 for stats in stats['nodes'])


def bucket_stats():
    """
    Wait for couchbase to generate bucket stats
    """
    r = requests.get('{}/pools/default/buckets/{}/stats'.format(URL, BUCKET_NAME), auth=(USER, PASSWORD))
    r.raise_for_status()
    stats = r.json()
    return stats['op']['lastTStamp'] != 0


def mock_http_responses(url, **_params):
    mapping = {
        'http://localhost:8091/pools/default': 'pools/default/default.json',
        'http://localhost:8091/pools/default/buckets?v=62866031&uuid=f66f28b255e70b6f2618c15228238797': 'pools/default/buckets.json',  # noqa
        'http://localhost:8091/pools/default/buckets/cb_bucket/stats': 'pools/default/buckets/cb_buckets/stats.json',
        'http://localhost:8091/pools/default/tasks': 'pools/default/tasks.json',
        'http://localhost:8093/admin/vitals': 'admin/vitals.json',
    }

    metrics_file = mapping.get(url)

    if not metrics_file:
        pytest.fail("url `{url}` not registered".format(url=url))

    with open(os.path.join(HERE, 'fixtures', metrics_file)) as f:
        return MockResponse(content=f.read())
