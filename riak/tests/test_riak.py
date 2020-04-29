# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import socket

import pytest

from datadog_checks.riak import Riak

from . import common


@pytest.mark.usefixtures('dd_environment')
def test_check(aggregator, check, instance):
    check.check(instance)
    check.check(instance)
    tags = ['my_tag']
    sc_tags = tags + ['url:' + instance['url']]

    for gauge in common.CHECK_GAUGES + common.CHECK_GAUGES_STATS:
        aggregator.assert_metric(gauge, tags=tags, count=2)

    aggregator.assert_service_check(common.SERVICE_CHECK_NAME, status=Riak.OK, tags=sc_tags)

    for gauge in common.GAUGE_OTHER:
        aggregator.assert_metric(gauge, count=1)

    aggregator.all_metrics_asserted()


@pytest.mark.usefixtures('dd_environment')
def test_bad_config(aggregator, instance):
    instance.update({"url": "http://localhost:5985"})
    check = Riak('riak', {}, [instance])

    with pytest.raises(socket.error):
        check.check(instance)

    sc_tags = ['my_tag', 'url:http://localhost:5985']
    aggregator.assert_service_check(common.SERVICE_CHECK_NAME, status=Riak.CRITICAL, tags=sc_tags)
