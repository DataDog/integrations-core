# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# stdlib
import re

# 3p
from nose.plugins.attrib import attr
from mock import Mock

# project
from tests.checks.common import AgentCheckTest
from checks import AgentCheck
from tests.core.test_wmi import TestCommonWMI


MINIMAL_INSTANCE = {
    'host': '.',
}

INSTANCE = {
    'host': '.',
    'sites': ['Default Web Site', 'Test-Website-1', 'Non Existing Website'],
}

INVALID_HOST_INSTANCE = {
    'host': 'nonexistinghost'
}


@attr('windows')
@attr(requires='iis')
class IISTest(AgentCheckTest):
    CHECK_NAME = 'iis'

    IIS_METRICS = (
        'iis.uptime',
        # Network
        'iis.net.bytes_sent',
        'iis.net.bytes_rcvd',
        'iis.net.bytes_total',
        'iis.net.num_connections',
        'iis.net.files_sent',
        'iis.net.files_rcvd',
        'iis.net.connection_attempts',
        # HTTP Methods
        'iis.httpd_request_method.get',
        'iis.httpd_request_method.post',
        'iis.httpd_request_method.head',
        'iis.httpd_request_method.put',
        'iis.httpd_request_method.delete',
        'iis.httpd_request_method.options',
        'iis.httpd_request_method.trace',
        # Errors
        'iis.errors.not_found',
        'iis.errors.locked',
        # Users
        'iis.users.anon',
        'iis.users.nonanon',
        # Requests
        'iis.requests.cgi',
        'iis.requests.isapi',
    )

    def test_basic_check(self):
        self.run_check_twice({'instances': [MINIMAL_INSTANCE]})

        site_tags = ['Default_Web_Site', 'Test_Website_1', 'Total']
        for metric in self.IIS_METRICS:
            for site_tag in site_tags:
                self.assertMetric(metric, tags=["site:{0}".format(site_tag)], count=1)

        for site_tag in site_tags:
            self.assertServiceCheckOK('iis.site_up',
                                      tags=["site:{0}".format(site_tag)], count=1)

        self.coverage_report()

    def test_check_on_specific_websites(self):
        self.run_check_twice({'instances': [INSTANCE]})

        site_tags = ['Default_Web_Site', 'Test_Website_1', 'Total']
        for metric in self.IIS_METRICS:
            for site_tag in site_tags:
                self.assertMetric(metric, tags=["site:{0}".format(site_tag)], count=1)

        for site_tag in site_tags:
            self.assertServiceCheckOK('iis.site_up',
                                      tags=["site:{0}".format(site_tag)], count=1)

        self.assertServiceCheckCritical('iis.site_up',
                                        tags=["site:{0}".format('Non_Existing_Website')], count=1)

        self.coverage_report()

    def test_service_check_with_invalid_host(self):
        self.run_check({'instances': [INVALID_HOST_INSTANCE]})

        self.assertServiceCheckCritical('iis.site_up', tags=["site:{0}".format('Total')])

        self.coverage_report()

@attr('windows')
@attr(requires='windows')
class IISTestCase(AgentCheckTest, TestCommonWMI):
    CHECK_NAME = 'iis'

    WIN_SERVICES_MINIMAL_CONFIG = {
        'host': ".",
        'tags': ["mytag1", "mytag2"]
    }

    WIN_SERVICES_CONFIG = {
        'host': ".",
        'tags': ["mytag1", "mytag2"],
        'sites': ["Default Web Site", "Working site", "Failing site"]
    }

    IIS_METRICS = [
        'iis.uptime',
        # Network
        'iis.net.bytes_sent',
        'iis.net.bytes_rcvd',
        'iis.net.bytes_total',
        'iis.net.num_connections',
        'iis.net.files_sent',
        'iis.net.files_rcvd',
        'iis.net.connection_attempts',
        # HTTP Methods
        'iis.httpd_request_method.get',
        'iis.httpd_request_method.post',
        'iis.httpd_request_method.head',
        'iis.httpd_request_method.put',
        'iis.httpd_request_method.delete',
        'iis.httpd_request_method.options',
        'iis.httpd_request_method.trace',
        # Errors
        'iis.errors.not_found',
        'iis.errors.locked',
        # Users
        'iis.users.anon',
        'iis.users.nonanon',
        # Requests
        'iis.requests.cgi',
        'iis.requests.isapi',
    ]

    def test_check(self):
        """
        Returns the right metrics and service checks
        """
        # Set up & run the check
        config = {
            'instances': [self.WIN_SERVICES_CONFIG]
        }
        logger = Mock()

        self.run_check_twice(config, mocks={'log': logger})

        # Test metrics
        # ... normalize site-names
        default_site_name = re.sub(r"[,\+\*\-/()\[\]{}\s]", "_", config['instances'][0]['sites'][0])
        ok_site_name = re.sub(r"[,\+\*\-/()\[\]{}\s]", "_", config['instances'][0]['sites'][1])
        fail_site_name = re.sub(r"[,\+\*\-/()\[\]{}\s]", "_", config['instances'][0]['sites'][2])

        for site_name in [default_site_name, ok_site_name]:
            for mname in self.IIS_METRICS:
                self.assertMetric(mname, tags=["mytag1", "mytag2", "site:{0}".format(site_name)], count=1)

            self.assertServiceCheck('iis.site_up', status=AgentCheck.OK,
                                    tags=["site:{0}".format(site_name)], count=1)

        self.assertServiceCheck('iis.site_up', status=AgentCheck.CRITICAL,
                                tags=["site:{0}".format(fail_site_name)], count=1)

        # Check completed with no warnings
        self.assertFalse(logger.warning.called)

        self.coverage_report()

    def test_check_2008(self):
        """
        Returns the right metrics and service checks for 2008 IIS
        """
        # Run check
        config = {
            'instances': [self.WIN_SERVICES_CONFIG]
        }
        config['instances'][0]['is_2008'] = True

        self.run_check_twice(config)

        # Test metrics
        query = ("Select ServiceUptime,TotalBytesSent,TotalBytesReceived,TotalBytesTransfered,"
                 "CurrentConnections,TotalFilesSent,TotalFilesReceived,TotalConnectionAttemptsAllInstances,"
                 "TotalGetRequests,TotalPostRequests,TotalHeadRequests,TotalPutRequests,TotalDeleteRequests,"
                 "TotalOptionsRequests,TotalTraceRequests,TotalNotFoundErrors,TotalLockedErrors,TotalAnonymousUsers,"
                 "TotalNonAnonymousUsers,TotalCGIRequests,TotalISAPIExtensionRequests"
                 " from Win32_PerfFormattedData_W3SVC_WebService WHERE "
                 "( Name = 'Failing site' ) OR ( Name = 'Working site' ) OR ( Name = 'Default Web Site' )")

        self.assertWMIQuery(query)

        # Normalize site-names
        default_site_name = re.sub(r"[,\+\*\-/()\[\]{}\s]", "_", config['instances'][0]['sites'][0])
        ok_site_name = re.sub(r"[,\+\*\-/()\[\]{}\s]", "_", config['instances'][0]['sites'][1])
        fail_site_name = re.sub(r"[,\+\*\-/()\[\]{}\s]", "_", config['instances'][0]['sites'][2])

        for site_name in [default_site_name, ok_site_name]:
            for mname in self.IIS_METRICS:
                self.assertMetric(mname, tags=["mytag1", "mytag2", "site:{0}".format(site_name)], count=1)

            self.assertServiceCheck('iis.site_up', status=AgentCheck.OK,
                                    tags=["site:{0}".format(site_name)], count=1)

        self.assertServiceCheck('iis.site_up', status=AgentCheck.CRITICAL,
                                tags=["site:{0}".format(fail_site_name)], count=1)

        self.coverage_report()

    def test_check_without_sites_specified(self):
        """
        Returns the right metrics and service checks for the `_Total` site
        """
        # Run check
        config = {
            'instances': [self.WIN_SERVICES_MINIMAL_CONFIG]
        }
        self.run_check_twice(config)

        for mname in self.IIS_METRICS:
            self.assertMetric(mname, tags=["mytag1", "mytag2"], count=1)

        self.assertServiceCheck('iis.site_up', status=AgentCheck.OK,
                                tags=["site:{0}".format('Total')], count=1)
        self.coverage_report()
