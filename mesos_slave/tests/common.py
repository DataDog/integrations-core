# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.dev import get_here

HERE = get_here()

INSTANCE = {
    'url': 'http://localhost:5051',
    'tasks': ['hello'],
    'tags': ['instance:mytag1']
}
