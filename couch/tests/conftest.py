# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import base64
import http.client
import json
import os
import urllib.error
import urllib.request
from copy import deepcopy
from typing import Any

import pytest

from datadog_checks.couch import CouchDb
from datadog_checks.dev import docker_run
from datadog_checks.dev.conditions import CheckDockerLogs, CheckEndpoints, WaitFor

from . import common


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
    headers: dict[str, str] | None = None,
    json_data: Any = None,
) -> HttpResponse:
    request_headers = dict(headers or {})
    body = None
    if json_data is not None:
        body = json.dumps(json_data).encode('utf-8')
        request_headers.setdefault('Content-Type', 'application/json')

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
def check():
    if common.COUCH_MAJOR_VERSION == 1:
        return CouchDb(common.CHECK_NAME, {}, instances=[common.BASIC_CONFIG])
    else:
        return CouchDb(common.CHECK_NAME, {}, instances=[common.BASIC_CONFIG_V2])


@pytest.fixture
def instance():
    if common.COUCH_MAJOR_VERSION == 1:
        return deepcopy(common.BASIC_CONFIG)
    else:
        return deepcopy(common.BASIC_CONFIG_V2)


@pytest.fixture
def active_tasks():
    """
    Returns a raw response from `/_active_tasks`
    """
    with open(os.path.join(common.HERE, 'fixtures', '_active_tasks.json')) as f:
        return json.loads(f.read())


@pytest.fixture
def load_test_data():
    """
    Returns a raw response from `/_3.4_system.json`
    """
    with open(os.path.join(common.HERE, 'fixtures', '_3.4_system.json')) as f:
        return json.load(f)


@pytest.fixture(scope="session")
def dd_environment():
    """
    Start a cluster with one master, one replica and one unhealthy replica and
    stop it after the tests are done.
    If there's any problem executing `docker compose`, let the exception bubble
    up.
    """
    couch_version = os.environ["COUCH_VERSION"][0]
    if couch_version == "1":
        with docker_run(
            compose_file=os.path.join(common.HERE, 'compose', 'compose_v1.yaml'),
            env_vars={'COUCH_PORT': common.PORT},
            conditions=[
                CheckEndpoints([common.URL]),
                CheckDockerLogs('couchdb-1', ['CouchDB has started', 'Application couch_index started']),
                WaitFor(generate_data, args=(couch_version,)),
            ],
        ):
            yield common.BASIC_CONFIG

    else:
        with docker_run(
            compose_file=os.path.join(common.HERE, 'compose', 'compose_v2.yaml'),
            env_vars={'COUCH_PORT': common.PORT, 'COUCH_USER': common.USER, 'COUCH_PASSWORD': common.PASSWORD},
            conditions=[
                CheckEndpoints([common.URL]),
                CheckDockerLogs('couchdb-1', ['Started replicator db changes listener']),
                WaitFor(enable_cluster),
                WaitFor(generate_data, args=(couch_version,)),
                WaitFor(check_node_stats),
                WaitFor(send_replication),
                WaitFor(get_replication),
            ],
        ):
            yield common.BASIC_CONFIG_V2


def enable_cluster():
    auth = (common.USER, common.PASSWORD)
    headers = {'Accept': 'text/json'}

    cluster_setup_payloads = []
    for node in [common.NODE2, common.NODE3]:
        _, node_name = node['name'].split('@')
        cluster_setup_payloads.append(
            {
                "action": "enable_cluster",
                "username": common.USER,
                "password": common.PASSWORD,
                "bind_address": "0.0.0.0",
                "port": 5984,
                "node_count": 3,
                "remote_node": node_name,
                "remote_current_user": common.USER,
                "remote_current_password": common.PASSWORD,
            }
        )
        cluster_setup_payloads.append(
            {
                "action": "add_node",
                "username": common.USER,
                "password": common.PASSWORD,
                "host": node_name,
                "port": 5984,
                "singlenode": False,
            }
        )

    resp_data = None
    for data in cluster_setup_payloads:
        resp = http_request(
            "{}/_cluster_setup".format(common.URL), method='POST', json_data=data, auth=auth, headers=headers
        )
        resp_data = resp.json()

    resp = http_request("{}/_membership".format(common.URL), auth=auth, headers=headers)
    membership = resp.json()

    expected_nb_nodes = 3
    actual_nb_nodes = len(membership['cluster_nodes'])
    error_msg = [
        "Expected {} cluster nodes, but only found {}".format(expected_nb_nodes, actual_nb_nodes),
        "Membership response: {}".format(membership),
        "Last cluster setup response: {}".format(resp_data),
    ]
    assert actual_nb_nodes == expected_nb_nodes, "\n".join(error_msg)


def generate_data(couch_version):
    """
    Generate data on the couch cluster to test metrics.
    """
    # pass in authentication info for version 2
    auth = None if couch_version == "1" else (common.USER, common.PASSWORD)
    headers = {'Accept': 'text/json'}

    # Generate a test database
    http_request("{}/kennel".format(common.URL), method='PUT', auth=auth, headers=headers)
    for i in range(5):
        http_request("{}/db{}".format(common.URL, i), method='PUT', auth=auth, headers=headers)

    # Populate the database
    data = {
        "language": "javascript",
        "views": {
            "all": {"map": "function(doc) { emit(doc._id); }"},
            "by_data": {"map": "function(doc) { emit(doc.data, doc); }"},
        },
    }
    http_request("{}/kennel/_design/dummy".format(common.URL), method='PUT', json_data=data, auth=auth, headers=headers)


def check_node_stats():
    auth = (common.USER, common.PASSWORD)
    headers = {'Accept': 'text/json'}
    # Check all nodes have stats
    for node in common.ALL_NODES:
        url = "{}/_node/{}/_stats".format(common.URL, node['name'])
        res = http_request(url, auth=auth, headers=headers)
        data = res.json()
        assert "global_changes" in data, "Invalid stats. Get stats url: {}".format(url)


def send_replication():
    """
    Send replication task to trigger tasks
    """
    replicator_url = "{}/_replicate".format(common.NODE1['server'])

    replication_body = {
        '_id': 'my_replication_id',
        'source': 'http://dduser:pawprint@127.0.0.1:5984/kennel',
        'target': 'http://dduser:pawprint@127.0.0.1:5984/kennel_replica',
        'create_target': True,
        'continuous': True,
    }
    for i in range(5):
        body = replication_body.copy()
        body['_id'] = 'my_replication_id_{}'.format(i)
        body['target'] = body['target'] + str(i)
        r = http_request(
            replicator_url,
            method='POST',
            auth=(common.NODE1['user'], common.NODE1['password']),
            headers={'Content-Type': 'application/json'},
            json_data=body,
        )
        r.raise_for_status()


def get_replication():
    """
    Attempt to get active replication tasks
    """
    task_url = "{}/_active_tasks".format(common.NODE1['server'])

    r = http_request(task_url, auth=(common.NODE1['user'], common.NODE1['password']))
    r.raise_for_status()
    active_tasks = r.json()
    count = len(active_tasks)
    assert count > 0, "Expect active tasks but none found.\nactive_tasks response: {}".format(active_tasks)
