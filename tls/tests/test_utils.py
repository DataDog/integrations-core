# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.tls.utils import DEFAULT_PROTOCOL_VERSIONS, get_protocol_versions, is_ip_address


class TestIPAddress:
    def test_true(self):
        assert is_ip_address('1.2.3.4')

    def test_false(self):
        assert not is_ip_address('host')


class TestProtocolVersions:
    def test_default(self):
        assert get_protocol_versions([]) == DEFAULT_PROTOCOL_VERSIONS

    def test_casing(self):
        assert get_protocol_versions(['tlsv1.0', 'TLSv1.3']) == {'TLSv1', 'TLSv1.3'}

    def test_numbers(self):
        assert get_protocol_versions(['v1.0', '1.3']) == {'TLSv1', 'TLSv1.3'}

    def test_unknown_ok(self):
        assert get_protocol_versions(['tlsv9000']) == {'tlsv9000'}
