# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.dev import docker_run

from . import common

METRICS = [
    'nfsstat.test'
]

@pytest.mark.e2e
def test_e2e(dd_agent_check):
    aggregator = dd_agent_check(common.CONFIG)
    print(aggregator)
    for metric in METRICS:
        aggregator.assert_metric(metric)

