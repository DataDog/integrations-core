# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import base64
import http.client
import json
import os
import subprocess
import time
import urllib.error
import urllib.request
from copy import deepcopy
from typing import Any

import pytest

from datadog_checks.couchbase import Couchbase
from datadog_checks.dev import WaitFor, docker_run
from datadog_checks.dev.docker import get_container_ip
from datadog_checks.dev.http import MockHTTPResponse

from .common import (
    BUCKET_NAME,
    CB_CONTAINER_NAME,
    COUCHBASE_MAJOR_VERSION,
    COUCHBASE_MINOR_VERSION,
    COUCHBASE_SYNCGW_MAJOR_VERSION,
    COUCHBASE_SYNCGW_MINOR_VERSION,
    DEFAULT_INSTANCE,
    HERE,
    INDEX_STATS_URL,
    PASSWORD,
    PORT,
    QUERY_URL,
    SG_URL,
    URL,
    USER,
)


class HttpResponse:
    def __init__(self, url: str, status_code: int, reason: str, content: bytes) -> None:
        self.url = url
        self.status_code = status_code
        self.reason = reason or http.client.responses.get(status_code, '')
        self.content = content

    @property
    def text(self) -> str:
        return self.content.decode('utf-8')

    def json(self) -> Any:
        return json.loads(self.text)

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise urllib.error.HTTPError(self.url, self.status_code, self.reason, http.client.HTTPMessage(), None)


def http_request(
    url: str,
    method: str = 'GET',
    *,
    auth: tuple[str, str] | None = None,
    json_data: Any = None,
) -> HttpResponse:
    request_headers = {}
    body = None
    if json_data is not None:
        body = json.dumps(json_data).encode('utf-8')
        request_headers['Content-Type'] = 'application/json'

    if auth is not None:
        username, password = auth
        token = base64.b64encode('{}:{}'.format(username, password).encode('utf-8')).decode('ascii')
        request_headers['Authorization'] = 'Basic {}'.format(token)

    req = urllib.request.Request(url, data=body, headers=request_headers, method=method)
    try:
        with urllib.request.urlopen(req) as response:
            return HttpResponse(url, response.getcode(), response.reason, response.read())
    except urllib.error.HTTPError as error:
        return HttpResponse(url, error.code, error.reason, error.read())


@pytest.fixture
def instance():
    return deepcopy(DEFAULT_INSTANCE)


@pytest.fixture
def instance_query(instance):
    instance['query_monitoring_url'] = QUERY_URL
    return instance


@pytest.fixture
def instance_sg(instance):
    instance['sync_gateway_url'] = SG_URL
    return instance


@pytest.fixture
def instance_index_stats(instance):
    instance['index_stats_url'] = INDEX_STATS_URL
    return instance


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
        WaitFor(gamesim_primary_index_ready),
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

    r = http_request('{}/pools/default'.format(URL), auth=(USER, PASSWORD))
    return r.status_code == http.client.OK


def load_sample_bucket():
    """
    Load sample data bucket
    """

    # Resources used:
    # https://docs.couchbase.com/server/current/manage/manage-settings/install-sample-buckets.html

    r = http_request(
        '{}/sampleBuckets/install'.format(URL),
        method='POST',
        auth=(USER, PASSWORD),
        json_data=["gamesim-sample"],
    )
    if r.status_code == http.client.BAD_REQUEST:
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

    # No matching task in the install response — the bucket is likely loading
    # under a task we can't observe. WaitFor will retry; on the retry the install
    # POST takes the already-loaded shortcut, and gamesim_primary_index_ready is
    # the authoritative gate that blocks until the bundled GSI is online.
    if task_id is None:
        return False

    while True:
        # Loop until the task ID is gone, meaning the task is done.
        r = http_request(
            '{}/pools/default/tasks'.format(URL),
            auth=(USER, PASSWORD),
        )
        r.raise_for_status()
        result = r.json()

        task_still_running = any(task.get("task_id") == task_id for task in result)
        if not task_still_running:
            break

        time.sleep(1)

    return True


def gamesim_primary_index_ready():
    """Wait until every gamesim_primary keyspace reports initial_build_progress == 100."""
    r = http_request(
        '{}/api/v1/stats'.format(INDEX_STATS_URL),
        auth=(USER, PASSWORD),
    )
    r.raise_for_status()

    data = r.json()
    matches = [
        stats
        for keyspace, stats in data.items()
        if keyspace != "indexer"
        and keyspace.split(":")[0] == "gamesim-sample"
        and keyspace.split(":")[-1] == "gamesim_primary"
    ]
    if not matches:
        print("gamesim_primary not yet visible; keyspaces seen: {}".format(list(data.keys())))
        return False
    return all(s.get("initial_build_progress") == 100 for s in matches)


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

    r = http_request(
        '{}/sync_gateway/'.format(SG_URL),
        method='PUT',
        auth=(USER, PASSWORD),
        json_data=payload,
    )
    r.raise_for_status()


def node_stats():
    """
    Wait for couchbase to generate node stats
    """
    r = http_request('{}/pools/default'.format(URL), auth=(USER, PASSWORD))
    r.raise_for_status()
    stats = r.json()
    return all(len(stats['interestingStats']) > 0 for stats in stats['nodes'])


def bucket_stats():
    """
    Wait for couchbase to generate bucket stats
    """
    r = http_request('{}/pools/default/buckets/{}/stats'.format(URL, BUCKET_NAME), auth=(USER, PASSWORD))
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
        return MockHTTPResponse(content=f.read())
