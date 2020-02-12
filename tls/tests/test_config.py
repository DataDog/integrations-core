# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import ssl

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
        'validate_hostname': False,
    }
    c = TLSCheck('tls', {}, [instance])

    assert c._tags == ['name:foo']


def test_tags_remote():
    instance = {'name': 'foo', 'server': 'https://www.google.com'}
    c = TLSCheck('tls', {}, [instance])

    assert c._tags == ['name:foo', 'server_hostname:www.google.com', 'server:www.google.com', 'port:443']


def test_cert():
    instance = {'cert': 'cert'}
    c = TLSCheck('tls', {}, [instance])

    assert c._cert == os.path.expanduser(instance['cert'])


def test_private_key():
    instance = {'private_key': 'private_key'}
    c = TLSCheck('tls', {}, [instance])

    assert c._private_key == os.path.expanduser(instance['private_key'])


def test_ca_cert_file():
    instance = {'ca_cert': 'ca_cert'}
    c = TLSCheck('tls', {}, [instance])

    assert c._cafile == os.path.expanduser(instance['ca_cert'])
    assert c._capath is None


def test_ca_cert_dir():
    instance = {'ca_cert': '~'}
    c = TLSCheck('tls', {}, [instance])

    assert c._cafile is None
    assert c._capath == os.path.expanduser(instance['ca_cert'])


def test_validation_data():
    c = TLSCheck('tls', {}, [{}])

    assert c._validation_data is None
    assert c.validation_data == c._validation_data
    assert isinstance(c.validation_data, tuple)


def test_tls_context():
    c = TLSCheck('tls', {}, [{}])

    assert c._tls_context is None
    assert c.tls_context == c._tls_context
    assert isinstance(c.tls_context, ssl.SSLContext)
