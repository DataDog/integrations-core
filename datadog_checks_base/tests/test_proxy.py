# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import mock
import pytest
import requests
from requests.exceptions import ConnectTimeout, ProxyError

from datadog_checks.checks import AgentCheck

PROXY_SETTINGS = {
    'http': 'http(s)://user:password@proxy_for_http:port',
    'https': 'http(s)://user:password@proxy_for_https:port',
    'no': None
}
SKIP_PROXY_SETTINGS = {
    'http': '',
    'https': '',
    'no': None
}
NO_PROXY_DD_CONFIG_SETTINGS = {
    'http': 'http://1.2.3.4:567',
    'https': 'https://1.2.3.4:567',
    'no': 'localhost'
}
BAD_PROXY_SETTINGS = {
    'http': 'http://1.2.3.4:567',
    'https': 'https://1.2.3.4:567',
}


def test_use_proxy():
    with mock.patch('datadog_checks.checks.AgentCheck._get_requests_proxy', return_value=PROXY_SETTINGS):
        check = AgentCheck()
        assert check.get_instance_proxy({}, 'uri/health') == PROXY_SETTINGS


def test_skip_proxy():
    with mock.patch('datadog_checks.checks.AgentCheck._get_requests_proxy', return_value=PROXY_SETTINGS):
        check = AgentCheck()
        assert check.get_instance_proxy({'skip_proxy': True}, 'uri/health') == SKIP_PROXY_SETTINGS


def test_deprecated_no_proxy():
    with mock.patch('datadog_checks.checks.AgentCheck._get_requests_proxy', return_value=PROXY_SETTINGS):
        check = AgentCheck()
        assert check.get_instance_proxy({'no_proxy': True}, 'uri/health') == SKIP_PROXY_SETTINGS


def test_http_proxy():
    old_env = dict(os.environ)
    os.environ['HTTP_PROXY'] = BAD_PROXY_SETTINGS['http']

    try:
        check = AgentCheck()
        proxies = check.get_instance_proxy({'skip_proxy': True}, 'uri/health')
        response = requests.get('http://google.com', proxies=proxies)
        response.raise_for_status()
    finally:
        os.environ.clear()
        os.environ.update(old_env)


def test_http_proxy_fail():
    old_env = dict(os.environ)
    os.environ['HTTP_PROXY'] = BAD_PROXY_SETTINGS['http']

    try:
        with mock.patch('datadog_checks.checks.AgentCheck._get_requests_proxy', return_value={}):
            check = AgentCheck()
            proxies = check.get_instance_proxy({}, 'uri/health')
        with pytest.raises((ConnectTimeout, ProxyError)):
            requests.get('http://google.com', timeout=1, proxies=proxies)
    finally:
        os.environ.clear()
        os.environ.update(old_env)


def test_https_proxy():
    old_env = dict(os.environ)
    os.environ['HTTPS_PROXY'] = BAD_PROXY_SETTINGS['https']

    try:
        check = AgentCheck()
        proxies = check.get_instance_proxy({'skip_proxy': True}, 'uri/health')
        response = requests.get('https://google.com', proxies=proxies)
        response.raise_for_status()
    finally:
        os.environ.clear()
        os.environ.update(old_env)


def test_https_proxy_fail():
    old_env = dict(os.environ)
    os.environ['HTTPS_PROXY'] = BAD_PROXY_SETTINGS['https']

    try:
        with mock.patch('datadog_checks.checks.AgentCheck._get_requests_proxy', return_value={}):
            check = AgentCheck()
            proxies = check.get_instance_proxy({}, 'uri/health')
        with pytest.raises((ConnectTimeout, ProxyError)):
            requests.get('https://google.com', timeout=1, proxies=proxies)
    finally:
        os.environ.clear()
        os.environ.update(old_env)


def test_config_no_proxy():
    with mock.patch('datadog_checks.checks.AgentCheck._get_requests_proxy', return_value=NO_PROXY_DD_CONFIG_SETTINGS):
        check = AgentCheck()
        proxy_results = check.get_instance_proxy({}, 'uri/health')
        assert 'localhost' in proxy_results['no']
