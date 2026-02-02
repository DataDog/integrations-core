# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

from datadog_checks.active_directory.metrics import METRICS_CONFIG

PERFORMANCE_OBJECTS = {}
for object_name in METRICS_CONFIG.keys():
    PERFORMANCE_OBJECTS[object_name] = (
        [None],
        {counter: [9000] for counter in METRICS_CONFIG[object_name]['counters'][0].keys()},
    )
