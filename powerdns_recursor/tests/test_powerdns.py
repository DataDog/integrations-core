# (C) Datadog, Inc. 2010-2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import pytest
import os
import subprocess
import requests
import time
import logging

from datadog_checks.powerdns_recursor import PowerDNSRecursorCheck

from .common import HOST, PORT, CONFIG, HERE
from .metrics import GAUGE_METRICS, RATE_METRICS, GAUGE_METRICS_V4, RATE_METRICS_V4, METRIC_FORMAT

CHECK_NAME = 'powerdns_recursor'

log = logging.getLogger('test_apache')


def wait_for_powerdns():
    base_url = "http://{}:{}".format(HOST, PORT)
    for _ in xrange(0, 100):
        res = None
        try:
            res = requests.get(base_url)
            res.raise_for_status
            return
        except Exception as e:
            log.info("exception: {0} res: {1}".format(e, res))
            time.sleep(2)
    raise Exception("Cannot start up apache")


@pytest.fixture(scope="session")
def spin_up_powerdns():
    env = os.environ
    pdns_version = env['POWERDNS_VERSION']
    pdns_tag = 'powerdns_recursor_' + pdns_version.replace('.', '_')
    powerdns_image = "datadog/docker-library:{0}".format(pdns_tag)
    env['POWERDNS_IMAGE'] = powerdns_image

    env['APACHE_CONFIG'] = os.path.join(HERE, 'compose', 'recursor.conf')
    args = [
        "docker-compose",
        "-f", os.path.join(HERE, 'compose', 'powerdns.yaml')
    ]
    subprocess.check_call(args + ["up", "-d", "--build"], env=env)
    wait_for_powerdns()
    time.sleep(20)
    yield
    subprocess.check_call(args + ["down"], env=env)


@pytest.fixture
def aggregator():
    from datadog_checks.stubs import aggregator
    aggregator.reset()
    return aggregator


def test_check(aggregator, spin_up_powerdns):
    assert True

# def test_check(self):
#     service_check_tags = ['recursor_host:127.0.0.1', 'recursor_port:8082']
#
#     # get version and test v3 first.
#     version = _get_pdns_version()
#     if version == 3:
#         run_check_twice(CONFIG)
#
#         # Assert metrics
#         for metric in GAUGE_METRICS:
#             assertMetric(METRIC_FORMAT.format(metric), tags=[])
#
#         for metric in self.RATE_METRICS:
#             assertMetric(METRIC_FORMAT.format(metric), tags=[])
#
#         self.assertServiceCheckOK('powerdns.recursor.can_connect', tags=service_check_tags)
#         self.coverage_report()
#
#     elif version == 4:
#         # copy the configuration and set the version to 4
#         config = self.config.copy()
#         config['instances'][0]['version'] = 4
#         self.run_check_twice(config)
#
#         # Assert metrics
#         for metric in self.GAUGE_METRICS + self.GAUGE_METRICS_V4:
#             self.assertMetric(self.METRIC_FORMAT.format(metric), tags=[])
#
#         for metric in self.RATE_METRICS + self.RATE_METRICS_V4:
#             self.assertMetric(self.METRIC_FORMAT.format(metric), tags=[])
#
#         self.assertServiceCheckOK('powerdns.recursor.can_connect', tags=service_check_tags)
#
#         self.coverage_report()
#     else:
#         print("powerdns_recursor unknown version.")
#         self.assertServiceCheckCritical('powerdns.recursor.can_connect', tags=service_check_tags)
#
# def test_tags(self):
#     version = self._get_pdns_version()
#     config = self.config.copy()
#     tags = ['foo:bar']
#     config['instances'][0]['tags'] = ['foo:bar']
#     if version == 3:
#         self.run_check_twice(config)
#
#         # Assert metrics v3
#         for metric in self.GAUGE_METRICS:
#             self.assertMetric(self.METRIC_FORMAT.format(metric), tags=tags)
#
#         for metric in self.RATE_METRICS:
#             self.assertMetric(self.METRIC_FORMAT.format(metric), tags=tags)
#
#     elif version == 4:
#         config['instances'][0]['version'] = 4
#         self.run_check_twice(config)
#
#         # Assert metrics v3
#         for metric in self.GAUGE_METRICS + self.GAUGE_METRICS_V4:
#             self.assertMetric(self.METRIC_FORMAT.format(metric), tags=tags)
#
#         for metric in self.RATE_METRICS + self.RATE_METRICS_V4:
#             self.assertMetric(self.METRIC_FORMAT.format(metric), tags=tags)
#
#     service_check_tags = ['recursor_host:127.0.0.1', 'recursor_port:8082']
#     self.assertServiceCheckOK('powerdns.recursor.can_connect', tags=service_check_tags)
#
#     self.coverage_report()
#
# def test_bad_config(self):
#     config = self.config.copy()
#     config['instances'][0]['port'] = 1111
#     service_check_tags = ['recursor_host:127.0.0.1', 'recursor_port:1111']
#     self.assertRaises(
#         Exception,
#         lambda: self.run_check(config)
#     )
#     self.assertServiceCheckCritical('powerdns.recursor.can_connect', tags=service_check_tags)
#     self.coverage_report()
#
# def test_bad_api_key(self):
#     config = self.config.copy()
#     config['instances'][0]['api_key'] = 'nope'
#     service_check_tags = ['recursor_host:127.0.0.1', 'recursor_port:8082']
#     self.assertRaises(
#         Exception,
#         lambda: self.run_check(config)
#     )
#     self.assertServiceCheckCritical('powerdns.recursor.can_connect', tags=service_check_tags)
#     self.coverage_report()
#
# def test_very_bad_config(self):
#     for config in [{}, {"host": "localhost"}, {"port": 1000}, {"host": "localhost", "port": 1000}]:
#         self.assertRaises(
#             Exception,
#             lambda: self.run_check({"instances": [config]})
#         )
#     self.coverage_report()
#
# def _get_pdns_version(self):
#     headers = {"X-API-Key": self.config['instances'][0]['api_key']}
#     url = "http://{}:{}/api/v1/servers/localhost/statistics".format(self.config['instances'][0]['host'],
#                                                                     self.config['instances'][0]['port'])
#     request = requests.get(url, headers=headers)
#     if request.status_code == 404:
#         return 3
#     else:
#         return 4
