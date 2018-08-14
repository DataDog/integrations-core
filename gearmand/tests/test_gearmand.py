# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest
import logging

from datadog_checks.gearmand import Gearman

from . import common

log = logging.getLogger('test_gearmand')


def test_metrics(spin_up_gearmand, check, aggregator):
    tags = ['first_tag', 'second_tag']
    service_checks_tags = [
        'server:{}'.format(common.HOST),
        'port:{}'.format(common.PORT)
    ]

    assert_tags = tags + service_checks_tags

    check.check(common.INSTANCE)

    aggregator.assert_metric('gearman.unique_tasks', value=0.0, tags=assert_tags, count=1)
    aggregator.assert_metric('gearman.running', value=0.0, tags=assert_tags, count=1)
    aggregator.assert_metric('gearman.queued', value=0.0, tags=assert_tags, count=1)
    aggregator.assert_metric('gearman.workers', value=0.0, tags=assert_tags, count=1)

    aggregator.assert_service_check('gearman.can_connect', status=Gearman.OK,
                                    tags=assert_tags, count=1)
    aggregator.assert_all_metrics_covered()


def test_service_check(spin_up_gearmand, check, aggregator):
    service_checks_tags_ok = [
        'server:{}'.format(common.HOST),
        'port:{}'.format(common.PORT)
    ]

    service_checks_tags_ok += common.TAGS2

    check.check(common.INSTANCE2)

    tags = service_checks_tags_ok

    aggregator.assert_metric('gearman.unique_tasks', value=0.0, tags=tags, count=1)
    aggregator.assert_metric('gearman.running', value=0.0, tags=tags, count=1)
    aggregator.assert_metric('gearman.queued', value=0.0, tags=tags, count=1)
    aggregator.assert_metric('gearman.workers', value=0.0, tags=tags, count=1)

    aggregator.assert_service_check('gearman.can_connect', status=Gearman.OK,
                                    tags=tags, count=1)

    aggregator.assert_all_metrics_covered()


def test_service_check_broken(spin_up_gearmand, check, aggregator):
    service_checks_tags_not_ok = [
        'server:{}'.format(common.HOST),
        'port:{}'.format(common.BAD_PORT)
    ]
    service_checks_tags_not_ok += common.TAGS2
    with pytest.raises(Exception):
        check.check(common.BAD_INSTANCE)

    aggregator.assert_service_check('gearman.can_connect', status=Gearman.CRITICAL,
                                    tags=service_checks_tags_not_ok, count=1)
    aggregator.assert_all_metrics_covered()
