# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from datadog_checks.dev import get_here

CHECK_NAME = 'linux_proc_extras'

HERE = get_here()
FIXTURE_DIR = os.path.join(HERE, "fixtures")

INSTANCE = {"tags": ["foo:bar"]}

EXPECTED_TAG = "foo:bar"

EXPECTED_METRICS = [
    'system.inodes.total',
    'system.inodes.used',
    'system.linux.context_switches',
    'system.linux.processes_created',
    'system.linux.interrupts',
    'system.entropy.available',
    'system.processes.states',
    'system.processes.priorities',
]
