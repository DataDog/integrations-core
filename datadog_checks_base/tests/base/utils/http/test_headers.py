# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from collections import OrderedDict

import mock
import pytest

from datadog_checks.base.utils.headers import headers as agent_headers
from datadog_checks.base.utils.http import RequestsWrapper

from .common import DEFAULT_OPTIONS, get_wire_headers

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

    assert list(http.options['headers'].items()) == list(headers.items())


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
    assert list(http.options['headers'].items()) == list(complete_headers.items())


def test_config_extra_headers_string_values():
    instance = {'extra_headers': {'answer': 42}}
    init_config = {}
    http = RequestsWrapper(instance, init_config)

    complete_headers = dict(DEFAULT_OPTIONS['headers'])
    complete_headers.update({'answer': '42'})
    assert http.options['headers'] == complete_headers


def test_config_extra_headers_non_canonical_case_takes_precedence_over_the_seeded_default():
    instance = {'extra_headers': {'accept': 'application/openmetrics-text'}}
    init_config = {}
    http = RequestsWrapper(instance, init_config)

    assert http.get_header('Accept') == 'application/openmetrics-text'


def test_config_extra_headers_override_config_headers_across_case():
    instance = {'headers': {'x-token': 'from-headers'}, 'extra_headers': {'X-Token': 'from-extra-headers'}}
    init_config = {}
    http = RequestsWrapper(instance, init_config)

    assert http.get_header('X-Token') == 'from-extra-headers'


def test_get_header_reports_the_value_that_reaches_the_wire():
    http = RequestsWrapper({'extra_headers': {'accept': 'application/openmetrics-text'}}, {})

    with mock.patch('requests.Session.get') as get:
        http.get('http://example.com/hello')

    assert get.call_args.kwargs['headers']['accept'] == http.get_header('Accept')


def test_config_headers_keep_every_configured_spelling():
    # HostHeaderSSLAdapter detects the exact configured spelling.
    instance = {'headers': {'host': 'first'}, 'extra_headers': {'Host': 'second'}, 'tls_use_host_header': True}
    init_config = {}
    http = RequestsWrapper(instance, init_config)

    assert http.options['headers'] == {'host': 'first', 'Host': 'second'}
    assert http.tls_use_host_header is True


def test_tls_use_host_header_sees_a_canonically_spelled_host_header():
    instance = {'headers': {'Host': 'example.com'}, 'tls_use_host_header': True}
    init_config = {}
    http = RequestsWrapper(instance, init_config)

    assert http.tls_use_host_header is True


def test_extra_headers_on_http_method_call():
    instance = {'extra_headers': {'answer': 42}}
    init_config = {}
    http = RequestsWrapper(instance, init_config)

    complete_headers = dict(DEFAULT_OPTIONS['headers'])
    complete_headers.update({'answer': '42'})

    extra_headers = {"foo": "bar"}
    with mock.patch("requests.Session.get") as get:
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


def test_request_headers_override_defaults_before_extra_headers():
    http = RequestsWrapper({'headers': {'X-Default': 'default', 'X-Precedence': 'default'}}, {})

    wire_headers = get_wire_headers(
        http,
        headers={'X-Request': 'request', 'X-Precedence': 'request'},
        extra_headers={'X-Extra': 'extra', 'X-Precedence': 'extra'},
    )

    assert wire_headers['X-Request'] == 'request'
    assert wire_headers['X-Extra'] == 'extra'
    assert wire_headers['X-Precedence'] == 'extra'
    assert wire_headers['X-Default'] == 'default'


def test_a_per_request_mapping_keeps_the_configured_headers():
    http = RequestsWrapper({'extra_headers': {'X-Configured': 'configured'}}, {})

    wire_headers = get_wire_headers(http, headers={'Cookie': 'APIC-cookie=token'})

    assert wire_headers['Cookie'] == 'APIC-cookie=token'
    assert wire_headers['User-Agent'] == 'Datadog Agent/0.0.0'
    assert wire_headers['X-Configured'] == 'configured'


def test_get_header_default_for_missing():
    http = RequestsWrapper({}, {})
    assert http.get_header('X-Missing') is None
    assert http.get_header('X-Missing', 'fallback') == 'fallback'


def test_get_header_case_insensitive():
    http = RequestsWrapper({}, {})
    assert http.get_header('accept') == '*/*'
    assert http.get_header('Accept') == '*/*'
    assert http.get_header('ACCEPT') == '*/*'


def test_set_header():
    http = RequestsWrapper({}, {})
    http.set_header('X-Token', 'abc123')
    assert http.get_header('X-Token') == 'abc123'
    http.set_header('Accept', 'application/json')
    assert http.get_header('Accept') == 'application/json'


def test_set_header_case_insensitive():
    http = RequestsWrapper({}, {})
    http.set_header('accept', 'application/json')
    assert http.get_header('Accept') == 'application/json'
    assert sum(1 for k in http.options['headers'] if k.lower() == 'accept') == 1


def test_set_header_collapses_case_insensitive_duplicates():
    http = RequestsWrapper({}, {})
    http.options['headers'] = OrderedDict(
        (('x-vault-token', 'configured-lower'), ('X-Vault-Token', 'configured-canonical'))
    )

    http.set_header('X-Vault-Token', 'runtime-token')

    assert http.get_header('X-Vault-Token') == 'runtime-token'
    assert sum(1 for key in http.options['headers'] if key.lower() == 'x-vault-token') == 1
