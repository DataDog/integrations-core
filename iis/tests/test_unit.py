# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base.constants import ServiceCheck
from datadog_checks.dev.testing import requires_py3
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.iis import IIS

from .common import DEFAULT_COUNTERS, PERFORMANCE_OBJECTS

pytestmark = [requires_py3]


def get_metrics_data():
    app_pool_metrics_data = []
    site_metrics_data = []

    for counter_data in DEFAULT_COUNTERS:
        object_name = counter_data[0]
        if object_name == 'APP_POOL_WAS':
            app_pool_metrics_data.append((counter_data[3], counter_data[4]))
        elif object_name == 'Web Service':
            site_metrics_data.append((counter_data[3], counter_data[4]))

    return app_pool_metrics_data, site_metrics_data


def test_check_all(aggregator, dd_default_hostname, dd_run_check, mock_performance_objects):
    mock_performance_objects(PERFORMANCE_OBJECTS)
    check = IIS('iis', {}, [{'host': dd_default_hostname}])
    check.hostname = dd_default_hostname
    dd_run_check(check)

    global_tags = ['iis_host:{}'.format(dd_default_hostname)]
    aggregator.assert_service_check('iis.windows.perf.health', ServiceCheck.OK, count=1, tags=global_tags)

    app_pool_metrics_data, site_metrics_data = get_metrics_data()

    for app_pool, value in (('foo-pool', 9000), ('bar-pool', 0)):
        tags = ['app_pool:{}'.format(app_pool)]
        tags.extend(global_tags)
        aggregator.assert_service_check(
            'iis.app_pool_up', ServiceCheck.CRITICAL if value == 0 else ServiceCheck.OK, count=1, tags=tags
        )

        for metric_name, metric_type in app_pool_metrics_data:
            aggregator.assert_metric(
                metric_name, value, metric_type=getattr(aggregator, metric_type.upper()), count=1, tags=tags
            )

    for site, value in (('foo.site', 9000), ('bar.site', 0)):
        tags = ['site:{}'.format(site)]
        tags.extend(global_tags)
        aggregator.assert_service_check(
            'iis.site_up', ServiceCheck.CRITICAL if value == 0 else ServiceCheck.OK, count=1, tags=tags
        )

        for metric_name, metric_type in site_metrics_data:
            aggregator.assert_metric(
                metric_name, value, metric_type=getattr(aggregator, metric_type.upper()), count=1, tags=tags
            )

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


def test_check_specific(aggregator, dd_default_hostname, dd_run_check, mock_performance_objects):
    mock_performance_objects(PERFORMANCE_OBJECTS)
    check = IIS(
        'iis',
        {},
        [
            {
                'host': dd_default_hostname,
                'app_pools': ['foo-pool', 'missing-pool'],
                'sites': ['foo.site', 'missing.site'],
            }
        ],
    )
    check.hostname = dd_default_hostname
    dd_run_check(check)

    global_tags = ['iis_host:{}'.format(dd_default_hostname)]
    aggregator.assert_service_check('iis.windows.perf.health', ServiceCheck.OK, count=1, tags=global_tags)

    app_pool_metrics_data, site_metrics_data = get_metrics_data()

    for app_pool, value in (('foo-pool', 9000), ('missing-pool', 0)):
        tags = ['app_pool:{}'.format(app_pool)]
        tags.extend(global_tags)
        aggregator.assert_service_check(
            'iis.app_pool_up', ServiceCheck.CRITICAL if value == 0 else ServiceCheck.OK, count=1, tags=tags
        )

        for metric_name, metric_type in app_pool_metrics_data:
            aggregator.assert_metric_has_tag(metric_name, 'app_pool:bar-pool', count=0)
            if not app_pool.startswith('missing'):
                aggregator.assert_metric(
                    metric_name, value, metric_type=getattr(aggregator, metric_type.upper()), count=1, tags=tags
                )

    for site, value in (('foo.site', 9000), ('missing.site', 0)):
        tags = ['site:{}'.format(site)]
        tags.extend(global_tags)
        aggregator.assert_service_check(
            'iis.site_up', ServiceCheck.CRITICAL if value == 0 else ServiceCheck.OK, count=1, tags=tags
        )

        for metric_name, metric_type in site_metrics_data:
            aggregator.assert_metric_has_tag(metric_name, 'site:bar.site', count=0)
            if not site.startswith('missing'):
                aggregator.assert_metric(
                    metric_name, value, metric_type=getattr(aggregator, metric_type.upper()), count=1, tags=tags
                )

    aggregator.assert_all_metrics_covered()


def test_check_include_patterns(aggregator, dd_default_hostname, dd_run_check, mock_performance_objects):
    mock_performance_objects(PERFORMANCE_OBJECTS)
    check = IIS(
        'iis',
        {},
        [{'host': dd_default_hostname, 'app_pools': {'include': ['^foo']}, 'sites': {'include': ['^foo']}}],
    )
    check.hostname = dd_default_hostname
    dd_run_check(check)

    global_tags = ['iis_host:{}'.format(dd_default_hostname)]
    aggregator.assert_service_check('iis.windows.perf.health', ServiceCheck.OK, count=1, tags=global_tags)

    app_pool_metrics_data, site_metrics_data = get_metrics_data()

    for app_pool, value in (('foo-pool', 9000),):
        tags = ['app_pool:{}'.format(app_pool)]
        tags.extend(global_tags)
        aggregator.assert_service_check(
            'iis.app_pool_up', ServiceCheck.CRITICAL if value == 0 else ServiceCheck.OK, count=1, tags=tags
        )

        for metric_name, metric_type in app_pool_metrics_data:
            aggregator.assert_metric_has_tag(metric_name, 'app_pool:bar-pool', count=0)
            aggregator.assert_metric(
                metric_name, value, metric_type=getattr(aggregator, metric_type.upper()), count=1, tags=tags
            )

    for site, value in (('foo.site', 9000),):
        tags = ['site:{}'.format(site)]
        tags.extend(global_tags)
        aggregator.assert_service_check(
            'iis.site_up', ServiceCheck.CRITICAL if value == 0 else ServiceCheck.OK, count=1, tags=tags
        )

        for metric_name, metric_type in site_metrics_data:
            aggregator.assert_metric_has_tag(metric_name, 'site:bar.site', count=0)
            aggregator.assert_metric(
                metric_name, value, metric_type=getattr(aggregator, metric_type.upper()), count=1, tags=tags
            )

    aggregator.assert_all_metrics_covered()


def test_check_exclude_patterns(aggregator, dd_default_hostname, dd_run_check, mock_performance_objects):
    mock_performance_objects(PERFORMANCE_OBJECTS)
    check = IIS(
        'iis',
        {},
        [{'host': dd_default_hostname, 'app_pools': {'exclude': ['^bar']}, 'sites': {'exclude': ['^bar']}}],
    )
    check.hostname = dd_default_hostname
    dd_run_check(check)

    global_tags = ['iis_host:{}'.format(dd_default_hostname)]
    aggregator.assert_service_check('iis.windows.perf.health', ServiceCheck.OK, count=1, tags=global_tags)

    app_pool_metrics_data, site_metrics_data = get_metrics_data()

    for app_pool, value in (('foo-pool', 9000),):
        tags = ['app_pool:{}'.format(app_pool)]
        tags.extend(global_tags)
        aggregator.assert_service_check(
            'iis.app_pool_up', ServiceCheck.CRITICAL if value == 0 else ServiceCheck.OK, count=1, tags=tags
        )

        for metric_name, metric_type in app_pool_metrics_data:
            aggregator.assert_metric_has_tag(metric_name, 'app_pool:bar-pool', count=0)
            aggregator.assert_metric(
                metric_name, value, metric_type=getattr(aggregator, metric_type.upper()), count=1, tags=tags
            )

    for site, value in (('foo.site', 9000),):
        tags = ['site:{}'.format(site)]
        tags.extend(global_tags)
        aggregator.assert_service_check(
            'iis.site_up', ServiceCheck.CRITICAL if value == 0 else ServiceCheck.OK, count=1, tags=tags
        )

        for metric_name, metric_type in site_metrics_data:
            aggregator.assert_metric_has_tag(metric_name, 'site:bar.site', count=0)
            aggregator.assert_metric(
                metric_name, value, metric_type=getattr(aggregator, metric_type.upper()), count=1, tags=tags
            )

    aggregator.assert_all_metrics_covered()
