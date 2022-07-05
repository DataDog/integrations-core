# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.varnish import Varnish

from . import common

pytestmark = [pytest.mark.usefixtures('dd_environment'), pytest.mark.integration]


def test_check(aggregator, instance, dd_run_check):
    check = Varnish(common.CHECK_NAME, {}, [instance])
    dd_run_check(check)

    if common.VARNISH_VERSION.startswith("5"):
        metrics_to_check = common.COMMON_METRICS + common.METRICS_5
    else:
        metrics_to_check = common.COMMON_METRICS + common.METRICS_6

    for mname in metrics_to_check:
        aggregator.assert_metric(mname, count=1, tags=['varnish_cluster:webs', 'varnish_name:default'])

    aggregator.assert_all_metrics_covered()
    metadata_metrics = get_metadata_metrics()
    aggregator.assert_metrics_using_metadata(metadata_metrics, check_submission_type=True)


def test_check_invalid_varnishadm(aggregator, instance, dd_run_check):
    # Note: this test may prompt you to enter a password when locally, if so, enter anything and it will pass
    instance['varnishadm'] = 'invalid-thing'
    check = Varnish(common.CHECK_NAME, {}, [instance])
    dd_run_check(check)

    aggregator.assert_service_check(Varnish.SERVICE_CHECK_NAME, count=0)


def test_inclusion_filter(aggregator, instance, dd_run_check):
    instance['metrics_filter'] = ['SMA.*']

    check = Varnish(common.CHECK_NAME, {}, [instance])
    dd_run_check(check)
    for mname in common.COMMON_METRICS:
        if 'SMA.' in mname:
            aggregator.assert_metric(mname, count=1, tags=['varnish_cluster:webs', 'varnish_name:default'])
        else:
            aggregator.assert_metric(mname, count=0, tags=['varnish_cluster:webs', 'varnish_name:default'])


def test_exclusion_filter(aggregator, instance, dd_run_check):
    instance['metrics_filter'] = ['^SMA.Transient.c_req']

    check = Varnish(common.CHECK_NAME, {}, [instance])
    dd_run_check(check)
    for mname in common.COMMON_METRICS:
        if 'SMA.Transient.c_req' in mname:
            aggregator.assert_metric(mname, count=0, tags=['varnish_cluster:webs', 'varnish_name:default'])
        elif 'varnish.uptime' not in mname:
            aggregator.assert_metric(mname, count=1, tags=['varnish_cluster:webs', 'varnish_name:default'])


def test_version_metadata(aggregator, instance, datadog_agent):
    check = Varnish(common.CHECK_NAME, {}, [instance])
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
