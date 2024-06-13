# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from datadog_checks.dev import get_here

HERE = get_here()

OM_MOCKED_INSTANCE = {
    'openmetrics_endpoint': 'http://kyverno:8000/metrics',
    'tags': ['test:tag'],
}

def get_fixture_path(filename):
    return os.path.join(HERE, 'fixtures', filename)
