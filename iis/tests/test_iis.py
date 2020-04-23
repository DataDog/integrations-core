# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import re

import pytest
from datadog_test_libs.win.pdh_mocks import pdh_mocks_fixture  # noqa: F401

from datadog_checks.iis import IIS
from datadog_checks.iis.iis import DEFAULT_COUNTERS

from .common import (
    CHECK_NAME,
    INSTANCE,
    INVALID_HOST_INSTANCE,
    MINIMAL_INSTANCE,
    WIN_SERVICES_CONFIG,
    WIN_SERVICES_MINIMAL_CONFIG,
)


@pytest.mark.usefixtures('pdh_mocks_fixture')
def test_basic_check(aggregator):
    instance = MINIMAL_INSTANCE
    c = IIS(CHECK_NAME, {}, [instance])
    c.check(None)
    iis_host = c.get_iishost()

    site_tags = ['Default_Web_Site', 'Exchange_Back_End', 'Total']
    for metric_def in DEFAULT_COUNTERS:
        metric = metric_def[3]
        for site_tag in site_tags:
            aggregator.assert_metric(metric, tags=["site:{0}".format(site_tag), iis_host], count=1)

    for site_tag in site_tags:
        aggregator.assert_service_check('iis.site_up', IIS.OK, tags=["site:{0}".format(site_tag), iis_host], count=1)

    aggregator.assert_all_metrics_covered()


@pytest.mark.usefixtures('pdh_mocks_fixture')
def test_check_on_specific_websites(aggregator):
    instance = INSTANCE
    c = IIS(CHECK_NAME, {}, [instance])
    c.check(None)
    iis_host = c.get_iishost()

    site_tags = ['Default_Web_Site', 'Exchange_Back_End', 'Total']
    for metric_def in DEFAULT_COUNTERS:
        metric = metric_def[3]
        for site_tag in site_tags:
            aggregator.assert_metric(metric, tags=["site:{0}".format(site_tag), iis_host], count=1)

    for site_tag in site_tags:
        aggregator.assert_service_check('iis.site_up', IIS.OK, tags=["site:{0}".format(site_tag), iis_host], count=1)

    aggregator.assert_service_check(
        'iis.site_up', IIS.CRITICAL, tags=["site:{0}".format('Non_Existing_Website'), iis_host], count=1
    )

    aggregator.assert_all_metrics_covered()


@pytest.mark.usefixtures('pdh_mocks_fixture')
def test_service_check_with_invalid_host(aggregator):
    instance = INVALID_HOST_INSTANCE
    c = IIS(CHECK_NAME, {}, [instance])
    c.check(None)
    iis_host = c.get_iishost()

    aggregator.assert_service_check('iis.site_up', IIS.CRITICAL, tags=["site:{0}".format('Total'), iis_host])


@pytest.mark.usefixtures('pdh_mocks_fixture')
def test_check(aggregator):
    """
    Returns the right metrics and service checks
    """
    instance = WIN_SERVICES_CONFIG
    c = IIS(CHECK_NAME, {}, [instance])
    c.check(None)
    iis_host = c.get_iishost()

    # Test metrics
    # ... normalize site-names
    default_site_name = re.sub(r"[,\+\*\-/()\[\]{}\s]", "_", WIN_SERVICES_CONFIG['sites'][0])
    ok_site_name = re.sub(r"[,\+\*\-/()\[\]{}\s]", "_", WIN_SERVICES_CONFIG['sites'][1])
    fail_site_name = re.sub(r"[,\+\*\-/()\[\]{}\s]", "_", WIN_SERVICES_CONFIG['sites'][2])

    for site_name in [default_site_name, ok_site_name, 'Total']:
        for metric_def in DEFAULT_COUNTERS:
            mname = metric_def[3]
            aggregator.assert_metric(mname, tags=["mytag1", "mytag2", "site:{0}".format(site_name), iis_host], count=1)

        aggregator.assert_service_check(
            'iis.site_up', status=IIS.OK, tags=["mytag1", "mytag2", "site:{0}".format(site_name), iis_host], count=1
        )

    aggregator.assert_service_check(
        'iis.site_up',
        status=IIS.CRITICAL,
        tags=["mytag1", "mytag2", "site:{0}".format(fail_site_name), iis_host],
        count=1,
    )

    # Check completed with no warnings
    # self.assertFalse(logger.warning.called)

    aggregator.assert_all_metrics_covered()


@pytest.mark.usefixtures('pdh_mocks_fixture')
def test_check_without_sites_specified(aggregator):
    """
    Returns the right metrics and service checks for the `_Total` site
    """
    # Run check
    instance = WIN_SERVICES_MINIMAL_CONFIG
    c = IIS(CHECK_NAME, {}, [instance])
    c.check(None)
    iis_host = c.get_iishost()

    site_tags = ['Default_Web_Site', 'Exchange_Back_End', 'Total']
    for metric_def in DEFAULT_COUNTERS:
        mname = metric_def[3]

        for site_tag in site_tags:
            aggregator.assert_metric(mname, tags=["mytag1", "mytag2", "site:{0}".format(site_tag), iis_host], count=1)

    for site_tag in site_tags:
        aggregator.assert_service_check(
            'iis.site_up', status=IIS.OK, tags=["mytag1", "mytag2", "site:{0}".format(site_tag), iis_host], count=1
        )
    aggregator.assert_all_metrics_covered()
