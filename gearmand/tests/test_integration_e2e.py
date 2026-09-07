# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.base.constants import ServiceCheck
from datadog_checks.dev.docker import assert_all_discovery_candidates_stable

from . import common


def assert_metrics(aggregator, *, check_tags=True):
    if check_tags:
        tags = ['server:{}'.format(common.HOST), 'port:{}'.format(common.PORT)] + common.TAGS
    else:
        tags = None

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


@pytest.mark.e2e
def test_e2e_discovery(dd_agent_check_discovery):
    aggregator = dd_agent_check_discovery(rate=True)

    assert_metrics(aggregator, check_tags=False)


@pytest.mark.e2e
def test_e2e_discovery_all_candidates(dd_agent_check):
    from datadog_checks.gearmand import Gearman

    assert_all_discovery_candidates_stable(dd_agent_check, Gearman, compose_service='gearman')
