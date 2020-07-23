# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os

from . import common


def read_fixture(name):
    with open(os.path.join(common.FIXTURE_DIR, name)) as f:
        return f.read()
