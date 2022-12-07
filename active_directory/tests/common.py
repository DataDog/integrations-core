# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from datadog_checks.active_directory.metrics import METRICS_CONFIG

MINIMAL_INSTANCE = {'host': '.'}

CHECK_NAME = 'active_directory'

PERFORMANCE_OBJECTS = {}
for object_name, instances in (('NTDS', [None]),):
    PERFORMANCE_OBJECTS[object_name] = (
        instances,
        {counter: [9000] for counter in METRICS_CONFIG[object_name]['counters'][0]},
    )
