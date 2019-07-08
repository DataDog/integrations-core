# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from six import iteritems


def test_fixtures(check_mock, instance, aggregator):
    check_mock.check(instance)
    metrics = {}
    for d in (
        check_mock.SLAVE_TASKS_METRICS,
        check_mock.SYSTEM_METRICS,
        check_mock.SLAVE_RESOURCE_METRICS,
        check_mock.SLAVE_EXECUTORS_METRICS,
        check_mock.STATS_METRICS,
    ):
        metrics.update(d)

    for _, v in iteritems(check_mock.TASK_METRICS):
        aggregator.assert_metric(v[0])
    for _, v in iteritems(metrics):
        aggregator.assert_metric(v[0])

    service_check_tags = [
        'instance:mytag1',
        'mesos_cluster:test',
        'mesos_node:slave',
        'mesos_pid:slave(1)@127.0.0.1:5051',
        'task_name:hello',
    ]
    aggregator.assert_service_check('hello.ok', tags=service_check_tags, count=1, status=check_mock.OK)
