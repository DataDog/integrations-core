# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import json
import pytest
import requests

from time import sleep
from collections import defaultdict
from copy import deepcopy

from datadog_checks.dev import docker_run
from datadog_checks.dev.conditions import CheckEndpoints
from datadog_checks.couch import CouchDb

from . import common


@pytest.fixture
def check():
    return CouchDb(common.CHECK_NAME, {}, {})


@pytest.fixture
def instance():
    instance = deepcopy(common.BASIC_CONFIG)
    return instance


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
    env = os.environ
    env['COUCH_PORT'] = common.PORT
    couch_version = env["COUCH_VERSION"][0]

    with docker_run(
        compose_file=os.path.join(common.HERE, 'compose', 'compose_v{}.yaml'.format(couch_version)),
        env_vars=env,
        conditions=[CheckEndpoints([common.URL]), lambda: generate_data(couch_version)],
    ):
        yield common.BASIC_CONFIG


def generate_data(couch_version):
    """
    Generate data on the couch cluster to test metrics.
    """
    # pass in authentication info for version 2
    auth = (common.USER, common.PASSWORD) if couch_version == "2" else None

    # Generate a test database
    requests.put("{}/kennel".format(common.URL), auth=auth)

    # Populate the database
    data = {
        "language": "javascript",
        "views": {
            "all": {
                "map": "function(doc) { emit(doc._id); }"
            },
            "by_data": {
                "map": "function(doc) { emit(doc.data, doc); }"
            }
        }
    }
    requests.put("{}/kennel/_design/dummy".format(common.URL), json=data, auth=auth)

    urls = [
        "{}/_node/node1@127.0.0.1/_stats".format(common.URL),
        "{}/_node/node2@127.0.0.1/_stats".format(common.URL),
        "{}/_node/node3@127.0.0.1/_stats".format(common.URL)
    ]

    ready = defaultdict(bool)
    for i in range(120):
        print("Waiting for stats to be generated on the nodes...")
        try:
            for url in urls:
                if not ready[url]:
                    res = requests.get(url, auth=auth)
                    if res.json():
                        ready[url] = True
            if len(ready) and all(ready.values()):
                break
        except Exception:
            pass
        sleep(1)
