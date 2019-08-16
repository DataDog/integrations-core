# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import json
import os

from datadog_checks.mesos_master import MesosMaster

from . import common


def read_fixture(name):
    with open(os.path.join(common.FIXTURE_DIR, name)) as f:
        return f.read()


def create_check(init_config, instance):
    check = MesosMaster(common.CHECK_NAME, init_config, [instance])
    check._get_master_roles = lambda v, x: json.loads(read_fixture('roles.json'))
    check._get_master_stats = lambda v, x: json.loads(read_fixture('stats.json'))
    check._get_master_state = lambda v, x: json.loads(read_fixture('state.json'))
    return check
