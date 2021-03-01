# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.tls import TLSCheck

from .conftest import CA_CERT, PRIVATE_KEY


def test_tags_local():
    instance = {'name': 'foo', 'local_cert_path': 'cert.pem'}
    c = TLSCheck('tls', {}, [instance])

    assert c._tags == ['name:foo']


def test_tags_local_hostname():
    instance = {'name': 'foo', 'local_cert_path': 'cert.pem', 'server_hostname': 'www.google.com'}
    c = TLSCheck('tls', {}, [instance])

    assert c._tags == ['name:foo', 'server_hostname:www.google.com']


def test_tags_local_hostname_no_validation():
    instance = {
        'name': 'foo',
        'local_cert_path': 'cert.pem',
        'server_hostname': 'www.google.com',
        'tls_validate_hostname': False,
    }
    c = TLSCheck('tls', {}, [instance])

    assert c._tags == ['name:foo']


# This is a special edge case where both supported `validate_hostname` configs are used with differing values.
# This case should realistically never happen, but theoretically can happen
# If either `tls_validate_hostname` or `validate_hostname` is false, then `tls_validate_hostname` is False
def test_tags_local_hostname_no_validation_legacy_edge_case():
    instance = {
        'name': 'foo',
        'local_cert_path': 'cert.pem',
        'server_hostname': 'www.google.com',
        'validate_hostname': False,
        'tls_validate_hostname': True,
    }
    c = TLSCheck('tls', {}, [instance])

    assert c._tags == ['name:foo']
    assert c._tls_validate_hostname is False


def test_tags_remote():
    instance = {'name': 'foo', 'server': 'https://www.google.com'}
    c = TLSCheck('tls', {}, [instance])

    assert c._tags == ['name:foo', 'server_hostname:www.google.com', 'server:www.google.com', 'port:443']


def test_validation_data():
    c = TLSCheck('tls', {}, [{}])

    assert c._validation_data is None
    assert c.validation_data == c._validation_data
    assert isinstance(c.validation_data, tuple)


@pytest.mark.parametrize(
    'extra_config, expected_http_kwargs',
    [
        pytest.param({'ca_cert': CA_CERT}, {'tls_ca_cert': CA_CERT}, id='legacy ca_cert param'),
        pytest.param({'private_key': PRIVATE_KEY}, {'tls_private_key': PRIVATE_KEY}, id='legacy private_key param'),
        pytest.param(
            {'validate_hostname': False}, {'tls_validate_hostname': False}, id='legacy validate_hostname param'
        ),
        pytest.param({'validate_cert': False}, {'tls_verify': False}, id='legacy validate_cert param'),
    ],
)
def test_config(extra_config, expected_http_kwargs):
    instance = {
        'name': 'foo',
    }
    instance.update(extra_config)
    c = TLSCheck('tls', {}, [instance])
    c.get_tls_context()  # need to call this for config values to be saved by _tls_context_wrapper
    actual_options = {k: v for k, v in c._tls_context_wrapper.config.items() if k in expected_http_kwargs}
    assert expected_http_kwargs == actual_options
