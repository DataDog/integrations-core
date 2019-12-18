# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from . import common

pytestmark = [pytest.mark.usefixtures('dd_environment'), pytest.mark.integration]


def test_check(aggregator, check, instance):
    check.check(instance)
    for mname in common.COMMON_METRICS:
        aggregator.assert_metric(mname, count=1, tags=['cluster:webs', 'varnish_name:default'])


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
