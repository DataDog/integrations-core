# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.base.constants import ServiceCheck

from . import common


def assert_metrics(aggregator):
    tags = ['server:{}'.format(common.HOST), 'port:{}'.format(common.PORT)] + common.TAGS

    aggregator.assert_metric('gearman.unique_tasks', value=0.0, tags=tags, count=2)
    aggregator.assert_metric('gearman.running', value=0.0, tags=tags, count=2)
    aggregator.assert_metric('gearman.queued', value=0.0, tags=tags, count=2)
    aggregator.assert_metric('gearman.workers', value=0.0, tags=tags, count=2)
    aggregator.assert_service_check('gearman.can_connect', status=ServiceCheck.OK, tags=tags, count=2)
    aggregator.assert_all_metrics_covered()


@pytest.mark.usefixtures("dd_environment")
def test_metrics(check, instance, aggregator, dd_run_check):
    check = check(instance)
    dd_run_check(check)
    dd_run_check(check)

    assert_metrics(aggregator)


@pytest.mark.e2e
def test_e2e(dd_agent_check, instance):
    aggregator = dd_agent_check(instance, rate=True)

    assert_metrics(aggregator)
