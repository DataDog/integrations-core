# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from unittest import mock

import dns.resolver
import pytest
from dns.exception import Timeout
from dns.resolver import NoAnswer

from datadog_checks.postgres import cloud
from datadog_checks.postgres.cloud import (
    CloudEndpoint,
    detect_cloud_endpoint,
    find_cloud_endpoint_in_chain,
    match_cloud_hostname,
    resolve_cname_chain,
)

pytestmark = pytest.mark.unit

RDS_ENDPOINT = 'mydb.cfxgae8cilcf.us-east-1.rds.amazonaws.com'


class _FakeRdata:
    def __init__(self, target):
        self.target = target


def _resolver_from_map(cname_map, error=None):
    """Build a side_effect for ``Resolver.resolve`` from a {name: cname_target} map.

    Names not present in the map raise ``NoAnswer`` (no further CNAME), unless
    ``error`` is provided, in which case it is raised for every lookup.
    """

    def _resolve(name, rdtype):
        if error is not None:
            raise error
        key = str(name).rstrip('.').lower()
        if key in cname_map:
            return [_FakeRdata(cname_map[key])]
        raise NoAnswer()

    return _resolve


def _patch_resolver(cname_map, error=None):
    return mock.patch.object(dns.resolver.Resolver, 'resolve', side_effect=_resolver_from_map(cname_map, error))


class TestResolveCnameChain:
    @pytest.mark.parametrize(
        'host, cname_map, expected',
        [
            ('', {}, []),
            (None, {}, []),
            ('db.example.com', {}, ['db.example.com']),
            ('  DB.Example.com.  ', {}, ['db.example.com']),
            ('db.example.com', {'db.example.com': RDS_ENDPOINT}, ['db.example.com', RDS_ENDPOINT]),
            (
                'db.example.com',
                {'db.example.com': 'proxy.internal.example.com', 'proxy.internal.example.com': RDS_ENDPOINT},
                ['db.example.com', 'proxy.internal.example.com', RDS_ENDPOINT],
            ),
            (
                'a.example.com',
                {'a.example.com': 'b.example.com', 'b.example.com': 'a.example.com'},
                ['a.example.com', 'b.example.com'],
            ),
        ],
        ids=['empty', 'none', 'no_cname', 'normalizes', 'single_hop', 'multi_hop', 'loop_protection'],
    )
    def test_resolve_cname_chain(self, host, cname_map, expected):
        with _patch_resolver(cname_map):
            assert resolve_cname_chain(host) == expected

    def test_max_hops(self):
        cname_map = {'h{}.example.com'.format(i): 'h{}.example.com'.format(i + 1) for i in range(20)}
        with _patch_resolver(cname_map):
            chain = resolve_cname_chain('h0.example.com', max_hops=3)
        # original host + at most max_hops targets
        assert len(chain) == 4

    @pytest.mark.parametrize('error', [Timeout(), RuntimeError('boom')], ids=['dns_error', 'unexpected_error'])
    def test_returns_partial_chain_on_error(self, error):
        with _patch_resolver({}, error=error):
            assert resolve_cname_chain('db.example.com') == ['db.example.com']

    def test_missing_dnspython_returns_host(self):
        with mock.patch.dict('sys.modules', {'dns.resolver': None}):
            assert resolve_cname_chain('db.example.com') == ['db.example.com']

    @pytest.mark.parametrize(
        'stop, expected, expected_calls',
        [
            (lambda h: h == 'b.example.com', ['a.example.com', 'b.example.com'], 1),
            (lambda h: True, ['a.example.com'], 0),
        ],
        ids=['stops_mid_chain', 'stops_on_initial_host'],
    )
    def test_stop_predicate(self, stop, expected, expected_calls):
        cname_map = {
            'a.example.com': 'b.example.com',
            'b.example.com': 'c.example.com',
            'c.example.com': 'd.example.com',
        }
        with _patch_resolver(cname_map) as resolve:
            chain = resolve_cname_chain('a.example.com', stop=stop)
        assert chain == expected
        assert resolve.call_count == expected_calls

    @pytest.mark.parametrize(
        'host',
        ['localhost', '127.0.0.1', '::1', '10.0.0.5', '/var/run/postgres.sock', 'mydb.local'],
    )
    def test_skips_dns_for_local_and_ip_hosts(self, host):
        # resolve must not be called for hosts that can't be a CNAME'd cloud endpoint
        with _patch_resolver({}) as resolve:
            chain = resolve_cname_chain(host)
        resolve.assert_not_called()
        assert chain == [host.strip().rstrip('.').lower()]


class TestFindCloudEndpointInChain:
    @pytest.mark.parametrize(
        'chain, expected_endpoint',
        [
            ([RDS_ENDPOINT], RDS_ENDPOINT),
            (['db.example.com', RDS_ENDPOINT], RDS_ENDPOINT),
            (['db.example.com', 'other.internal'], None),
            ([], None),
        ],
        ids=['direct_rds', 'match_in_chain', 'no_match', 'empty'],
    )
    def test_find_cloud_endpoint_in_chain(self, chain, expected_endpoint):
        result = find_cloud_endpoint_in_chain(chain)
        if expected_endpoint is None:
            assert result is None
        else:
            assert result == CloudEndpoint(
                provider='aws', product='rds', resource_type='aws_rds_instance', endpoint=expected_endpoint
            )

    @pytest.mark.parametrize(
        'hostname, expected_resource_type',
        [(RDS_ENDPOINT, 'aws_rds_instance'), ('db.example.com', None), ('', None)],
        ids=['rds', 'non_cloud', 'empty'],
    )
    def test_match_cloud_hostname(self, hostname, expected_resource_type):
        result = match_cloud_hostname(hostname)
        if expected_resource_type is None:
            assert result is None
        else:
            assert result.resource_type == expected_resource_type

    def test_registry_is_extensible(self, monkeypatch):
        monkeypatch.setitem(
            cloud.CLOUD_HOSTNAME_PATTERNS,
            'fakecloud',
            [('fakeproduct', '.fake.example.com', 'fake_resource')],
        )
        result = find_cloud_endpoint_in_chain(['svc.fake.example.com'])
        assert result == CloudEndpoint(
            provider='fakecloud', product='fakeproduct', resource_type='fake_resource', endpoint='svc.fake.example.com'
        )


class TestDetectCloudEndpoint:
    @pytest.mark.parametrize(
        'host, cname_map, expected_endpoint',
        [
            ('db.example.com', {'db.example.com': RDS_ENDPOINT}, RDS_ENDPOINT),
            ('db.example.com', {}, None),
        ],
        ids=['cname_to_rds', 'non_cloud'],
    )
    def test_detect_cloud_endpoint(self, host, cname_map, expected_endpoint):
        with _patch_resolver(cname_map):
            result = detect_cloud_endpoint(host)
        if expected_endpoint is None:
            assert result is None
        else:
            assert result is not None
            assert result.resource_type == 'aws_rds_instance'
            assert result.endpoint == expected_endpoint

    def test_short_circuits_at_first_cloud_hop(self):
        # the chain continues past the RDS endpoint to an internal compute host,
        # but resolution should stop as soon as the RDS endpoint is found
        cname_map = {
            'db.example.com': RDS_ENDPOINT,
            RDS_ENDPOINT: 'ec2-1-2-3-4.compute-1.amazonaws.com',
        }
        with _patch_resolver(cname_map) as resolve:
            result = detect_cloud_endpoint('db.example.com')
        assert result is not None
        assert result.endpoint == RDS_ENDPOINT
        # only the first hop (db.example.com -> RDS) is resolved; the chain past it is not
        assert resolve.call_count == 1

    def test_direct_rds_host_skips_resolution(self):
        # a host that is already an RDS endpoint should not trigger any CNAME lookup
        with _patch_resolver({}) as resolve:
            result = detect_cloud_endpoint(RDS_ENDPOINT)
        assert result is not None
        assert result.endpoint == RDS_ENDPOINT
        resolve.assert_not_called()
