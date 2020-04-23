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
from datadog_checks.dev import WaitFor, docker_run
from datadog_checks.dev.conditions import CheckEndpoints

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

    with docker_run(
        compose_file=os.path.join(common.HERE, 'compose', 'compose_v{}.yaml'.format(couch_version)),
        env_vars={'COUCH_PORT': common.PORT},
        conditions=[
            CheckEndpoints([common.URL]),
            lambda: generate_data(couch_version),
            WaitFor(send_replication, args=(couch_version,), wait=2, attempts=60),
            WaitFor(get_replication, args=(couch_version,), wait=3, attempts=40),
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

    replicator_url = "{}/_replicator".format(common.NODE1['server'])

    replication_body = {
        '_id': 'my_replication_id',
        'source': 'http://dduser:pawprint@127.0.0.1:5984/kennel',
        'target': 'http://dduser:pawprint@127.0.0.1:5984/kennel_replica',
        'create_target': True,
        'continuous': True,
    }
    r = requests.post(
        replicator_url,
        auth=(common.NODE1['user'], common.NODE1['password']),
        headers={'Content-Type': 'application/json'},
        json=replication_body,
    )
    r.raise_for_status()


def get_replication(couch_version):
    """
    Attempt to get active replication tasks
    """
    if couch_version == '1':
        return

    task_url = "{}/_active_tasks".format(common.NODE1['server'])

    r = requests.get(task_url, auth=(common.NODE1['user'], common.NODE1['password']))
    r.raise_for_status()
    count = len(r.json())
    return count > 0


def generate_data(couch_version):
    """
    Generate data on the couch cluster to test metrics.
    """
    # pass in authentication info for version 2
    auth = (common.USER, common.PASSWORD) if couch_version == "2" else None
    headers = {'Accept': 'text/json'}

    # Generate a test database
    requests.put("{}/kennel".format(common.URL), auth=auth, headers=headers)

    # Populate the database
    data = {
        "language": "javascript",
        "views": {
            "all": {"map": "function(doc) { emit(doc._id); }"},
            "by_data": {"map": "function(doc) { emit(doc.data, doc); }"},
        },
    }
    requests.put("{}/kennel/_design/dummy".format(common.URL), json=data, auth=auth, headers=headers)

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
                    if res.json():
                        ready[url] = True
            if len(ready) and all(ready.values()):
                break
        except Exception:
            pass
        sleep(1)

    if couch_version == "1":
        return

    doc_url = "{}/_replicator/_all_docs".format(common.URL)
    for _ in range(120):
        try:
            res = requests.get(doc_url, auth=auth, headers=headers)
            data = res.json()
            if data.get('rows'):
                break
        except Exception:
            pass
        sleep(1)
