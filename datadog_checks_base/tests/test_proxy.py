# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import mock

from datadog_checks.checks import AgentCheck

PROXY_SETTINGS = {
    "http": 'http(s)://user:password@proxy_for_http:port',
    "https": 'http(s)://user:password@proxy_for_https:port',
    "no": None
}

NO_PROXY_SETTINGS = {
    "no": None
}

def test_use_proxy():
    with mock.patch('datadog_checks.checks.AgentCheck._get_requests_proxy', return_value=PROXY_SETTINGS):
        check = AgentCheck()
        assert check.get_instance_proxy({}, 'uri1/health') == PROXY_SETTINGS


def test_skip_proxy():
    with mock.patch('datadog_checks.checks.AgentCheck._get_requests_proxy', return_value=PROXY_SETTINGS):
        check = AgentCheck()
        assert check.get_instance_proxy({'skip_proxy': True}, 'uri/health') == NO_PROXY_SETTINGS


def test_deprecated_no_proxy():
    with mock.patch('datadog_checks.checks.AgentCheck._get_requests_proxy', return_value=PROXY_SETTINGS):
        check = AgentCheck()
        assert check.get_instance_proxy({'no_proxy': True}, 'uri/health') == NO_PROXY_SETTINGS
