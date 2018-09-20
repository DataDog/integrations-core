# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import os

CHECK_NAME = "riakcs"
HERE = os.path.dirname(os.path.abspath(__file__))
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


def read_fixture(filename):
    p = os.path.join(HERE, 'fixtures', filename)
    with open(p) as f:
        contents = f.read()

    return contents
