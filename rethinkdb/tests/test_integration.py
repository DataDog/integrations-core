# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy
from typing import ContextManager, Set

import mock
import pytest
import rethinkdb

from datadog_checks.base.stubs.aggregator import AggregatorStub
from datadog_checks.base.stubs.datadog_agent import DatadogAgentStub
from datadog_checks.base.types import ServiceCheckStatus
from datadog_checks.rethinkdb import RethinkDBCheck
from datadog_checks.rethinkdb.types import Instance

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
from .types import ServerName

try:
    from contextlib import nullcontext  # type: ignore
except ImportError:
    from contextlib2 import nullcontext


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
class TestCheck:
    METRICS_COLLECTION_MOCK_TARGET = 'datadog_checks.rethinkdb.check.RethinkDBCheck.collect_metrics'

    def run_test(
        self, aggregator, instance, check_context=None, connect_status=RethinkDBCheck.OK, disconnected_servers=None
    ):
        # type: (AggregatorStub, Instance, ContextManager[None], ServiceCheckStatus, Set[ServerName]) -> None
        check = RethinkDBCheck('rethinkdb', {}, [instance])

        with check_context if check_context is not None else nullcontext():
            check.check(instance)

        if connect_status == RethinkDBCheck.OK:
            assert_metrics(
                aggregator,
                is_proxy=instance['port'] == SERVER_PORTS['proxy'],
                disconnected_servers=disconnected_servers,
            )
            aggregator.assert_all_metrics_covered()

        assert_service_checks(
            aggregator, instance, connect_status=connect_status, disconnected_servers=disconnected_servers
        )

    def test_default(self, aggregator, instance):
        # type: (AggregatorStub, Instance) -> None
        self.run_test(aggregator, instance)

    def test_connect_proxy_ok(self, aggregator, instance):
        # type: (AggregatorStub, Instance) -> None
        instance = instance.copy()
        instance['port'] = SERVER_PORTS['proxy']
        self.run_test(aggregator, instance)

    def test_connect_tls_ok(self, aggregator, instance):
        # type: (AggregatorStub, Instance) -> None
        instance = instance.copy()
        instance['port'] = SERVER_PORTS[TLS_SERVER]
        instance['tls_ca_cert'] = TLS_CLIENT_CERT
        self.run_test(aggregator, instance)

    def test_no_credentials_ok(self, aggregator, instance):
        # type: (AggregatorStub, Instance) -> None
        instance = instance.copy()

        # RethinkDB will default to 'admin' w/o password.
        # Should work assuming admin account in our test cluster doesn't have a password.
        instance.pop('username')
        instance.pop('password')

        self.run_test(aggregator, instance)

    @pytest.mark.parametrize('server_with_data', list(HEROES_TABLE_SERVERS))
    def test_disconnected_data_server_ok(self, aggregator, instance, server_with_data):
        # type: (AggregatorStub, Instance, ServerName) -> None
        # Simulate the scenario where one of the servers in the cluster is down, but not the one we're
        # connecting to.
        self.run_test(
            aggregator,
            instance,
            check_context=temporarily_disconnect_server(server_with_data),
            disconnected_servers={server_with_data},
        )

    def test_connection_failure(self, aggregator, instance):
        # type: (AggregatorStub, Instance) -> None
        instance = copy.deepcopy(instance)
        instance['host'] = 'doesnotexist'
        self.run_test(
            aggregator,
            instance,
            check_context=pytest.raises(rethinkdb.errors.ReqlDriverError),
            connect_status=RethinkDBCheck.CRITICAL,
        )

    def test_metric_collection_failure(self, aggregator, instance):
        # type: (AggregatorStub, Instance) -> None
        class Failure(Exception):
            pass

        with mock.patch(self.METRICS_COLLECTION_MOCK_TARGET, side_effect=Failure):
            self.run_test(
                aggregator, instance, check_context=pytest.raises(Failure), connect_status=RethinkDBCheck.CRITICAL
            )


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
class TestVersionMetadata:
    VERSION_MOCK_TARGET = 'datadog_checks.rethinkdb.operations.get_connected_server_raw_version'

    def run_test(self, instance, datadog_agent, metadata):
        # type: (Instance, DatadogAgentStub, dict) -> None
        check_id = 'test'
        check = RethinkDBCheck('rethinkdb', {}, [instance])
        check.check_id = check_id
        check.check(instance)
        datadog_agent.assert_metadata(check_id, metadata)

    @pytest.mark.skipif(not RAW_VERSION, reason='Requires RAW_VERSION to be set')
    def test_default(self, instance, datadog_agent):
        # type: (Instance, DatadogAgentStub) -> None
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

        self.run_test(instance, datadog_agent, metadata=metadata)

    @pytest.mark.integration
    @pytest.mark.parametrize('malformed_version_string', MALFORMED_VERSION_STRING_PARAMS)
    def test_malformed(self, instance, aggregator, datadog_agent, malformed_version_string):
        # type: (Instance, AggregatorStub, DatadogAgentStub, str) -> None
        with mock.patch(self.VERSION_MOCK_TARGET, return_value=malformed_version_string):
            self.run_test(instance, datadog_agent, metadata={})

    @pytest.mark.integration
    def test_failure(self, instance, aggregator, datadog_agent):
        # type: (Instance, AggregatorStub, DatadogAgentStub) -> None
        with mock.patch(self.VERSION_MOCK_TARGET, side_effect=ValueError('Oops!')):
            self.run_test(instance, datadog_agent, metadata={})
