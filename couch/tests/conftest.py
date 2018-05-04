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


@pytest.fixture(scope="session")
def couch_cluster():
    """
    Start a cluster with one master, one replica and one unhealthy replica and
    stop it after the tests are done.
    If there's any problem executing docker-compose, let the exception bubble
    up.
    """
    env = os.environ
    env['COUCH_PORT'] = common.PORT
    couch_version = env["COUCH_VERSION"][0]

    args = [
        "docker-compose",
        "-f", os.path.join(common.HERE, 'compose', 'compose_v{}.yaml'.format(couch_version))
    ]

    subprocess.check_call(args + ["down"])
    subprocess.check_call(args + ["up", "-d"])
    # wait for the cluster to be up before yielding
    if not wait_for_couch():
        raise Exception("couchdb container boot timed out!")

    generate_data(couch_version)

    yield
    subprocess.check_call(args + ["down"])


def generate_data(couch_version):
    """
    Generate data on the couch cluster to test metrics
    """
    if couch_version == "1":
        # Generate a test database
        requests.put("{}/kennel".format(common.URL))
    else:
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

        urls = [
            "{}/_node/node1@127.0.0.1/_stats".format(common.URL),
            "{}/_node/node2@127.0.0.1/_stats".format(common.URL),
            "{}/_node/node3@127.0.0.1/_stats".format(common.URL)
        ]
        ready = [False, False, False]

        print("Waiting for stats to be generated on the nodes...")
        for i in xrange(60):
            try:
                for i in xrange(3):
                    if not ready[i]:
                        res = requests.get(urls[i], auth=(common.USER, common.PASSWORD))
                        if res.json():
                            ready[i] = True

                if all(ready):
                    break
            except Exception:
                print("Waiting for stats to be generated on the nodes...")
                pass
            sleep(1)


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
