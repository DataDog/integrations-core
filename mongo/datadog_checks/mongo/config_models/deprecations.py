# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


def instance():
    return {
        'schemas': {'Agent version': '7.69.0', 'Migration': 'Use `collect_schemas` instead.'},
        'server': {
            'Agent version': '8.0.0',
            'Migration': 'Use the following options instead:\nhosts, username, password, database, options\n',
        },
    }
