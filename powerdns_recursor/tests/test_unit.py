# (C) Datadog, Inc. 2010-2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import pytest

from . import common


def test_bad_config(aggregator, check):
    with pytest.raises(Exception):
        check.check(common.BAD_CONFIG)

    service_check_tags = common._config_sc_tags(common.BAD_CONFIG)
    aggregator.assert_service_check('powerdns.recursor.can_connect', status=check.CRITICAL, tags=service_check_tags)
    assert len(aggregator._metrics) == 0


def test_very_bad_config(aggregator, check):
    for config in [{}, {"host": "localhost"}, {"port": 1000}, {"host": "localhost", "port": 1000}]:
        with pytest.raises(Exception):
            check.check(common.BAD_API_KEY_CONFIG)

    assert len(aggregator._metrics) == 0
