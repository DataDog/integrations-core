# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.gearmand import Gearman

from . import common


def test_service_check_broken(check, aggregator):
    tags = ['server:{}'.format(common.HOST), 'port:{}'.format(common.BAD_PORT)] + common.TAGS2

    with pytest.raises(Exception):
        check.check(common.BAD_INSTANCE)

    aggregator.assert_service_check('gearman.can_connect', status=Gearman.CRITICAL, tags=tags, count=1)
    aggregator.assert_all_metrics_covered()
