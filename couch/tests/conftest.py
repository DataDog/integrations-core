# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os
import subprocess
from time import sleep

import pytest
import requests

import common


@pytest.fixture
def aggregator():
    from datadog_checks.stubs import aggregator
    aggregator.reset()
    return aggregator


@pytest.fixture(scope="module")
def spin_up_couchv1():
    """
    Start a cluster with one master, one replica and one unhealthy replica and
    stop it after the tests are done.
    If there's any problem executing docker-compose, let the exception bubble
    up.
    """
    env = os.environ
    env['COUCH_PORT'] = common.PORT

    args = [
        "docker-compose",
        "-f", os.path.join(common.HERE, 'compose', 'compose_v1.yaml')
    ]

    subprocess.check_call(args + ["down"])
    subprocess.check_call(args + ["up", "-d"])
    # wait for the cluster to be up before yielding
    if not wait_for_couch():
        raise Exception("couchdb container boot timed out!")

    # Generate a test database
    requests.put("{}/kennel".format(common.URL))

    yield
    subprocess.check_call(args + ["down"])


@pytest.fixture(scope="module")
def spin_up_couchv2():
    """
    Start a cluster with one master, one replica and one unhealthy replica and
    stop it after the tests are done.
    If there's any problem executing docker-compose, let the exception bubble
    up.
    """
    env = os.environ
    env['COUCH_PORT'] = common.PORT

    args = [
        "docker-compose",
        "-f", os.path.join(common.HERE, 'compose', 'compose_v2.yaml')
    ]

    subprocess.check_call(args + ["down"])
    subprocess.check_call(args + ["up", "-d"])
    # wait for the cluster to be up before yielding
    if not wait_for_couch():
        raise Exception("couchdb container boot timed out!")

    # Generate a test database
    requests.put("{}/kennel".format(common.URL), auth=(common.USER, common.PASSWORD))

    # Populate database
    data = {
        "language": "javascript",
        "views": {
            "all": {
                "map": "function(doc) { emit(doc._id, doc); }"
            },
            "by_data": {
                "map": "function(doc) { emit(doc.data, doc); }"
            }
        }
    }
    requests.put("{}/kennel/_design/dummy".format(common.URL), json=data, auth=(common.USER, common.PASSWORD))

    url1 = "{}/_node/node1@127.0.0.1/_stats".format(common.URL)
    url2 = "{}/_node/node2@127.0.0.1/_stats".format(common.URL)
    url3 = "{}/_node/node3@127.0.0.1/_stats".format(common.URL)
    ready1 = ready2 = ready3 = False

    print("Waiting for stats to be generated on the nodes...")
    for i in xrange(60):
        try:
            if not ready1:
                res = requests.get(url1, auth=(common.USER, common.PASSWORD))
                if res.json():
                    ready1 = True
            if not ready2:
                res = requests.get(url2, auth=(common.USER, common.PASSWORD))
                if res.json():
                    ready2 = True
            if not ready3:
                res = requests.get(url3, auth=(common.USER, common.PASSWORD))
                if res.json():
                    ready3 = True

            if ready1 and ready2 and ready3:
                break
        except Exception:
            print("Waiting for stats to be generated on the nodes...")
            pass
        sleep(1)

    yield
    subprocess.check_call(args + ["down"])


def wait_for_couch():
    """
    Wait for the couchdb container to be reachable
    """
    for i in xrange(40):
        sleep(1)
        try:
            requests.get(common.URL).raise_for_status()
            return True
        except Exception:
            print("Waiting for container to come up")
            pass

    return False
