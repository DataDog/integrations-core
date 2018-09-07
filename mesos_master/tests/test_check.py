# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os
import pytest
import json

from datadog_checks.mesos_master import MesosMaster


CHECK_NAME = 'mesos_master'
FIXTURE_DIR = os.path.join(os.path.dirname(__file__), 'fixtures')

INSTANCE = {
    'url': 'http://localhost:5050',
    'tags': ['instance:mytag1']
}


def read_fixture(name):
    with open(os.path.join(FIXTURE_DIR, name)) as f:
        return f.read()


@pytest.fixture
def check():
    check = MesosMaster(CHECK_NAME, {}, {})
    check._get_master_roles = lambda v, x, y, z: json.loads(read_fixture('roles.json'))
    check._get_master_stats = lambda v, x, y, z: json.loads(read_fixture('stats.json'))
    check._get_master_state = lambda v, x, y, z: json.loads(read_fixture('state.json'))

    return check


def test_check(check, aggregator):
    check.check(INSTANCE)
    metrics = {}
    for d in (check.CLUSTER_TASKS_METRICS, check.CLUSTER_SLAVES_METRICS,
              check.CLUSTER_RESOURCES_METRICS, check.CLUSTER_REGISTRAR_METRICS,
              check.CLUSTER_FRAMEWORK_METRICS, check.SYSTEM_METRICS, check.STATS_METRICS):
        metrics.update(d)

    for _, v in check.FRAMEWORK_METRICS.iteritems():
        aggregator.assert_metric(v[0])
    for _, v in metrics.iteritems():
        aggregator.assert_metric(v[0])
    for _, v in check.ROLE_RESOURCES_METRICS.iteritems():
        aggregator.assert_metric(v[0])

    aggregator.assert_metric('mesos.cluster.total_frameworks')
    aggregator.assert_metric('mesos.framework.total_tasks')
    aggregator.assert_metric('mesos.role.frameworks.count')
    aggregator.assert_metric('mesos.role.weight')
