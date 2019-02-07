# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import re

from datadog_checks.iis import IIS
from datadog_checks.iis.iis import DEFAULT_COUNTERS
from datadog_test_libs.win.pdh_mocks import pdh_mocks_fixture  # noqa F401

from .common import (
    CHECK_NAME,
    MINIMAL_INSTANCE,
    INSTANCE,
    INVALID_HOST_INSTANCE,
    WIN_SERVICES_MINIMAL_CONFIG,
    WIN_SERVICES_CONFIG
)


def test_basic_check(aggregator, pdh_mocks_fixture):  # noqa: F811
    instance = MINIMAL_INSTANCE
    c = IIS(CHECK_NAME, {}, {}, [instance])
    c.check(instance)

    site_tags = ['Default_Web_Site', 'Exchange_Back_End', 'Total']
    for metric_def in DEFAULT_COUNTERS:
        metric = metric_def[3]
        for site_tag in site_tags:
            aggregator.assert_metric(metric, tags=["site:{0}".format(site_tag)], count=1)

    for site_tag in site_tags:
        aggregator.assert_service_check('iis.site_up', IIS.OK,
                                        tags=["site:{0}".format(site_tag)], count=1)

    aggregator.assert_all_metrics_covered()


def test_check_on_specific_websites(aggregator, pdh_mocks_fixture):  # noqa: F811
    instance = INSTANCE
    c = IIS(CHECK_NAME, {}, {}, [instance])
    c.check(instance)

    site_tags = ['Default_Web_Site', 'Exchange_Back_End', 'Total']
    for metric_def in DEFAULT_COUNTERS:
        metric = metric_def[3]
        for site_tag in site_tags:
            aggregator.assert_metric(metric, tags=["site:{0}".format(site_tag)], count=1)

    for site_tag in site_tags:
        aggregator.assert_service_check('iis.site_up', IIS.OK,
                                        tags=["site:{0}".format(site_tag)], count=1)

    aggregator.assert_service_check('iis.site_up', IIS.CRITICAL,
                                    tags=["site:{0}".format('Non_Existing_Website')], count=1)

    aggregator.assert_all_metrics_covered()


def test_service_check_with_invalid_host(aggregator, pdh_mocks_fixture):  # noqa: F811
    instance = INVALID_HOST_INSTANCE
    c = IIS(CHECK_NAME, {}, {}, [instance])
    c.check(instance)

    aggregator.assert_service_check('iis.site_up', IIS.CRITICAL, tags=["site:{0}".format('Total')])


def test_check(aggregator, pdh_mocks_fixture):  # noqa: F811
    """
    Returns the right metrics and service checks
    """
    instance = WIN_SERVICES_CONFIG
    c = IIS(CHECK_NAME, {}, {}, [instance])
    c.check(instance)

    # Test metrics
    # ... normalize site-names
    default_site_name = re.sub(r"[,\+\*\-/()\[\]{}\s]", "_", WIN_SERVICES_CONFIG['sites'][0])
    ok_site_name = re.sub(r"[,\+\*\-/()\[\]{}\s]", "_", WIN_SERVICES_CONFIG['sites'][1])
    fail_site_name = re.sub(r"[,\+\*\-/()\[\]{}\s]", "_", WIN_SERVICES_CONFIG['sites'][2])

    for site_name in [default_site_name, ok_site_name, 'Total']:
        for metric_def in DEFAULT_COUNTERS:
            mname = metric_def[3]
            aggregator.assert_metric(mname, tags=["mytag1", "mytag2", "site:{0}".format(site_name)], count=1)

        aggregator.assert_service_check('iis.site_up', status=IIS.OK,
                                        tags=["mytag1", "mytag2", "site:{0}".format(site_name)], count=1)

    aggregator.assert_service_check('iis.site_up', status=IIS.CRITICAL,
                                    tags=["mytag1", "mytag2", "site:{0}".format(fail_site_name)], count=1)

    # Check completed with no warnings
    # self.assertFalse(logger.warning.called)

    aggregator.assert_all_metrics_covered()


def test_check_without_sites_specified(aggregator, pdh_mocks_fixture):  # noqa: F811
    """
    Returns the right metrics and service checks for the `_Total` site
    """
    # Run check
    instance = WIN_SERVICES_MINIMAL_CONFIG
    c = IIS(CHECK_NAME, {}, {}, [instance])
    c.check(instance)

    site_tags = ['Default_Web_Site', 'Exchange_Back_End', 'Total']
    for metric_def in DEFAULT_COUNTERS:
        mname = metric_def[3]

        for site_tag in site_tags:
            aggregator.assert_metric(mname, tags=["mytag1", "mytag2", "site:{0}".format(site_tag)], count=1)

    for site_tag in site_tags:
        aggregator.assert_service_check('iis.site_up', status=IIS.OK,
                                        tags=["mytag1", "mytag2", "site:{0}".format(site_tag)], count=1)
    aggregator.assert_all_metrics_covered()
