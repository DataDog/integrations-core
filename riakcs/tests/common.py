# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import copy
import os

from datadog_checks.dev import get_here, run_command

CHECK_NAME = "riakcs"
HERE = get_here()
SERVICE_CHECK_NAME = 'riakcs.can_connect'

CONFIG = {
    "access_id": "foo",
    "access_secret": "bar",
    "tags": ["optional:tag1"]
}

CONFIG_21 = {
    "access_id": "foo",
    "access_secret": "bar",
    "metrics": [
        "request_pool_overflow",
        "request_pool_size",
        "request_pool_workers",
    ],
}


def generate_config_with_creds():
    access_id = run_command([
        "docker", "exec", "dd-test-riakcs",
        "bash", "-c", "grep admin_key /etc/riak-cs/advanced.config | cut -d '\"' -f2"
    ], capture="out").stdout.strip()
    access_secret = run_command([
        "docker", "exec", "dd-test-riakcs",
        "bash", "-c", "grep admin_secret /etc/riak-cs/advanced.config | cut -d '\"' -f2"
    ], capture="out").stdout.strip()

    config = copy.deepcopy(CONFIG_21)
    config["access_id"] = access_id
    config["access_secret"] = access_secret
    config["is_secure"] = False
    config["s3_root"] = "s3.amazonaws.dev"

    return config


def read_fixture(filename):
    p = os.path.join(HERE, 'fixtures', filename)
    with open(p) as f:
        contents = f.read()

    return contents
