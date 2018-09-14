# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import subprocess
import time

import pytest
import requests

from .common import HERE, URL, get_es_version


@pytest.fixture(scope="session", autouse=True)
def spin_up_elastic():
    args = [
        'docker-compose', '-f', os.path.join(HERE, 'compose', 'elastic.yaml')
    ]
    env = os.environ
    env['ELASTIC_CONFIG'] = "dummy=true"
    if get_es_version() >= [6, 3, 0]:
        env['ELASTIC_CONFIG'] = "xpack.monitoring.collection.enabled=true"
    subprocess.check_call(args + ["up", "-d"])
    print("Waiting for ES to boot...")

    for _ in xrange(20):
        try:
            res = requests.get(URL)
            res.raise_for_status()
            break
        except Exception:
            time.sleep(2)

    # Create an index in ES
    requests.put(URL, '/datadog/')
    yield
    subprocess.check_call(args + ["down"])


@pytest.fixture
def aggregator():
    from datadog_checks.stubs import aggregator
    aggregator.reset()
    return aggregator
