# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import json
import os

import pytest
from six import iteritems

from datadog_checks.mesos_master import MesosMaster

from .utils import read_fixture


def test_check(check, instance, aggregator):
    check = check({}, instance)
    check._get_master_roles = lambda v, x: json.loads(read_fixture('roles.json'))
    check._get_master_stats = lambda v, x: json.loads(read_fixture('stats.json'))
    check._get_master_state = lambda v, x: json.loads(read_fixture('state.json'))
    check.check(instance)
    metrics = {}
    for d in (
        check.CLUSTER_TASKS_METRICS,
        check.CLUSTER_SLAVES_METRICS,
        check.CLUSTER_RESOURCES_METRICS,
        check.CLUSTER_REGISTRAR_METRICS,
        check.CLUSTER_FRAMEWORK_METRICS,
        check.SYSTEM_METRICS,
        check.STATS_METRICS,
    ):
        metrics.update(d)

    for _, v in iteritems(check.FRAMEWORK_METRICS):
        aggregator.assert_metric(v[0])
    for _, v in iteritems(metrics):
        aggregator.assert_metric(v[0])
    for _, v in iteritems(check.ROLE_RESOURCES_METRICS):
        aggregator.assert_metric(v[0])

    aggregator.assert_metric('mesos.cluster.total_frameworks')
    aggregator.assert_metric('mesos.framework.total_tasks')
    aggregator.assert_metric('mesos.role.frameworks.count')
    aggregator.assert_metric('mesos.role.weight')


def test_default_timeout(check, instance):
    # test default timeout
    check1 = check({}, instance)
    check1._get_master_roles = lambda v, x: json.loads(read_fixture('roles.json'))
    check1._get_master_stats = lambda v, x: json.loads(read_fixture('stats.json'))
    check1._get_master_state = lambda v, x: json.loads(read_fixture('state.json'))
    check1.check(instance)

    assert check1.http.options['timeout'] == (5, 5)


def test_init_config_old_timeout(check, instance):
    # test init_config timeout
    init_config = {'default_timeout': 2}


def test_init_config_timeout(check, instance):
    # test init_config timeout
    init_config = {'timeout': 7}
    check = check(init_config, instance)
    check._get_master_roles = lambda v, x: json.loads(read_fixture('roles.json'))
    check._get_master_stats = lambda v, x: json.loads(read_fixture('stats.json'))
    check._get_master_state = lambda v, x: json.loads(read_fixture('state.json'))
    check.check(instance)

    assert check.http.options['timeout'] == (7, 7)


def test_instance_old_timeout(check, instance):
    # test instance default_timeout
    default_timeout = instance
    default_timeout['default_timeout'] = 13
    check = check({'default_timeout': 9}, instance)
    check._get_master_roles = lambda v, x: json.loads(read_fixture('roles.json'))
    check._get_master_stats = lambda v, x: json.loads(read_fixture('stats.json'))
    check._get_master_state = lambda v, x: json.loads(read_fixture('state.json'))
    check.check(default_timeout)
    assert check.http.options['timeout'] == (13, 13)


def test_instance_timeout(check, instance):
    # test instance timeout
    instance['timeout'] = 15
    check = check({}, instance)
    check._get_master_roles = lambda v, x: json.loads(read_fixture('roles.json'))
    check._get_master_stats = lambda v, x: json.loads(read_fixture('stats.json'))
    check._get_master_state = lambda v, x: json.loads(read_fixture('state.json'))
    check.check(instance)

    assert check.http.options['timeout'] == (15, 15)
