# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest
import os
import subprocess
import time
import sys
import json

import requests
from datadog_checks.php_fpm import PHPFPMCheck
from datadog_checks.utils.common import get_docker_hostname


HOST = get_docker_hostname()
HERE = os.path.dirname(os.path.abspath(__file__))


@pytest.fixture
def aggregator():
    from datadog_checks.stubs import aggregator
    aggregator.reset()
    return aggregator


@pytest.fixture
def check():
    return PHPFPMCheck('php_fpm', {}, {})


@pytest.fixture
def instance():
    return {
        'status_url': 'http://{}:8080/status'.format(HOST),
        'ping_url': 'http://{}:8080/ping'.format(HOST),
    }


@pytest.fixture
def ping_url_tag():
    return 'ping_url:http://{}:8080/ping'.format(HOST)


@pytest.fixture(scope="session")
def php_fpm_instance():
    env = os.environ
    args = [
        "docker-compose",
        "-f", os.path.join(HERE, 'compose', 'docker-compose.yml')
    ]
    subprocess.check_call(args + ["up", "-d"], env=env)

    for _ in xrange(10):
        try:
            res = requests.get('http://{}:8080'.format(HOST))
            res.raise_for_status()
            break
        except Exception:
            time.sleep(1)
            sys.stderr.write("Waiting for php-fpm to boot...")
    else:
        subprocess.check_call(args + ["logs"], env=env)
        subprocess.check_call(args + ["down"], env=env)
        raise Exception("php-fpm failed to boot...")

    yield

    subprocess.check_call(args + ["down"], env=env)


@pytest.fixture
def payload():
    """
    example payload from /status?json
    """
    return json.loads("""{
        "pool":"www",
        "process manager":"dynamic",
        "start time":1530722898,
        "start since":12,
        "accepted conn":2,
        "listen queue":0,
        "max listen queue":0,
        "listen queue len":128,
        "idle processes":1,
        "active processes":1,
        "total processes":2,
        "max active processes":1,
        "max children reached":0,
        "slow requests":0
    }""")
