# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base.utils.http_httpx import HTTPXWrapper


def test_tls_verify_default_true(capturing_transport):
    http = HTTPXWrapper({}, {}, transport=capturing_transport)
    assert http.options['verify'] is True


def test_tls_verify_false(capturing_transport):
    http = HTTPXWrapper({'tls_verify': False}, {}, transport=capturing_transport)
    assert http.options['verify'] is False


def test_tls_ca_cert_uses_path(capturing_transport):
    http = HTTPXWrapper({'tls_ca_cert': '/etc/ssl/ca.pem'}, {}, transport=capturing_transport)
    assert http.options['verify'] == '/etc/ssl/ca.pem'


def test_tls_client_cert_string(capturing_transport):
    http = HTTPXWrapper({'tls_cert': '/etc/ssl/client.pem'}, {}, transport=capturing_transport)
    assert http.options['cert'] == '/etc/ssl/client.pem'


def test_tls_client_cert_with_key(capturing_transport):
    http = HTTPXWrapper(
        {'tls_cert': '/etc/ssl/client.pem', 'tls_private_key': '/etc/ssl/client.key'},
        {},
        transport=capturing_transport,
    )
    assert http.options['cert'] == ('/etc/ssl/client.pem', '/etc/ssl/client.key')


def test_tls_no_cert_when_not_configured(capturing_transport):
    http = HTTPXWrapper({}, {}, transport=capturing_transport)
    assert http.options['cert'] is None
