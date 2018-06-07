# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os
import subprocess
from shutil import rmtree, copytree
import tempfile
from time import sleep

import pytest
import requests

from .common import HERE, URL


@pytest.fixture
def aggregator():
    from datadog_checks.stubs import aggregator
    aggregator.reset()
    return aggregator


@pytest.fixture(scope="session", autouse=True)
def activemq_xml_container():
    tmp_dir = tempfile.mkdtemp()
    fixture_dir = os.path.join(HERE, "fixtures")
    activemq_data_dir = os.path.join(tmp_dir, "data")
    copytree(fixture_dir, activemq_data_dir)

    env = os.environ
    env["ACTIVEMQ_DATA_DIR"] = activemq_data_dir

    args = [
        "docker-compose",
        "-f", os.path.join(HERE, 'compose', 'docker-compose.yaml')
    ]

    subprocess.check_call(args + ["down"])
    subprocess.check_call(args + ["up", "-d"])

    # wait for the cluster to be up before yielding
    if not wait_for_container():
        subprocess.check_call(args + ["down"])
        raise Exception("activemq_xml container boot timed out!")

    yield

    rmtree(tmp_dir, ignore_errors=True)
    subprocess.check_call(args + ["down"])


def wait_for_container():
    """
    Wait for the activemq_xml container to be reachable
    """
    for i in xrange(100):
        print("Waiting for service to come up")
        try:
            requests.get(URL).raise_for_status()
            return True
        except Exception as e:
            print e
            sleep(1)

    return False
