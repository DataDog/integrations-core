# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os
import subprocess
from shutil import rmtree
import stat
import tarfile
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
    # use os.path.realpath to avoid mounting issues of symlinked /var -> /private/var in Docker on macOS
    tmp_dir = os.path.realpath(tempfile.mkdtemp())
    activemq_data_dir = os.path.join(tmp_dir, "data")
    fixture_archive = os.path.join(HERE, "fixtures", "apache-activemq-kahadb.tar.gz")
    os.mkdir(activemq_data_dir)
    with tarfile.open(fixture_archive, "r:gz") as f:
        f.extractall(path=activemq_data_dir)
    os.chmod(os.path.join(activemq_data_dir, "kahadb"), stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)
    os.chmod(os.path.join(activemq_data_dir, "kahadb", "db-1.log"), stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)
    os.chmod(os.path.join(activemq_data_dir, "kahadb", "db.data"), stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)
    os.chmod(os.path.join(activemq_data_dir, "kahadb", "db.redo"), stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)

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
        subprocess.check_call(args + ["logs"])
        subprocess.check_call(args + ["down"])
        raise Exception("activemq_xml container boot timed out!")

    yield

    rmtree(tmp_dir, ignore_errors=True)
    subprocess.check_call(args + ["down"])


def wait_for_container():
    """
    Wait for the activemq_xml container to be reachable
    """
    for i in xrange(30):
        print("Waiting for service to come up")
        try:
            requests.get(URL).raise_for_status()
            return True
        except Exception as e:
            print e
            sleep(1)

    return False
