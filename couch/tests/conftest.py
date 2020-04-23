# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import os
from collections import defaultdict
from copy import deepcopy
from time import sleep

import pytest
import requests

from datadog_checks.couch import CouchDb
from datadog_checks.dev import docker_run
from datadog_checks.dev.conditions import CheckDockerLogs, CheckEndpoints

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
        startup_msg = 'CouchDB has started'
    else:
        startup_msg = 'Started replicator db changes listener'

    with docker_run(
        compose_file=os.path.join(common.HERE, 'compose', 'compose_v{}.yaml'.format(couch_version)),
        env_vars={'COUCH_PORT': common.PORT},
        conditions=[
            CheckEndpoints([common.URL]),
            CheckDockerLogs('server-0', [startup_msg]),
            lambda: enable_cluster(couch_version),
            lambda: generate_data(couch_version),
            # WaitFor(send_replication, args=(couch_version,), wait=2, attempts=60),
            # WaitFor(get_replication, args=(couch_version,), wait=3, attempts=40),
        ],
    ):
        if couch_version == '1':
            yield common.BASIC_CONFIG
        elif couch_version == '2':
            yield common.BASIC_CONFIG_V2


def send_replication(couch_version):
    """
    Send replication task to trigger tasks
    """
    if couch_version == '1':
        return

    replicator_url = "{}/_replicate".format(common.NODE1['server'])

    replication_body = {
        '_id': 'my_replication_id',
        'source': 'http://dduser:pawprint@127.0.0.1:5984/kennel',
        'target': 'http://dduser:pawprint@127.0.0.1:5984/kennel_replica',
        'create_target': True,
        'continuous': True,
    }
    for i in range(100):
        print("Create Replication task")
        replication_body['_id'] = 'my_replication_id_{}'.format(i)
        r = requests.post(
            replicator_url,
            auth=(common.NODE1['user'], common.NODE1['password']),
            headers={'Content-Type': 'application/json'},
            json=replication_body,
        )
        r.raise_for_status()
        print("Replication task created:", r.json())


def get_replication(couch_version):
    """
    Attempt to get active replication tasks
    """
    if couch_version == '1':
        return

    task_url = "{}/_active_tasks".format(common.NODE1['server'])

    r = requests.get(task_url, auth=(common.NODE1['user'], common.NODE1['password']))
    r.raise_for_status()
    active_tasks = r.json()
    print("active_tasks:", active_tasks)
    count = len(active_tasks)
    return count > 0


def enable_cluster(couch_version):
    if couch_version == "1":
        return
    auth = (common.USER, common.PASSWORD)
    headers = {'Accept': 'text/json'}

    requests_data = []
    for node in ["couchdb-1.docker.com", "couchdb-2.docker.com"]:
        requests_data.append(
            {
                "action": "enable_cluster",
                "username": common.USER,
                "password": common.PASSWORD,
                "bind_address": "0.0.0.0",
                "port": 5984,
                "node_count": 3,
                "remote_node": node,
                "remote_current_user": common.USER,
                "remote_current_password": common.PASSWORD,
            }
        )
        requests_data.append(
            {
                "action": "add_node",
                "username": common.USER,
                "password": common.PASSWORD,
                "host": node,
                "port": 5984,
                "singlenode": False,
            }
        )

    for data in enumerate(requests_data):
        for i in range(10):
            r = requests.post("{}/_cluster_setup".format(common.URL), json=data, auth=auth, headers=headers)
            if r.status_code == 200:
                break
            print('cluster_setup request error: ', r.json())
            sleep(1)


def generate_data(couch_version):
    """
    Generate data on the couch cluster to test metrics.
    """
    # pass in authentication info for version 2
    auth = (common.USER, common.PASSWORD) if couch_version == "2" else None
    headers = {'Accept': 'text/json'}

    # Generate a test database
    r = requests.put("{}/kennel".format(common.URL), auth=auth, headers=headers)
    r.raise_for_status()

    # Populate the database
    data = {
        "language": "javascript",
        "views": {
            "all": {"map": "function(doc) { emit(doc._id); }"},
            "by_data": {"map": "function(doc) { emit(doc.data, doc); }"},
        },
    }
    r = requests.put("{}/kennel/_design/dummy".format(common.URL), json=data, auth=auth, headers=headers)
    r.raise_for_status()

    urls = [
        "{}/_node/node1@127.0.0.1/_stats".format(common.URL),
        "{}/_node/node2@127.0.0.1/_stats".format(common.URL),
        "{}/_node/node3@127.0.0.1/_stats".format(common.URL),
    ]

    ready = defaultdict(bool)
    for _ in range(120):
        print("Waiting for stats to be generated on the nodes...")
        try:
            for url in urls:
                if not ready[url]:
                    res = requests.get(url, auth=auth, headers=headers)
                    data = res.json()
                    print("node data", data)
                    if data:
                        ready[url] = True
            if len(ready) and all(ready.values()):
                break
        except Exception:
            pass
        sleep(1)

    if couch_version == "1":
        return
    #
    # doc_url = "{}/_replicator/_all_docs".format(common.URL)
    # for _ in range(120):
    #     try:
    #         res = requests.get(doc_url, auth=auth, headers=headers)
    #         data = res.json()
    #         print("_replicator/_all_docs", data)
    #         if data.get('rows'):
    #             break
    #     except Exception:
    #         pass
    #     sleep(1)
