# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.tls import TLSCheck


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


def test_tags_local_hostname_no_validation_legacy():
    instance = {
        'name': 'foo',
        'local_cert_path': 'cert.pem',
        'server_hostname': 'www.google.com',
        'validate_hostname': False,
    }
    c = TLSCheck('tls', {}, [instance])

    assert c._tags == ['name:foo']


# This is a special edge case where both supported `validate_hostname` configs are used with differing values.
# This case should realistically never happen, but theoretically can happen
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


def test_tags_remote():
    instance = {'name': 'foo', 'server': 'https://www.google.com'}
    c = TLSCheck('tls', {}, [instance])

    assert c._tags == ['name:foo', 'server_hostname:www.google.com', 'server:www.google.com', 'port:443']


def test_validation_data():
    c = TLSCheck('tls', {}, [{}])

    assert c._validation_data is None
    assert c.validation_data == c._validation_data
    assert isinstance(c.validation_data, tuple)
