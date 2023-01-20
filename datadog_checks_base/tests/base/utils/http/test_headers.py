# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from collections import OrderedDict

import mock
import pytest
from six import iteritems

from datadog_checks.base.utils.headers import headers as agent_headers
from datadog_checks.base.utils.http import RequestsWrapper

from .common import DEFAULT_OPTIONS

pytestmark = [pytest.mark.unit]


def test_agent_headers():
    # This helper is not used by the RequestsWrapper, but some integrations may use it.
    # So we provide a unit test for it.
    agent_config = {}
    headers = agent_headers(agent_config)
    assert headers == DEFAULT_OPTIONS['headers']


def test_config_default():
    instance = {}
    init_config = {}
    http = RequestsWrapper(instance, init_config)

    assert http.options['headers'] == DEFAULT_OPTIONS['headers']


def test_config_headers():
    headers = OrderedDict((('key1', 'value1'), ('key2', 'value2')))
    instance = {'headers': headers}
    init_config = {}
    http = RequestsWrapper(instance, init_config)

    assert list(iteritems(http.options['headers'])) == list(iteritems(headers))


def test_config_headers_string_values():
    instance = {'headers': {'answer': 42}}
    init_config = {}
    http = RequestsWrapper(instance, init_config)

    assert http.options['headers'] == {'answer': '42'}


def test_config_extra_headers():
    headers = OrderedDict((('key1', 'value1'), ('key2', 'value2')))
    instance = {'extra_headers': headers}
    init_config = {}
    http = RequestsWrapper(instance, init_config)

    complete_headers = OrderedDict(DEFAULT_OPTIONS['headers'])
    complete_headers.update(headers)
    assert list(iteritems(http.options['headers'])) == list(iteritems(complete_headers))


def test_config_extra_headers_string_values():
    instance = {'extra_headers': {'answer': 42}}
    init_config = {}
    http = RequestsWrapper(instance, init_config)

    complete_headers = dict(DEFAULT_OPTIONS['headers'])
    complete_headers.update({'answer': '42'})
    assert http.options['headers'] == complete_headers


def test_extra_headers_on_http_method_call():
    instance = {'extra_headers': {'answer': 42}}
    init_config = {}
    http = RequestsWrapper(instance, init_config)

    complete_headers = dict(DEFAULT_OPTIONS['headers'])
    complete_headers.update({'answer': '42'})

    extra_headers = {"foo": "bar"}
    with mock.patch("requests.get") as get:
        http.get("http://example.com/hello", extra_headers=extra_headers)

        expected_options = dict(complete_headers)
        expected_options.update(extra_headers)

        get.assert_called_with(
            "http://example.com/hello",
            headers=expected_options,
            auth=None,
            cert=None,
            proxies=None,
            timeout=(10.0, 10.0),
            verify=True,
            allow_redirects=True,
        )

    # make sure the original headers are not modified
    assert http.options['headers'] == complete_headers
    assert extra_headers == {"foo": "bar"}
