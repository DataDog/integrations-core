# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import subprocess
import time

import pytest
import requests

from datadog_checks.elastic import ESCheck

from .common import HERE, URL


@pytest.fixture(scope="session")
def elastic_cluster():
    args = [
        'docker-compose', '-f', os.path.join(HERE, 'compose', 'docker-compose.yaml')
    ]
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
def elastic_check():
    return ESCheck('elastic', {}, {})
