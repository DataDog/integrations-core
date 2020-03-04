# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy
from typing import Any, Iterator, List

import pytest

from datadog_checks.base.stubs.aggregator import AggregatorStub
from datadog_checks.base.stubs.datadog_agent import DatadogAgentStub
from datadog_checks.rethinkdb import RethinkDBCheck
from datadog_checks.rethinkdb.config import Config
from datadog_checks.rethinkdb.connections import Connection
from datadog_checks.rethinkdb.exceptions import CouldNotConnect
from datadog_checks.rethinkdb.types import Instance, Metric

from ._types import ServerName
from .assertions import assert_metrics
from .cluster import temporarily_disconnect_server
from .common import (
    DATABASE,
    HEROES_TABLE,
    HEROES_TABLE_SERVERS,
    HOST,
    RETHINKDB_VERSION,
    SERVER_PORTS,
    TABLE_STATUS_SERVICE_CHECKS,
    TLS_CLIENT_CERT,
    TLS_SERVER,
)
from .unit.common import MALFORMED_VERSION_STRING_PARAMS
from .unit.utils import MockConnection


def _get_connect_service_check_tags(server='server0'):
    # type: (ServerName) -> List[str]
    return [
        'host:{}'.format(HOST),
        'port:{}'.format(SERVER_PORTS[server]),
        'server:{}'.format(server),
        'proxy:false',
    ]


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_check(aggregator, instance):
    # type: (AggregatorStub, Instance) -> None
    check = RethinkDBCheck('rethinkdb', {}, [instance])
    check.check(instance)

    assert_metrics(aggregator)
    aggregator.assert_all_metrics_covered()

    service_check_tags = _get_connect_service_check_tags()
    aggregator.assert_service_check('rethinkdb.can_connect', RethinkDBCheck.OK, count=1, tags=service_check_tags)

    for service_check in TABLE_STATUS_SERVICE_CHECKS:
        tags = ['table:{}'.format(HEROES_TABLE), 'database:{}'.format(DATABASE)]
        aggregator.assert_service_check(service_check, RethinkDBCheck.OK, count=1, tags=tags)


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_check_as_admin(aggregator, instance):
    # type: (AggregatorStub, Instance) -> None
    instance = instance.copy()
    instance.pop('user')
    instance.pop('password')

    check = RethinkDBCheck('rethinkdb', {}, [instance])
    check.check(instance)

    assert_metrics(aggregator)
    aggregator.assert_all_metrics_covered()

    service_check_tags = _get_connect_service_check_tags()
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

    service_check_tags = _get_connect_service_check_tags(server=server)
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

    service_check_tags = _get_connect_service_check_tags()
    aggregator.assert_service_check('rethinkdb.can_connect', RethinkDBCheck.OK, count=1, tags=service_check_tags)

    table_status_tags = ['table:{}'.format(HEROES_TABLE), 'database:{}'.format(DATABASE)]

    aggregator.assert_service_check(
        'rethinkdb.table_status.ready_for_outdated_reads', RethinkDBCheck.OK, count=1, tags=table_status_tags
    )
    aggregator.assert_service_check(
        'rethinkdb.table_status.ready_for_reads', RethinkDBCheck.WARNING, count=1, tags=table_status_tags
    )
    aggregator.assert_service_check(
        'rethinkdb.table_status.ready_for_writes', RethinkDBCheck.WARNING, count=1, tags=table_status_tags
    )
    aggregator.assert_service_check(
        'rethinkdb.table_status.all_replicas_ready', RethinkDBCheck.WARNING, count=1, tags=table_status_tags
    )


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_cannot_connect_unknown_host(aggregator, instance):
    # type: (AggregatorStub, Instance) -> None
    instance = copy.deepcopy(instance)
    instance['host'] = 'doesnotexist'

    check = RethinkDBCheck('rethinkdb', {}, [instance])

    with pytest.raises(CouldNotConnect):
        check.check(instance)

    aggregator.assert_service_check('rethinkdb.can_connect', RethinkDBCheck.CRITICAL, count=1, tags=[])


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_connected_but_check_failed_unexpectedly(aggregator, instance):
    # type: (AggregatorStub, Instance) -> None
    class Failure(Exception):
        pass

    def collect_and_fail():
        # type: () -> Iterator[Metric]
        yield {'type': 'gauge', 'name': 'rethinkdb.some.metric', 'value': 42, 'tags': []}
        raise Failure

    check = RethinkDBCheck('rethinkdb', {}, [instance])
    check.config._collect_funcs = [lambda engine, conn: collect_and_fail()]

    with pytest.raises(Failure):
        check.check(instance)

    service_check_tags = _get_connect_service_check_tags()
    aggregator.assert_service_check('rethinkdb.can_connect', RethinkDBCheck.CRITICAL, count=1, tags=service_check_tags)


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_version_metadata(instance, datadog_agent):
    # type: (Instance, DatadogAgentStub) -> None
    check_id = 'test'

    check = RethinkDBCheck('rethinkdb', {}, [instance])
    check.check_id = check_id

    check.check(instance)

    raw_version = RETHINKDB_VERSION
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
def test_version_metadata_failure(monkeypatch, instance, datadog_agent, malformed_version_string):
    # type: (Any, Instance, DatadogAgentStub, str) -> None
    """
    Verify that check still runs to completion if version provided by RethinkDB is malformed.
    """

    class FakeConfig(Config):
        def __init__(self, *args, **kwargs):
            # type: (*Any, **Any) -> None
            super(FakeConfig, self).__init__(*args, **kwargs)
            self._collect_funcs = []  # Skip metrics as we only provide a row for server version.

        def connect(self):
            # type: () -> Connection
            server_status = {'process': {'version': malformed_version_string}}
            return MockConnection(rows=lambda: server_status)

    check_id = 'test'

    check = RethinkDBCheck('rethinkdb', {}, [instance])
    check.check_id = check_id
    check.config = FakeConfig(instance)

    check.check(instance)

    datadog_agent.assert_metadata(check_id, {})
