# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging
import os

import mock
import pytest

from datadog_checks.base import AgentCheck, ConfigurationError
from datadog_checks.base.log import TRACE_LEVEL
from datadog_checks.vertica import VerticaCheck
from datadog_checks.vertica.queries import QueryBuilder
from datadog_checks.vertica.utils import parse_major_version
from datadog_checks.vertica.vertica import VerticaClient

CERTIFICATE_DIR = os.path.join(os.path.dirname(__file__), 'certificate')
cert = os.path.join(CERTIFICATE_DIR, 'cert.cert')
private_key = os.path.join(CERTIFICATE_DIR, 'server.pem')

pytestmark = pytest.mark.unit


def test_ssl_config_ok(aggregator, tls_instance):
    with mock.patch('datadog_checks.vertica.vertica.vertica') as vertica:
        with mock.patch('datadog_checks.base.utils.tls.ssl') as ssl:
            vertica.connect.return_value = mock.MagicMock()
            tls_context = mock.MagicMock()
            ssl.SSLContext.return_value = tls_context
            check = VerticaCheck('vertica', {}, [tls_instance])
            check.check(tls_instance)

            assert check._client.use_tls
            assert tls_context.verify_mode == ssl.CERT_REQUIRED
            assert tls_context.check_hostname is True
            tls_context.load_verify_locations.assert_called_with(cadata=None, cafile=None, capath=CERTIFICATE_DIR)
            tls_context.load_cert_chain.assert_called_with(cert, keyfile=private_key, password=None)

    aggregator.assert_service_check("vertica.can_connect", status=AgentCheck.OK, tags=['db:abc', 'foo:bar'])


def test_ssl_legacy_config_ok(aggregator, tls_instance_legacy):
    with mock.patch('datadog_checks.vertica.vertica.vertica') as vertica:
        with mock.patch('datadog_checks.base.utils.tls.ssl') as ssl:
            vertica.connect.return_value = mock.MagicMock()
            tls_context = mock.MagicMock()
            ssl.SSLContext.return_value = tls_context
            check = VerticaCheck('vertica', {}, [tls_instance_legacy])
            check.check(tls_instance_legacy)

            assert check._client.use_tls
            assert tls_context.verify_mode == ssl.CERT_REQUIRED
            assert tls_context.check_hostname is True
            tls_context.load_verify_locations.assert_called_with(cadata=None, cafile=None, capath=CERTIFICATE_DIR)
            tls_context.load_cert_chain.assert_called_with(cert, keyfile=private_key, password=None)

    aggregator.assert_service_check("vertica.can_connect", status=AgentCheck.OK, tags=['db:abc', 'foo:bar'])


def test_client_logging_enabled(aggregator, instance):
    instance['client_lib_log_level'] = 'DEBUG'

    check = VerticaCheck('vertica', {}, [instance])

    with mock.patch('datadog_checks.vertica.vertica.vertica') as vertica:
        check.check(instance)

        vertica.connect.assert_called_with(
            database=mock.ANY,
            host=mock.ANY,
            port=mock.ANY,
            user=mock.ANY,
            password=mock.ANY,
            backup_server_node=mock.ANY,
            connection_load_balance=mock.ANY,
            connection_timeout=mock.ANY,
            log_level='DEBUG',
            log_path='',
        )


def test_client_logging_disabled(aggregator, instance):
    instance['client_lib_log_level'] = None
    check = VerticaCheck('vertica', {}, [instance])

    with mock.patch('datadog_checks.vertica.vertica.vertica') as vertica:
        check.check(instance)

        vertica.connect.assert_called_with(
            database=mock.ANY,
            host=mock.ANY,
            port=mock.ANY,
            user=mock.ANY,
            password=mock.ANY,
            backup_server_node=mock.ANY,
            connection_load_balance=mock.ANY,
            connection_timeout=mock.ANY,
        )


@pytest.mark.parametrize(
    'agent_log_level, expected_vertica_log_level', [(logging.DEBUG, logging.DEBUG), (TRACE_LEVEL, logging.DEBUG)]
)
def test_client_logging_enabled_debug_if_agent_uses_debug_or_trace(
    aggregator, instance, agent_log_level, expected_vertica_log_level
):
    """
    Improve collection of debug flares by automatically enabling client DEBUG logs when the Agent uses DEBUG logs.
    """
    instance.pop('client_lib_log_level', None)
    root_logger = logging.getLogger()
    root_logger.setLevel(agent_log_level)

    check = VerticaCheck('vertica', {}, [instance])

    with mock.patch('datadog_checks.vertica.vertica.vertica') as vertica:
        check.check(instance)

        vertica.connect.assert_called_with(
            database=mock.ANY,
            host=mock.ANY,
            port=mock.ANY,
            user=mock.ANY,
            password=mock.ANY,
            backup_server_node=mock.ANY,
            connection_load_balance=mock.ANY,
            connection_timeout=mock.ANY,
            log_level=expected_vertica_log_level,
            log_path='',
        )


def test_client_logging_disabled_if_agent_uses_info(aggregator, instance):
    """
    Library logs should be disabled by default, in particular under normal Agent operation (INFO level).
    """
    instance.pop('client_lib_log_level', None)
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    check = VerticaCheck('vertica', {}, [instance])

    with mock.patch('datadog_checks.vertica.vertica.vertica') as vertica:
        check.check(instance)

        vertica.connect.assert_called_with(
            database=mock.ANY,
            host=mock.ANY,
            port=mock.ANY,
            user=mock.ANY,
            password=mock.ANY,
            backup_server_node=mock.ANY,
            connection_load_balance=mock.ANY,
            connection_timeout=mock.ANY,
        )


def test_connection_error_service_check(aggregator, instance, monkeypatch):
    check = VerticaCheck('vertica', {}, [instance])

    monkeypatch.setattr(check._client, 'connect', mock.Mock(side_effect=Exception))

    check.check(instance)

    aggregator.assert_service_check("vertica.can_connect", status=AgentCheck.CRITICAL, tags=['db:datadog', 'foo:bar'])


def test_invalid_groups_in_config(instance):
    instance['metric_groups'] = ['system', 'a_group_that_does_not_exist']

    with pytest.raises(ConfigurationError):
        VerticaCheck('vertica', {}, [instance]).parse_metric_groups()


@pytest.mark.parametrize(
    'version_string, expected',
    [
        ('Vertica Analytic Database v11.1.1-0', '11.1.1+0'),
        ('Vertica Analytic Database v10.0.0-1', '10.0.0+1'),
    ],
)
def test_VerticaCheck_parse_db_version(version_string, expected):
    assert VerticaCheck.parse_db_version(version_string) == expected


@pytest.mark.parametrize('version_string, expected', [('v9.2.0-7', 9), ('v11.1.1-0', 11)])
def test_parse_major_version(version_string, expected):
    assert parse_major_version(version_string) == expected


def test_parse_db_version_only_replaces_first_dash():
    # Kills the core/NumberReplacer mutant at vertica.py:129 (.replace('-', '+', 1) count 1 -> 2).
    assert VerticaCheck.parse_db_version('Vertica Analytic Database v11.1.1-0-beta') == '11.1.1+0-beta'


def test_default_connection_options(instance):
    # Kills NumberReplacer mutants at vertica.py:38 (port default 5433) and vertica.py:47 (timeout default 10),
    # and the core/ReplaceFalseWithTrue mutant at vertica.py:46 (connection_load_balance default False).
    instance.pop('port', None)
    instance.pop('timeout', None)
    instance.pop('connection_load_balance', None)

    check = VerticaCheck('vertica', {}, [instance])

    assert check._port == 5433
    assert check._timeout == 10
    assert check._connection_load_balance is False


def test_parse_metric_groups_all_valid(instance):
    # Kills the core/AddNot mutant at vertica.py:146 (flips `group not in default_metric_groups`).
    instance['metric_groups'] = ['system']
    check = VerticaCheck('vertica', {}, [instance])

    check.parse_metric_groups()

    assert check._metric_groups == ['system']


def test_set_version_metadata_skipped_when_metadata_collection_disabled(instance, datadog_agent):
    # Kills the core/RemoveDecorator mutant at vertica.py:120 (removes @AgentCheck.metadata_entrypoint);
    # without it, set_version_metadata would call self._version() and blow up on the absent connection.
    check = VerticaCheck('vertica', {}, [instance])
    check.check_id = 'test:123'
    datadog_agent._config['enable_metadata_collection'] = False

    check.set_version_metadata()

    datadog_agent.assert_metadata_count(0)


def test_vertica_client_log_defaults_to_root_logger_when_not_provided():
    # Kills the core/ReplaceOrWithAnd mutant at vertica.py:165 (`log or logging.getLogger()` -> `log and ...`).
    assert isinstance(VerticaClient({}, log=None).log, logging.Logger)

    custom_log = logging.getLogger('vertica_test_custom_logger')
    assert VerticaClient({}, log=custom_log).log is custom_log


def test_vertica_client_reconnects_when_load_balance_enabled():
    # Kills the core/AddNot and core/ReplaceOrWithAnd mutants at vertica.py:175 (reconnect condition).
    with mock.patch('datadog_checks.vertica.vertica.vertica') as vertica_mod:
        first_connection = mock.MagicMock()
        first_connection.closed.return_value = False
        vertica_mod.connect.return_value = first_connection

        client = VerticaClient({'connection_load_balance': True})
        client.connect()

        client.connect()

        first_connection.close.assert_called_once()


def test_vertica_client_reuses_connection_without_load_balance():
    # Kills the core/RemoveDecorator mutant at vertica.py:215 (connection_load_balance property removed).
    with mock.patch('datadog_checks.vertica.vertica.vertica') as vertica_mod:
        first_connection = mock.MagicMock()
        first_connection.closed.return_value = False
        vertica_mod.connect.return_value = first_connection

        client = VerticaClient({})
        client.connect()

        client.connect()

        first_connection.close.assert_not_called()


def test_vertica_client_query_version_returns_first_column():
    # Kills NumberReplacer mutants at vertica.py:192 (fetchone()[0] -> fetchone()[1] / fetchone()[-1]).
    client = VerticaClient({})
    client.connection = mock.MagicMock()
    client.connection.cursor.return_value.execute.return_value.fetchone.return_value = ['first', 'second']

    assert client.query_version() == 'first'


def test_vertica_client_options_omit_ssl_when_tls_disabled():
    # Kills the core/AddNot mutant at vertica.py:208 and core/RemoveDecorator mutant at vertica.py:211 (use_tls).
    client = VerticaClient({}, tls_context=None)

    assert 'ssl' not in client.options


def test_vertica_client_connection_load_balance_defaults_false():
    # Kills the core/ReplaceFalseWithTrue mutant at vertica.py:217 (connection_load_balance default False -> True).
    assert VerticaClient({}).connection_load_balance is False


@pytest.mark.parametrize('version, includes_legacy_fields', [(9, True), (10, True), (11, False), (12, False)])
def test_build_projection_storage_queries_legacy_fields_boundary(version, includes_legacy_fields):
    # Kills queries.py:251 mutants: operator swaps raise on tuple concatenation for version < 11, and the
    # comparison/AddNot/NumberReplacer mutants shift the </==/!=/<=/>/>= 11 boundary tested across versions.
    query = QueryBuilder(version).build_projection_storage_queries()[0]['query']

    assert ('wos_used_bytes' in query) is includes_legacy_fields


@pytest.mark.parametrize('version, includes_storage_type', [(9, True), (10, True), (11, False), (12, False)])
def test_build_storage_containers_queries_storage_type_boundary(version, includes_storage_type):
    # Kills queries.py:293 comparison/AddNot/NumberReplacer mutants shifting the version < 11 boundary.
    query = QueryBuilder(version).build_storage_containers_queries()[0]['query']

    assert ('storage_type' in query) is includes_storage_type


def test_build_grouped_query_total_has_no_prefix():
    # Kills queries.py:310 (ReplaceUnaryOperator_Delete_Not / AddNot flips the empty-group_columns branch).
    query = QueryBuilder(9)._build_grouped_query(
        'total',
        [],
        schema='s',
        table_name='t',
        column_to_metric_mapping={'a': 'metric.a'},
        value_select_columns=['sum(a) as a'],
        value_columns=['a'],
    )

    assert query['name'] == 't_total'
    assert query['query'] == 'SELECT sum(a) as a FROM s.t'
    assert query['columns'] == [{'name': 'metric.a', 'type': 'gauge'}]


def test_build_grouped_query_non_empty_group_columns():
    # Kills queries.py:319/323/327/329 (Add_X operator swaps raise on str/list concatenation for a real group).
    query = QueryBuilder(9)._build_grouped_query(
        'grouping',
        ['a'],
        schema='s',
        table_name='t',
        column_to_metric_mapping={'a': 'metric.a', 'b': 'metric.b'},
        value_select_columns=['sum(b) as b'],
        value_columns=['b'],
    )

    assert query['name'] == 't_per_grouping'
    assert query['query'] == 'SELECT a, sum(b) as b FROM s.t GROUP BY a'
    assert query['columns'] == [
        {'name': 'metric.a', 'type': 'tag'},
        {'name': 'grouping.metric.b', 'type': 'gauge'},
    ]
