# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy
from typing import Callable  # noqa: F401

import mock
import pytest

from datadog_checks.base.stubs.aggregator import AggregatorStub  # noqa: F401
from datadog_checks.base.stubs.datadog_agent import DatadogAgentStub  # noqa: F401
from datadog_checks.rethinkdb import RethinkDBCheck
from datadog_checks.rethinkdb.types import Instance  # noqa: F401

from .assertions import assert_metrics, assert_service_checks
from .cluster import temporarily_disconnect_server
from .common import (
    HEROES_TABLE_SERVERS,
    MALFORMED_VERSION_STRING_PARAMS,
    RAW_VERSION,
    SERVER_PORTS,
    TLS_CLIENT_CERT,
    TLS_SERVER,
)
from .types import ServerName  # noqa: F401


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
class TestCheck:
    METRICS_COLLECTION_MOCK_TARGET = 'datadog_checks.rethinkdb.check.RethinkDBCheck.collect_metrics'

    def test_default(self, dd_run_check, aggregator, instance):
        # type: (Callable, AggregatorStub, Instance) -> None
        check = RethinkDBCheck('rethinkdb', {}, [instance])
        dd_run_check(check)
        assert_metrics(aggregator)
        assert_service_checks(aggregator, instance)

    def test_connect_proxy_ok(self, dd_run_check, aggregator, instance):
        # type: (Callable, AggregatorStub, Instance) -> None
        instance = instance.copy()
        instance['port'] = SERVER_PORTS['proxy']

        check = RethinkDBCheck('rethinkdb', {}, [instance])
        dd_run_check(check)
        assert_metrics(aggregator, is_proxy=True)
        assert_service_checks(aggregator, instance)

    def test_connect_tls_ok(self, dd_run_check, aggregator, instance):
        # type: (Callable, AggregatorStub, Instance) -> None
        instance = instance.copy()
        instance['port'] = SERVER_PORTS[TLS_SERVER]
        instance['tls_ca_cert'] = TLS_CLIENT_CERT

        check = RethinkDBCheck('rethinkdb', {}, [instance])
        dd_run_check(check)
        assert_metrics(aggregator)
        assert_service_checks(aggregator, instance)

    def test_no_credentials_ok(self, dd_run_check, aggregator, instance):
        # type: (Callable, AggregatorStub, Instance) -> None
        instance = instance.copy()

        # RethinkDB will default to 'admin' w/o password.
        # Should work assuming admin account in our test cluster doesn't have a password.
        instance.pop('username')
        instance.pop('password')

        check = RethinkDBCheck('rethinkdb', {}, [instance])
        dd_run_check(check)
        assert_metrics(aggregator)
        assert_service_checks(aggregator, instance)

    @pytest.mark.parametrize('server_with_data', list(HEROES_TABLE_SERVERS))
    def test_disconnected_data_server_ok(self, dd_run_check, aggregator, instance, server_with_data):
        # type: (Callable, AggregatorStub, Instance, ServerName) -> None
        # Simulate the scenario where one of the servers in the cluster is down, but not the one we're
        # connecting to.
        check = RethinkDBCheck('rethinkdb', {}, [instance])
        with temporarily_disconnect_server(server_with_data):
            dd_run_check(check)
        assert_metrics(aggregator, disconnected_servers={server_with_data})
        assert_service_checks(aggregator, instance, disconnected_servers={server_with_data})

    def test_connection_failure(self, dd_run_check, aggregator, instance):
        # type: (Callable, AggregatorStub, Instance) -> None
        instance = copy.deepcopy(instance)
        instance['host'] = 'doesnotexist'

        check = RethinkDBCheck('rethinkdb', {}, [instance])
        with pytest.raises(Exception, match='Could not connect'):
            dd_run_check(check)
        assert_service_checks(aggregator, instance, connect_status=RethinkDBCheck.CRITICAL)

    def test_metric_collection_failure(self, dd_run_check, aggregator, instance):
        # type: (Callable, AggregatorStub, Instance) -> None
        with mock.patch(self.METRICS_COLLECTION_MOCK_TARGET, side_effect=Exception('Horrible failure')):
            check = RethinkDBCheck('rethinkdb', {}, [instance])
            with pytest.raises(Exception, match='Horrible failure'):
                dd_run_check(check)
            assert_service_checks(aggregator, instance, connect_status=RethinkDBCheck.CRITICAL)


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
class TestVersionMetadata:
    VERSION_MOCK_TARGET = 'datadog_checks.rethinkdb.queries_impl.get_version_metadata'

    @pytest.mark.skipif(not RAW_VERSION, reason='Requires RAW_VERSION to be set')
    def test_default(self, instance, dd_run_check, datadog_agent):
        # type: (Instance, Callable, DatadogAgentStub) -> None
        raw_version = RAW_VERSION
        version, _, build = raw_version.partition('~')
        major, minor, patch = version.split('.')
        metadata = {
            'version.scheme': 'semver',
            'version.major': major,
            'version.minor': minor,
            'version.patch': patch,
            'version.raw': raw_version,
        }

        check_id = 'test'
        check = RethinkDBCheck('rethinkdb', {}, [instance])
        check.check_id = check_id
        dd_run_check(check)
        datadog_agent.assert_metadata(check_id, metadata)

    @pytest.mark.integration
    @pytest.mark.parametrize('malformed_version_string', MALFORMED_VERSION_STRING_PARAMS)
    def test_malformed(self, instance, dd_run_check, datadog_agent, malformed_version_string):
        # type: (Instance, Callable, DatadogAgentStub, str) -> None
        with mock.patch(self.VERSION_MOCK_TARGET, return_value=[(malformed_version_string,)]):
            check_id = 'test'
            check = RethinkDBCheck('rethinkdb', {}, [instance])
            check.check_id = check_id
            dd_run_check(check)
            datadog_agent.assert_metadata(check_id, {})

    @pytest.mark.integration
    def test_failure(self, instance, dd_run_check, datadog_agent):
        # type: (Instance, Callable, DatadogAgentStub) -> None
        with mock.patch(self.VERSION_MOCK_TARGET, side_effect=ValueError('Oops!')):
            check_id = 'test'
            check = RethinkDBCheck('rethinkdb', {}, [instance])
            check.check_id = check_id
            dd_run_check(check)
            datadog_agent.assert_metadata(check_id, {})
