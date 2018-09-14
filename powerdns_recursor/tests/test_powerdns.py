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

import common
import metrics

CHECK_NAME = 'powerdns_recursor'

log = logging.getLogger('test_apache')


def wait_for_powerdns():
    base_url = "http://{}:{}".format(common.HOST, common.PORT)
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
    pdns_underscore_version = pdns_version.replace('.', '_')
    pdns_tag = "powerdns_recursor_{0}".format(pdns_underscore_version)
    powerdns_image = "datadog/docker-library:{0}".format(pdns_tag)
    env['POWERDNS_IMAGE'] = powerdns_image

    env['POWERDNS_CONFIG'] = os.path.join(common.HERE, 'compose', 'recursor.conf')
    args = [
        "docker-compose",
        "-f", os.path.join(common.HERE, 'compose', 'powerdns.yaml')
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


def _get_pdns_version():
    headers = {"X-API-Key": common.CONFIG['api_key']}
    url = "http://{}:{}/api/v1/servers/localhost/statistics".format(common.HOST, common.PORT)
    request = requests.get(url, headers=headers)
    if request.status_code == 404:
        return 3
    else:
        return 4


def test_check(aggregator, spin_up_powerdns):
    service_check_tags = common._config_sc_tags(common.CONFIG)

    # get version and test v3 first.
    version = _get_pdns_version()
    pdns_check = PowerDNSRecursorCheck(CHECK_NAME, {}, {})
    if version == 3:
        pdns_check.check(common.CONFIG)

        # Assert metrics
        for metric in metrics.GAUGE_METRICS:
            aggregator.assert_metric(metrics.METRIC_FORMAT.format(metric), tags=[], count=1)

        for metric in metrics.RATE_METRICS:
            aggregator.assert_metric(metrics.METRIC_FORMAT.format(metric), tags=[], count=1)

        aggregator.assert_service_check('powerdns.recursor.can_connect',
                                        status=PowerDNSRecursorCheck.OK,
                                        tags=service_check_tags)
        assert aggregator.metrics_asserted_pct == 100.0

    elif version == 4:
        pdns_check.check(common.CONFIG_V4)

        # Assert metrics
        for metric in metrics.GAUGE_METRICS + metrics.GAUGE_METRICS_V4:
            aggregator.assert_metric(metrics.METRIC_FORMAT.format(metric), tags=[], count=1)

        for metric in metrics.RATE_METRICS + metrics.RATE_METRICS_V4:
            aggregator.assert_metric(metrics.METRIC_FORMAT.format(metric), tags=[], count=1)

        aggregator.assert_service_check('powerdns.recursor.can_connect',
                                        status=PowerDNSRecursorCheck.OK,
                                        tags=service_check_tags)
        assert aggregator.metrics_asserted_pct == 100.0
    else:
        print("powerdns_recursor unknown version.")
        aggregator.assert_service_check('powerdns.recursor.can_connect',
                                        status=PowerDNSRecursorCheck.CRITICAL,
                                        tags=service_check_tags)


def test_tags(aggregator, spin_up_powerdns):
    version = _get_pdns_version()

    pdns_check = PowerDNSRecursorCheck(CHECK_NAME, {}, {})
    tags = ['foo:bar']
    if version == 3:
        config = common.CONFIG.copy()
        config['tags'] = ['foo:bar']
        pdns_check.check(config)

        # Assert metrics v3
        for metric in metrics.GAUGE_METRICS:
            aggregator.assert_metric(metrics.METRIC_FORMAT.format(metric), tags=tags, count=1)

        for metric in metrics.RATE_METRICS:
            aggregator.assert_metric(metrics.METRIC_FORMAT.format(metric), tags=tags, count=1)

    elif version == 4:
        config = common.CONFIG_V4.copy()
        config['tags'] = ['foo:bar']
        pdns_check.check(config)

        # Assert metrics v3
        for metric in metrics.GAUGE_METRICS + metrics.GAUGE_METRICS_V4:
            aggregator.assert_metric(metrics.METRIC_FORMAT.format(metric), tags=tags, count=1)

        for metric in metrics.RATE_METRICS + metrics.RATE_METRICS_V4:
            aggregator.assert_metric(metrics.METRIC_FORMAT.format(metric), tags=tags, count=1)

    service_check_tags = common._config_sc_tags(common.CONFIG)
    aggregator.assert_service_check('powerdns.recursor.can_connect',
                                    status=PowerDNSRecursorCheck.OK,
                                    tags=service_check_tags+tags)

    aggregator.assert_all_metrics_covered()


def test_bad_config(aggregator):
    pdns_check = PowerDNSRecursorCheck(CHECK_NAME, {}, {})
    with pytest.raises(Exception):
        pdns_check.check(common.BAD_CONFIG)

    service_check_tags = common._config_sc_tags(common.BAD_CONFIG)
    aggregator.assert_service_check('powerdns.recursor.can_connect',
                                    status=PowerDNSRecursorCheck.CRITICAL,
                                    tags=service_check_tags)
    assert len(aggregator._metrics) == 0


def test_bad_api_key(aggregator, spin_up_powerdns):
    pdns_check = PowerDNSRecursorCheck(CHECK_NAME, {}, {})
    with pytest.raises(Exception):
        pdns_check.check(common.BAD_API_KEY_CONFIG)

    service_check_tags = common._config_sc_tags(common.BAD_API_KEY_CONFIG)
    aggregator.assert_service_check('powerdns.recursor.can_connect',
                                    status=PowerDNSRecursorCheck.CRITICAL,
                                    tags=service_check_tags)
    assert len(aggregator._metrics) == 0


def test_very_bad_config(aggregator):
    pdns_check = PowerDNSRecursorCheck(CHECK_NAME, {}, {})
    for config in [{}, {"host": "localhost"}, {"port": 1000}, {"host": "localhost", "port": 1000}]:
        with pytest.raises(Exception):
            pdns_check.check(common.BAD_API_KEY_CONFIG)

    assert len(aggregator._metrics) == 0
