# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import os
from copy import deepcopy

import pytest
import requests

from datadog_checks.couch import CouchDb
from datadog_checks.dev import docker_run
from datadog_checks.dev.conditions import CheckDockerLogs, CheckEndpoints, WaitFor

from . import common


@pytest.fixture
def check():
    if common.COUCH_MAJOR_VERSION == 1:
        return CouchDb(common.CHECK_NAME, {}, instances=[common.BASIC_CONFIG])
    elif common.COUCH_MAJOR_VERSION == 2:
        return CouchDb(common.CHECK_NAME, {}, instances=[common.BASIC_CONFIG_V2])


@pytest.fixture
def instance():
    if common.COUCH_MAJOR_VERSION == 1:
        return deepcopy(common.BASIC_CONFIG)
    elif common.COUCH_MAJOR_VERSION == 2:
        return deepcopy(common.BASIC_CONFIG_V2)


@pytest.fixture
def active_tasks():
    """
    Returns a raw response from `/_active_tasks`
    """
    with open(os.path.join(common.HERE, 'fixtures', '_active_tasks.json')) as f:
        return json.loads(f.read())


@pytest.fixture(scope="session")
def dd_environment():
    """
    Start a cluster with one master, one replica and one unhealthy replica and
    stop it after the tests are done.
    If there's any problem executing docker-compose, let the exception bubble
    up.
    """
    couch_version = os.environ["COUCH_VERSION"][0]
    if couch_version == "1":
        with docker_run(
            compose_file=os.path.join(common.HERE, 'compose', 'compose_v1.yaml'),
            env_vars={'COUCH_PORT': common.PORT},
            conditions=[
                CheckEndpoints([common.URL]),
                CheckDockerLogs('couchdb-1', ['CouchDB has started']),
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

    requests_data = []
    for node in [common.NODE2, common.NODE3]:
        _, node_name = node['name'].split('@')
        requests_data.append(
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
        requests_data.append(
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
    for data in requests_data:
        resp = requests.post("{}/_cluster_setup".format(common.URL), json=data, auth=auth, headers=headers)
        resp_data = resp.json()

    resp = requests.get("{}/_membership".format(common.URL), auth=auth, headers=headers)
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
    auth = (common.USER, common.PASSWORD) if couch_version == "2" else None
    headers = {'Accept': 'text/json'}

    # Generate a test database
    requests.put("{}/kennel".format(common.URL), auth=auth, headers=headers)
    for i in range(5):
        requests.put("{}/db{}".format(common.URL, i), auth=auth, headers=headers)

    # Populate the database
    data = {
        "language": "javascript",
        "views": {
            "all": {"map": "function(doc) { emit(doc._id); }"},
            "by_data": {"map": "function(doc) { emit(doc.data, doc); }"},
        },
    }
    requests.put("{}/kennel/_design/dummy".format(common.URL), json=data, auth=auth, headers=headers)


def check_node_stats():
    auth = (common.USER, common.PASSWORD)
    headers = {'Accept': 'text/json'}
    # Check all nodes have stats
    for node in common.ALL_NODES:
        url = "{}/_node/{}/_stats".format(common.URL, node['name'])
        res = requests.get(url, auth=auth, headers=headers)
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
        r = requests.post(
            replicator_url,
            auth=(common.NODE1['user'], common.NODE1['password']),
            headers={'Content-Type': 'application/json'},
            json=body,
        )
        r.raise_for_status()


def get_replication():
    """
    Attempt to get active replication tasks
    """
    task_url = "{}/_active_tasks".format(common.NODE1['server'])

    r = requests.get(task_url, auth=(common.NODE1['user'], common.NODE1['password']))
    r.raise_for_status()
    active_tasks = r.json()
    count = len(active_tasks)
    assert count > 0, "Expect active tasks but none found.\nactive_tasks response: {}".format(active_tasks)
