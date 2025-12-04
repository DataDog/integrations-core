# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


def instance():
    return {
        'deadlocks_collection': {'Agent version': '7.69.0', 'Migration': 'Use `collect_deadlocks` instead.'},
        'schemas_collection': {'Agent version': '7.69.0', 'Migration': 'Use `collect_schemas` instead.'},
        'xe_collection': {'Agent version': '7.69.0', 'Migration': 'Use `collect_xe` instead.'},
    }
