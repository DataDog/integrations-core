# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os
import pytest
import json

from six import iteritems

from datadog_checks.mesos_slave import MesosSlave


CHECK_NAME = 'mesos_master'
FIXTURE_DIR = os.path.join(os.path.dirname(__file__), 'fixtures')


def read_fixture(name):
    with open(os.path.join(FIXTURE_DIR, name)) as f:
        return f.read()


@pytest.fixture
def check():
    check = MesosSlave(CHECK_NAME, {}, {})
    check._get_stats = lambda v, x, y, z: json.loads(read_fixture('stats.json'))
    check._get_state = lambda v, x, y, z: json.loads(read_fixture('state.json'))

    return check


def test_check(check, instance, aggregator):
    check.check(instance)
    metrics = {}
    for d in (check.SLAVE_TASKS_METRICS, check.SYSTEM_METRICS, check.SLAVE_RESOURCE_METRICS,
              check.SLAVE_EXECUTORS_METRICS, check.STATS_METRICS):
        metrics.update(d)

    for _, v in iteritems(check.TASK_METRICS):
        aggregator.assert_metric(v[0])
    for _, v in iteritems(metrics):
        aggregator.assert_metric(v[0])

    service_check_tags = ['instance:mytag1',
                          'mesos_cluster:test',
                          'mesos_node:slave',
                          'mesos_pid:slave(1)@127.0.0.1:5051',
                          'task_name:hello']
    aggregator.assert_service_check('hello.ok',
                                    tags=service_check_tags,
                                    count=1,
                                    status=MesosSlave.OK)
