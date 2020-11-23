# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.varnish import Varnish

from . import common

pytestmark = [pytest.mark.usefixtures('dd_environment'), pytest.mark.integration]


def test_check(aggregator, check, instance):
    check.check(instance)
    exclude = list(Varnish.GAUGE_IN_5_RATE_IN_6)

    if common.VARNISH_VERSION.startswith("5"):
        metrics_to_check = common.COMMON_METRICS + common.METRICS_5
    else:
        metrics_to_check = common.COMMON_METRICS + common.METRICS_6

    for mname in metrics_to_check:
        aggregator.assert_metric(mname, count=1, tags=['cluster:webs', 'varnish_name:default'])

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), exclude=exclude)


def test_check_compatibility_mode_off(aggregator, instance):
    instance['compatibility_mode'] = False
    check = Varnish(common.CHECK_NAME, {}, [instance])
    check.check(instance)

    metric_type = aggregator.GAUGE if common.VARNISH_VERSION.startswith("5") else aggregator.RATE
    for mname in Varnish.GAUGE_IN_5_RATE_IN_6:
        aggregator.assert_metric(mname, count=1, metric_type=metric_type)


def test_check_compatibility_mode_on(aggregator, instance):
    instance['compatibility_mode'] = True
    check = Varnish(common.CHECK_NAME, {}, [instance])
    check.check(instance)

    for mname in Varnish.GAUGE_IN_5_RATE_IN_6:
        aggregator.assert_metric(mname, count=1, metric_type=aggregator.GAUGE)
    aggregator.assert_metric('varnish.n_purgesps', count=1, metric_type=aggregator.RATE)


def test_inclusion_filter(aggregator, check, instance):
    instance['metrics_filter'] = ['SMA.*']

    check.check(instance)
    for mname in common.COMMON_METRICS:
        if 'SMA.' in mname:
            aggregator.assert_metric(mname, count=1, tags=['cluster:webs', 'varnish_name:default'])
        else:
            aggregator.assert_metric(mname, count=0, tags=['cluster:webs', 'varnish_name:default'])


def test_exclusion_filter(aggregator, check, instance):
    instance['metrics_filter'] = ['^SMA.Transient.c_req']

    check.check(instance)
    for mname in common.COMMON_METRICS:
        if 'SMA.Transient.c_req' in mname:
            aggregator.assert_metric(mname, count=0, tags=['cluster:webs', 'varnish_name:default'])
        elif 'varnish.uptime' not in mname:
            aggregator.assert_metric(mname, count=1, tags=['cluster:webs', 'varnish_name:default'])


def test_version_metadata(aggregator, check, instance, datadog_agent):
    check.check_id = 'test:123'
    check.check(instance)

    raw_version = common.VARNISH_VERSION.replace('_', '.')
    major, minor, patch = raw_version.split('.')
    version_metadata = {
        'version.scheme': 'semver',
        'version.major': major,
        'version.minor': minor,
        'version.patch': patch,
        'version.raw': raw_version,
    }

    datadog_agent.assert_metadata('test:123', version_metadata)
