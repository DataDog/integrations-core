# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.gearmand import Gearman

from . import common


@pytest.mark.usefixtures("dd_environment")
def test_service_check(check, aggregator):
    tags = ['server:{}'.format(common.HOST), 'port:{}'.format(common.PORT)] + common.TAGS2

    check.check(common.INSTANCE2)

    aggregator.assert_metric('gearman.unique_tasks', value=0.0, tags=tags, count=1)
    aggregator.assert_metric('gearman.running', value=0.0, tags=tags, count=1)
    aggregator.assert_metric('gearman.queued', value=0.0, tags=tags, count=1)
    aggregator.assert_metric('gearman.workers', value=0.0, tags=tags, count=1)

    aggregator.assert_service_check('gearman.can_connect', status=Gearman.OK, tags=tags, count=1)

    aggregator.assert_all_metrics_covered()


@pytest.mark.usefixtures("dd_environment")
def test_service_check_broken(check, aggregator):
    tags = ['server:{}'.format(common.HOST), 'port:{}'.format(common.BAD_PORT)] + common.TAGS2

    with pytest.raises(Exception):
        check.check(common.BAD_INSTANCE)

    aggregator.assert_service_check('gearman.can_connect', status=Gearman.CRITICAL, tags=tags, count=1)
    aggregator.assert_all_metrics_covered()
