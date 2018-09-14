# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import pytest
import re
from datadog_checks.stubs import aggregator
from datadog_checks.iis import IIS
from datadog_checks.iis.iis import DEFAULT_COUNTERS
# for reasons unknown, flake8 says that pdh_mocks_fixture is unused, even though
# it's used below.  noqa to suppress that error.
from datadog_test_libs.win.pdh_mocks import pdh_mocks_fixture, initialize_pdh_tests  # noqa: F401


@pytest.fixture
def Aggregator():
    aggregator.reset()
    return aggregator


CHECK_NAME = 'iis'
MINIMAL_INSTANCE = {
    'host': '.',
}

INSTANCE = {
    'host': '.',
    'sites': ['Default Web Site', 'Exchange Back End', 'Non Existing Website'],
}

INVALID_HOST_INSTANCE = {
    'host': 'nonexistinghost'
}


# flake8 then says this is a redefinition of unused, which it's not.
@pytest.mark.usefixtures("pdh_mocks_fixture")  # noqa: F811
def test_basic_check(Aggregator, pdh_mocks_fixture):
    initialize_pdh_tests()
    instance = MINIMAL_INSTANCE
    c = IIS(CHECK_NAME, {}, {}, [instance])
    c.check(instance)

    site_tags = ['Default_Web_Site', 'Exchange_Back_End', 'Total']
    for metric_def in DEFAULT_COUNTERS:
        metric = metric_def[3]
        for site_tag in site_tags:
            Aggregator.assert_metric(metric, tags=["site:{0}".format(site_tag)], count=1)

    for site_tag in site_tags:
        Aggregator.assert_service_check('iis.site_up', IIS.OK,
                                        tags=["site:{0}".format(site_tag)], count=1)

    Aggregator.assert_all_metrics_covered()


# flake8 then says this is a redefinition of unused, which it's not.
@pytest.mark.usefixtures("pdh_mocks_fixture")  # noqa: F811
def test_check_on_specific_websites(Aggregator, pdh_mocks_fixture):
    initialize_pdh_tests()
    instance = INSTANCE
    c = IIS(CHECK_NAME, {}, {}, [instance])
    c.check(instance)

    site_tags = ['Default_Web_Site', 'Exchange_Back_End', 'Total']
    for metric_def in DEFAULT_COUNTERS:
        metric = metric_def[3]
        for site_tag in site_tags:
            Aggregator.assert_metric(metric, tags=["site:{0}".format(site_tag)], count=1)

    for site_tag in site_tags:
        Aggregator.assert_service_check('iis.site_up', IIS.OK,
                                        tags=["site:{0}".format(site_tag)], count=1)

    Aggregator.assert_service_check('iis.site_up', IIS.CRITICAL,
                                    tags=["site:{0}".format('Non_Existing_Website')], count=1)

    Aggregator.assert_all_metrics_covered()


# flake8 then says this is a redefinition of unused, which it's not.
@pytest.mark.usefixtures("pdh_mocks_fixture")  # noqa: F811
def test_service_check_with_invalid_host(Aggregator, pdh_mocks_fixture):
    initialize_pdh_tests()
    instance = INVALID_HOST_INSTANCE
    c = IIS(CHECK_NAME, {}, {}, [instance])
    c.check(instance)

    Aggregator.assert_service_check('iis.site_up', IIS.CRITICAL, tags=["site:{0}".format('Total')])


WIN_SERVICES_MINIMAL_CONFIG = {
    'host': ".",
    'tags': ["mytag1", "mytag2"]
}

WIN_SERVICES_CONFIG = {
    'host': ".",
    'tags': ["mytag1", "mytag2"],
    'sites': ["Default Web Site", "Exchange Back End", "Failing site"]
}


# flake8 then says this is a redefinition of unused, which it's not.
@pytest.mark.usefixtures("pdh_mocks_fixture")  # noqa: F811
def test_check(Aggregator, pdh_mocks_fixture):
    """
    Returns the right metrics and service checks
    """
    # Set up & run the check
    config = {
        'instances': [WIN_SERVICES_CONFIG]
    }
    initialize_pdh_tests()
    instance = WIN_SERVICES_CONFIG
    c = IIS(CHECK_NAME, {}, {}, [instance])
    c.check(instance)

    # Test metrics
    # ... normalize site-names
    default_site_name = re.sub(r"[,\+\*\-/()\[\]{}\s]", "_", config['instances'][0]['sites'][0])
    ok_site_name = re.sub(r"[,\+\*\-/()\[\]{}\s]", "_", config['instances'][0]['sites'][1])
    fail_site_name = re.sub(r"[,\+\*\-/()\[\]{}\s]", "_", config['instances'][0]['sites'][2])

    for site_name in [default_site_name, ok_site_name, 'Total']:
        for metric_def in DEFAULT_COUNTERS:
            mname = metric_def[3]
            Aggregator.assert_metric(mname, tags=["mytag1", "mytag2", "site:{0}".format(site_name)], count=1)

        Aggregator.assert_service_check('iis.site_up', status=IIS.OK,
                                        tags=["mytag1", "mytag2", "site:{0}".format(site_name)], count=1)

    Aggregator.assert_service_check('iis.site_up', status=IIS.CRITICAL,
                                    tags=["mytag1", "mytag2", "site:{0}".format(fail_site_name)], count=1)

    # Check completed with no warnings
    # self.assertFalse(logger.warning.called)

    Aggregator.assert_all_metrics_covered()


# flake8 then says this is a redefinition of unused, which it's not.
@pytest.mark.usefixtures("pdh_mocks_fixture")  # noqa: F811
def test_check_without_sites_specified(Aggregator, pdh_mocks_fixture):
    """
    Returns the right metrics and service checks for the `_Total` site
    """
    # Run check
    initialize_pdh_tests()
    instance = WIN_SERVICES_MINIMAL_CONFIG
    c = IIS(CHECK_NAME, {}, {}, [instance])
    c.check(instance)

    site_tags = ['Default_Web_Site', 'Exchange_Back_End', 'Total']
    for metric_def in DEFAULT_COUNTERS:
        mname = metric_def[3]

        for site_tag in site_tags:
            Aggregator.assert_metric(mname, tags=["mytag1", "mytag2", "site:{0}".format(site_tag)], count=1)

    for site_tag in site_tags:
        Aggregator.assert_service_check('iis.site_up', status=IIS.OK,
                                        tags=["mytag1", "mytag2", "site:{0}".format(site_tag)], count=1)
    Aggregator.assert_all_metrics_covered()
