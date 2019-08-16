# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import json
import os

from . import common


def read_fixture(name):
    with open(os.path.join(common.FIXTURE_DIR, name)) as f:
        return f.read()


def mock_check(check):
    check._get_stats = lambda v, x: json.loads(read_fixture('stats.json'))
    check._get_state = lambda v, x: json.loads(read_fixture('state.json'))
    return check
