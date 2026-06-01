# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from datadog_checks.dev import get_here

HERE = get_here()


def get_fixture_path(filename):
    return os.path.join(HERE, 'fixtures', filename)


MOCKED_INSTANCE = {
    'openmetrics_endpoint': 'http://localhost:8080/metrics',
    'tags': ['test:tag'],
}

TEST_METRICS = [
    'kueue.go_goroutines',
    'kueue.kueue_resource_flavor_quota_reserved_workloads',
]
# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from datadog_checks.dev import get_here

HERE = get_here()


def get_fixture_path(filename):
    return os.path.join(HERE, 'fixtures', filename)


MOCKED_INSTANCE = {
    'openmetrics_endpoint': 'http://localhost:8080/metrics',
    'tags': ['test:tag'],
}

TEST_METRICS = [
    'kueue.go_goroutines',
    'kueue.kueue_resource_flavor_quota_reserved_workloads',
]
