# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import time

import pytest

from . import common

pytestmark = [pytest.mark.usefixtures('dd_environment'), pytest.mark.integration]


def test_check(aggregator, check, instance):
    _check_repeat(check, instance)
    for mname in common.COMMON_METRICS:
        aggregator.assert_metric(mname, at_least=1, tags=['cluster:webs', 'varnish_name:default'])


def test_inclusion_filter(aggregator, check, instance):
    instance['metrics_filter'] = ['SMA.*']

    _check_repeat(check, instance)
    for mname in common.COMMON_METRICS:
        if 'SMA.' in mname:
            aggregator.assert_metric(mname, at_least=1, tags=['cluster:webs', 'varnish_name:default'])
        else:
            aggregator.assert_metric(mname, count=0, tags=['cluster:webs', 'varnish_name:default'])


def test_exclusion_filter(aggregator, check, instance):
    instance['metrics_filter'] = ['^SMA.Transient.c_req']

    _check_repeat(check, instance)
    for mname in common.COMMON_METRICS:
        if 'SMA.Transient.c_req' in mname:
            aggregator.assert_metric(mname, count=0, tags=['cluster:webs', 'varnish_name:default'])
        elif 'varnish.uptime' not in mname:
            aggregator.assert_metric(mname, at_least=1, tags=['cluster:webs', 'varnish_name:default'])


def _check_repeat(check, instance):
    # Ensure all metrics are generated
    check.check(instance)
    time.sleep(2)
    check.check(instance)
