# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy
from typing import Any, Iterator, List

import pytest
import rethinkdb

from datadog_checks.base.stubs.aggregator import AggregatorStub
from datadog_checks.base.stubs.datadog_agent import DatadogAgentStub
from datadog_checks.rethinkdb import RethinkDBCheck
from datadog_checks.rethinkdb.types import Instance, Metric

from .assertions import assert_metrics
from .cluster import temporarily_disconnect_server
from .common import (
    DATABASE,
    HEROES_TABLE,
    HEROES_TABLE_SERVERS,
    MALFORMED_VERSION_STRING_PARAMS,
    RAW_VERSION,
    SERVER_PORTS,
    TABLE_STATUS_SERVICE_CHECKS,
    TAGS,
    TLS_CLIENT_CERT,
    TLS_SERVER,
)
from .types import ServerName


def _get_connect_service_check_tags(instance):
    # type: (Instance) -> List[str]
    return [
        'host:{}'.format(instance['host']),
        'port:{}'.format(instance['port']),
    ]


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_check(aggregator, instance):
    # type: (AggregatorStub, Instance) -> None
    check = RethinkDBCheck('rethinkdb', {}, [instance])
    check.check(instance)

    assert_metrics(aggregator)
    aggregator.assert_all_metrics_covered()

    service_check_tags = TAGS + _get_connect_service_check_tags(instance)
    aggregator.assert_service_check('rethinkdb.can_connect', RethinkDBCheck.OK, count=1, tags=service_check_tags)

    for service_check in TABLE_STATUS_SERVICE_CHECKS:
        tags = TAGS + ['table:{}'.format(HEROES_TABLE), 'database:{}'.format(DATABASE)]
        aggregator.assert_service_check(service_check, RethinkDBCheck.OK, count=1, tags=tags)


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_check_without_credentials_uses_admin(aggregator, instance):
    # type: (AggregatorStub, Instance) -> None
    """
    Verify that when no credentials are configured (not recommended though), the check still runs successfully provided
    the admin account doesn't have a password set.
    """
    instance = instance.copy()

    # Remove any credentials so that the Python driver uses the default credentials (i.e. admin account w/o password)
    # when connecting to RethinkDB.
    # See: https://rethinkdb.com/api/python/connect/#description
    instance.pop('username')
    instance.pop('password')

    check = RethinkDBCheck('rethinkdb', {}, [instance])
    check.check(instance)

    assert_metrics(aggregator)
    aggregator.assert_all_metrics_covered()

    service_check_tags = TAGS + _get_connect_service_check_tags(instance)
    aggregator.assert_service_check('rethinkdb.can_connect', RethinkDBCheck.OK, count=1, tags=service_check_tags)


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_check_connect_to_server_with_tls(aggregator, instance):
    # type: (AggregatorStub, Instance) -> None
    server = TLS_SERVER

    instance = instance.copy()
    instance['port'] = SERVER_PORTS[server]
    instance['tls_ca_cert'] = TLS_CLIENT_CERT

    check = RethinkDBCheck('rethinkdb', {}, [instance])
    check.check(instance)

    assert_metrics(aggregator)
    aggregator.assert_all_metrics_covered()

    service_check_tags = TAGS + _get_connect_service_check_tags(instance)
    aggregator.assert_service_check('rethinkdb.can_connect', RethinkDBCheck.OK, count=1, tags=service_check_tags)


@pytest.mark.integration
@pytest.mark.parametrize('server_with_data', list(HEROES_TABLE_SERVERS))
@pytest.mark.usefixtures('dd_environment')
def test_check_with_disconnected_server(aggregator, instance, server_with_data):
    # type: (AggregatorStub, Instance, ServerName) -> None
    """
    Verify that the check still runs to completion and sends appropriate service checks if one of the
    servers that holds data is disconnected.
    """
    check = RethinkDBCheck('rethinkdb', {}, [instance])

    with temporarily_disconnect_server(server_with_data):
        check.check(instance)

    disconnected_servers = {server_with_data}

    assert_metrics(aggregator, disconnected_servers=disconnected_servers)
    aggregator.assert_all_metrics_covered()

    service_check_tags = TAGS + _get_connect_service_check_tags(instance)
    aggregator.assert_service_check('rethinkdb.can_connect', RethinkDBCheck.OK, count=1, tags=service_check_tags)

    table_status_tags = TAGS + ['table:{}'.format(HEROES_TABLE), 'database:{}'.format(DATABASE)]

    for service_check in TABLE_STATUS_SERVICE_CHECKS:
        status = RethinkDBCheck.OK if service_check.endswith('ready_for_outdated_reads') else RethinkDBCheck.WARNING
        aggregator.assert_service_check(service_check, status, count=1, tags=table_status_tags)


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_cannot_connect_unknown_host(aggregator, instance):
    # type: (AggregatorStub, Instance) -> None
    instance = copy.deepcopy(instance)
    instance['host'] = 'doesnotexist'

    check = RethinkDBCheck('rethinkdb', {}, [instance])

    with pytest.raises(rethinkdb.errors.ReqlDriverError):
        check.check(instance)

    tags = TAGS + _get_connect_service_check_tags(instance)
    aggregator.assert_service_check('rethinkdb.can_connect', RethinkDBCheck.CRITICAL, count=1, tags=tags)


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_connected_but_check_failed_unexpectedly(aggregator, instance):
    # type: (AggregatorStub, Instance) -> None
    class Failure(Exception):
        pass

    class MockRethinkDBCheck(RethinkDBCheck):
        def collect_metrics(self, conn):
            # type: (Any) -> Iterator[Metric]
            yield {'type': 'gauge', 'name': 'rethinkdb.some.metric', 'value': 42, 'tags': []}
            raise Failure

    check = MockRethinkDBCheck('rethinkdb', {}, [instance])

    with pytest.raises(Failure):
        check.check(instance)

    service_check_tags = TAGS + _get_connect_service_check_tags(instance)
    aggregator.assert_service_check('rethinkdb.can_connect', RethinkDBCheck.CRITICAL, count=1, tags=service_check_tags)


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_metadata_version(instance, datadog_agent):
    # type: (Instance, DatadogAgentStub) -> None
    check_id = 'test'

    check = RethinkDBCheck('rethinkdb', {}, [instance])
    check.check_id = check_id

    check.check(instance)

    raw_version = RAW_VERSION
    version, _, build = raw_version.partition('~')
    major, minor, patch = version.split('.')
    version_metadata = {
        'version.scheme': 'semver',
        'version.major': major,
        'version.minor': minor,
        'version.patch': patch,
        'version.raw': raw_version,
    }

    datadog_agent.assert_metadata(check_id, version_metadata)


@pytest.mark.unit
@pytest.mark.parametrize('malformed_version_string', MALFORMED_VERSION_STRING_PARAMS)
def test_metadata_version_malformed(instance, aggregator, datadog_agent, malformed_version_string):
    # type: (Instance, AggregatorStub, DatadogAgentStub, str) -> None
    """
    Verify that check still runs to completion if version provided by RethinkDB is malformed.
    """

    class MockRethinkDBCheck(RethinkDBCheck):
        def collect_connected_server_version(self, conn):
            # type: (Any) -> str
            return malformed_version_string

    check_id = 'test'

    check = MockRethinkDBCheck('rethinkdb', {}, [instance])
    check.check_id = check_id

    check.check(instance)
    aggregator.assert_service_check('rethinkdb.can_connect', RethinkDBCheck.OK)

    datadog_agent.assert_metadata(check_id, {})


@pytest.mark.unit
def test_metadata_version_failure(instance, aggregator, datadog_agent):
    # type: (Instance, AggregatorStub, DatadogAgentStub) -> None
    """
    Verify that check still runs to completion if it fails to retrieve the RethinkDB version.
    """

    class MockRethinkDBCheck(RethinkDBCheck):
        def collect_connected_server_version(self, conn):
            # type: (Any) -> str
            raise ValueError('Oops!')

    check_id = 'test'

    check = MockRethinkDBCheck('rethinkdb', {}, [instance])
    check.check_id = check_id

    check.check(instance)
    aggregator.assert_service_check('rethinkdb.can_connect', RethinkDBCheck.OK)

    datadog_agent.assert_metadata(check_id, {})
