# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os
from collections import OrderedDict

DEFAULT_OPTIONS = {
    'auth': None,
    'cert': None,
    'headers': OrderedDict(
        [
            ('User-Agent', 'Datadog Agent/0.0.0'),
            ('Accept', '*/*'),
            ('Accept-Encoding', 'gzip, deflate'),
        ]
    ),
    'proxies': None,
    'timeout': (10.0, 10.0),
    'verify': True,
    'allow_redirects': True,
}

FIXTURE_PATH = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'fixtures')


def verify_from_tls(tls):
    if tls.tls_ca_cert:
        return tls.tls_ca_cert
    return tls.tls_verify


def cert_from_tls(tls):
    if not tls.tls_cert:
        return None
    if tls.tls_private_key:
        return (tls.tls_cert, tls.tls_private_key)
    return tls.tls_cert


def proxies_from_http(http):
    http_proxy = http.proxy_for_url('http://example.com')
    https_proxy = http.proxy_for_url('https://example.com')
    if http_proxy is None and https_proxy is None:
        return None
    return {'http': http_proxy or '', 'https': https_proxy or ''}


def expected_request_options(http, auth=None, **overrides):
    """Build expected requests.Session kwargs from HTTP client capabilities."""
    timeout = http.default_timeout
    tls = http.tls_config
    options = {
        'auth': auth if auth is not None else http.get_basic_auth(),
        'cert': cert_from_tls(tls),
        'headers': http.get_headers(),
        'proxies': proxies_from_http(http),
        'timeout': (timeout.connect, timeout.read),
        'verify': verify_from_tls(tls),
        'allow_redirects': True,
    }
    options.update(overrides)
    return options
