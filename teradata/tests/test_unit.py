# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import logging
import re

import mock
import pytest

try:
    from contextlib import ExitStack
except ImportError:
    from contextlib2 import ExitStack

from datadog_checks.base.constants import ServiceCheck
from datadog_checks.teradata.check import TeradataCheck
from datadog_checks.teradata.utils import submit_version, tags_normalizer, timestamp_validator

from .common import CHECK_NAME, EXPECTED_TAGS, SERVICE_CHECK_CONNECT, SERVICE_CHECK_QUERY, TABLE_DISK_METRICS

pytestmark = pytest.mark.unit


def query_name_from(table_name):
    """Mirror `_execute_query_raw`'s extraction so query names are never the same object as a source-file literal."""
    return re.search(r'(DBC.[^\s]+)', 'FROM {} WHERE 1=1'.format(table_name)).group(1)


@pytest.mark.parametrize(
    'test_instance, expected_tags, conn_params',
    [
        pytest.param(
            {
                "server": "localhost",
                "username": "datadog",
                "password": "dd_teradata",
                "database": "AdventureWorksDW",
            },
            ['teradata_server:localhost', 'teradata_port:1025'],
            {
                "host": "localhost",
                "account": "",
                "database": "AdventureWorksDW",
                "dbs_port": "1025",
                "logmech": None,
                "logdata": "",
                "user": "datadog",
                "password": "dd_teradata",
                "https_port": "443",
                "sslmode": "Prefer",
                "sslprotocol": "TLSv1.2",
            },
            id="Use default options",
        ),
        pytest.param(
            {
                "server": "td-internal",
                "port": 1125,
                "username": "dd",
                "password": "td_datadog",
                "database": "AdventureWorksDW",
            },
            ['teradata_server:td-internal', 'teradata_port:1125'],
            {
                "host": "td-internal",
                "account": "",
                "database": "AdventureWorksDW",
                "dbs_port": "1125",
                "logmech": None,
                "logdata": "",
                "user": "dd",
                "password": "td_datadog",
                "https_port": "443",
                "sslmode": "Prefer",
                "sslprotocol": "TLSv1.2",
            },
            id="Use custom server, db port, and driver path",
        ),
        pytest.param(
            {
                "server": "localhost",
                "username": "dd",
                "password": "td_datadog",
                "database": "AdventureWorksDW",
            },
            ['teradata_server:localhost', 'teradata_port:1025'],
            {
                "host": "localhost",
                "account": "",
                "database": "AdventureWorksDW",
                "dbs_port": "1025",
                "logmech": None,
                "logdata": "",
                "user": "dd",
                "password": "td_datadog",
                "https_port": "443",
                "sslmode": "Prefer",
                "sslprotocol": "TLSv1.2",
            },
            id="Use default TLS options",
        ),
        pytest.param(
            {
                "server": "localhost",
                "https_port": 543,
                "ssl_mode": "Require",
                "username": "dd",
                "password": "td_datadog",
                "database": "AdventureWorksDW",
            },
            ['teradata_server:localhost', 'teradata_port:1025'],
            {
                "host": "localhost",
                "account": "",
                "database": "AdventureWorksDW",
                "dbs_port": "1025",
                "logmech": None,
                "logdata": "",
                "user": "dd",
                "password": "td_datadog",
                "https_port": "543",
                "sslmode": "Require",
                "sslprotocol": "TLSv1.2",
            },
            id="Use custom TLS options",
        ),
        pytest.param(
            {
                "server": "localhost",
                "auth_mechanism": "JWT",
                "auth_data": "token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4g"
                "RG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c",
                "database": "AdventureWorksDW",
            },
            ['teradata_server:localhost', 'teradata_port:1025'],
            {
                "host": "localhost",
                "account": "",
                "database": "AdventureWorksDW",
                "dbs_port": "1025",
                "logmech": "JWT",
                "logdata": "token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9"
                "lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c",
                "user": "",
                "password": "",
                "https_port": "443",
                "sslmode": "Prefer",
                "sslprotocol": "TLSv1.2",
            },
            id="Use JWT auth option",
        ),
        pytest.param(
            {
                "server": "localhost",
                "auth_mechanism": "KRB5",
                "auth_data": "dd@localhost@@td_datadog",
                "database": "AdventureWorksDW",
            },
            ['teradata_server:localhost', 'teradata_port:1025'],
            {
                "host": "localhost",
                "account": "",
                "database": "AdventureWorksDW",
                "dbs_port": "1025",
                "logmech": "KRB5",
                "logdata": "dd@localhost@@td_datadog",
                "user": "",
                "password": "",
                "https_port": "443",
                "sslmode": "Prefer",
                "sslprotocol": "TLSv1.2",
            },
            id="Use KRB5 auth option",
        ),
        pytest.param(
            {
                "server": "localhost",
                "auth_mechanism": "LDAP",
                "auth_data": "dd@@td_datadog",
                "database": "AdventureWorksDW",
            },
            ['teradata_server:localhost', 'teradata_port:1025'],
            {
                "host": "localhost",
                "account": "",
                "database": "AdventureWorksDW",
                "dbs_port": "1025",
                "logmech": "LDAP",
                "logdata": "dd@@td_datadog",
                "user": "",
                "password": "",
                "https_port": "443",
                "sslmode": "Prefer",
                "sslprotocol": "TLSv1.2",
            },
            id="Use LDAP auth option",
        ),
        pytest.param(
            {
                "server": "localhost",
                "auth_mechanism": "TDNEGO",
                "database": "AdventureWorksDW",
            },
            ['teradata_server:localhost', 'teradata_port:1025'],
            {
                "host": "localhost",
                "account": "",
                "database": "AdventureWorksDW",
                "dbs_port": "1025",
                "logmech": "TDNEGO",
                "logdata": "",
                "user": "",
                "password": "",
                "https_port": "443",
                "sslmode": "Prefer",
                "sslprotocol": "TLSv1.2",
            },
            id="Use TDNEGO auth option",
        ),
        pytest.param(
            {
                "server": "localhost",
                "username": "datadog",
                "password": "dd_teradata",
                "auth_mechanism": "TD2",
                "database": "AdventureWorksDW",
            },
            ['teradata_server:localhost', 'teradata_port:1025'],
            {
                "host": "localhost",
                "account": "",
                "database": "AdventureWorksDW",
                "dbs_port": "1025",
                "logmech": "TD2",
                "logdata": "",
                "user": "datadog",
                "password": "dd_teradata",
                "https_port": "443",
                "sslmode": "Prefer",
                "sslprotocol": "TLSv1.2",
            },
            id="Use TD2 auth option (default)",
        ),
    ],
)
def test_connect(test_instance, dd_run_check, aggregator, expected_tags, conn_params):
    check = TeradataCheck(CHECK_NAME, {}, [test_instance])
    conn = mock.MagicMock()
    cursor = conn.cursor()
    cursor.rowcount = float('+inf')

    teradatasql = mock.MagicMock()
    teradatasql.connect.return_value = conn

    mocks = [
        ('datadog_checks.teradata.check.teradatasql', teradatasql),
        ('datadog_checks.teradata.check.TERADATASQL_IMPORT_ERROR', None),
    ]

    with ExitStack() as stack:
        for mock_call in mocks:
            stack.enter_context(mock.patch(*mock_call))
        dd_run_check(check)
        assert check._connection == conn

    teradatasql.connect.assert_called_with(json.dumps(conn_params))
    aggregator.assert_service_check(SERVICE_CHECK_CONNECT, ServiceCheck.OK, tags=expected_tags)
    aggregator.assert_service_check(SERVICE_CHECK_QUERY, ServiceCheck.OK, tags=expected_tags)


def test_connection_errors(cursor_factory, dd_run_check, aggregator, instance, caplog):
    with cursor_factory(exception=True):
        check = TeradataCheck(CHECK_NAME, {}, [instance])
        with pytest.raises(Exception, match="Exception: Unable to connect to Teradata."):
            dd_run_check(check)
        aggregator.assert_service_check(SERVICE_CHECK_CONNECT, ServiceCheck.CRITICAL, tags=EXPECTED_TAGS)
        aggregator.assert_service_check(SERVICE_CHECK_QUERY, count=0)


def test_query_errors(dd_run_check, aggregator, instance):
    check = TeradataCheck(CHECK_NAME, {}, [instance])
    query_error = mock.Mock(side_effect=Exception("teradatasql.Error"))
    check._query_manager.executor = mock.MagicMock()
    check._query_manager.executor.side_effect = query_error

    teradatasql = mock.MagicMock()

    mocks = [
        ('datadog_checks.teradata.check.teradatasql', teradatasql),
        ('datadog_checks.teradata.check.TERADATASQL_IMPORT_ERROR', None),
    ]

    with ExitStack() as stack:
        for mock_call in mocks:
            stack.enter_context(mock.patch(*mock_call))
        dd_run_check(check)

    assert check._query_errors > 0

    aggregator.assert_service_check(SERVICE_CHECK_CONNECT, ServiceCheck.OK, tags=EXPECTED_TAGS)
    aggregator.assert_service_check(SERVICE_CHECK_QUERY, ServiceCheck.CRITICAL, tags=EXPECTED_TAGS)


def test_no_rows_returned(dd_run_check, aggregator, instance, caplog):
    caplog.clear()
    caplog.set_level(logging.WARNING)
    check = TeradataCheck(CHECK_NAME, {}, [instance])
    conn = mock.MagicMock()
    cursor = conn.cursor()
    cursor.rowcount = 0

    teradatasql = mock.MagicMock()
    teradatasql.connect.return_value = conn

    mocks = [
        ('datadog_checks.teradata.check.teradatasql', teradatasql),
        ('datadog_checks.teradata.check.TERADATASQL_IMPORT_ERROR', None),
    ]

    with ExitStack() as stack:
        for mock_call in mocks:
            stack.enter_context(mock.patch(*mock_call))
        dd_run_check(check)

    assert "Failed to fetch records from query:" in caplog.text
    aggregator.assert_service_check(SERVICE_CHECK_CONNECT, ServiceCheck.OK, tags=EXPECTED_TAGS)
    aggregator.assert_service_check(SERVICE_CHECK_QUERY, ServiceCheck.CRITICAL, tags=EXPECTED_TAGS)


@pytest.mark.parametrize(
    'config, expected',
    [
        pytest.param(['DimDate', 'DimSalesReason'], ({'DimDate', 'DimSalesReason'}, set()), id="Tables filter list"),
        pytest.param(
            {'include': ['DimScenario', 'DimCustomer']},
            ({'DimScenario', 'DimCustomer'}, set()),
            id="Tables filter map: include only",
        ),
        pytest.param(
            {'exclude': ['DimCustomer', 'DimDepartmentGroup']},
            (set(), {'DimCustomer', 'DimDepartmentGroup'}),
            id="Tables filter map: exclude only",
        ),
        pytest.param(
            {'include': ['DimCustomer', 'DimDepartmentGroup'], 'exclude': ['DimGeography', 'DimEmployee']},
            ({'DimCustomer', 'DimDepartmentGroup'}, {'DimGeography', 'DimEmployee'}),
            id="Tables filter map: include and exclude",
        ),
        pytest.param(
            {'include': ['DimCurrency', 'DimEmployee'], 'exclude': ['DimCurrency', 'DimCustomer']},
            ({'DimEmployee'}, {'DimCurrency', 'DimCustomer'}),
            id="Tables filter map: exclusion overlap",
        ),
        pytest.param(
            {
                'include': ['DimDepartmentGroup', 'DimCustomer', 'DimDepartmentGroup'],
                'exclude': ['DimGeography', 'DimEmployee'],
            },
            ({'DimDepartmentGroup', 'DimCustomer'}, {'DimGeography', 'DimEmployee'}),
            id="Tables filter map: duplicate table in include",
        ),
        pytest.param(
            {'include': ['DimSalesReason', 'DimScenario'], 'exclude': ['DimGeography', 'DimCustomer', 'DimCustomer']},
            ({'DimSalesReason', 'DimScenario'}, {'DimGeography', 'DimCustomer'}),
            id="Tables filter map: duplicate table in exclude",
        ),
        pytest.param([], (set(), set()), id="No tables filter: collect all tables"),
    ],
)
def test_tables_filter(cursor_factory, config, expected, instance, dd_run_check, aggregator):
    instance['tables'] = config
    check = TeradataCheck(CHECK_NAME, {}, [instance])
    with cursor_factory():
        dd_run_check(check)
    tag_template = 'td_table:{}'
    for metric in TABLE_DISK_METRICS:
        if isinstance(config, list):
            if not config:
                aggregator.assert_metric_has_tag_prefix(metric, 'td_table', at_least=1)
            for include_table in config:
                aggregator.assert_metric_has_tag(metric, tag_template.format(include_table), at_least=1)
                aggregator.assert_metric_has_tag(metric, tag_template.format("DimOrganization"), count=0)
        else:
            for include_table in expected[0]:
                aggregator.assert_metric_has_tag(metric, tag_template.format(include_table), at_least=1)
            for exclude_table in expected[1]:
                aggregator.assert_metric_has_tag(metric, tag_template.format(exclude_table), count=0)
            aggregator.assert_metric_has_tag(metric, tag_template.format("DimOrganization"), count=0)

    assert check._tables_filter == expected


def test_init_queries_use_defaults_when_flags_omitted():
    # Kills the core/NumberReplacer mutant at check.py:43,45 (the `False` default becoming `True` when the
    # optional flags are absent from the instance).
    check = TeradataCheck(CHECK_NAME, {}, [{"server": "s", "database": "d"}])
    names = {query.query_data['name'] for query in check._query_manager.queries}
    assert names == {'disk_space', 'amp_usage', 'teradata_version'}


def test_init_queries_include_optional_when_flags_enabled():
    # Kills the core/AddNot mutant at check.py:43,45 (inverting `is_affirmative(...)` would drop these queries).
    instance = {"server": "s", "database": "d", "collect_res_usage_metrics": True, "collect_table_disk_metrics": True}
    check = TeradataCheck(CHECK_NAME, {}, [instance])
    names = {query.query_data['name'] for query in check._query_manager.queries}
    assert names == {'disk_space', 'amp_usage', 'teradata_version', 'resource_usage', 'all_space'}


def test_connect_raises_when_import_error_present(instance, caplog):
    # Kills the core/AddNot mutant at check.py:129 (`if TERADATASQL_IMPORT_ERROR:` inverted would skip the raise).
    check = TeradataCheck(CHECK_NAME, {}, [instance])
    check.load_configuration_models()
    import_error = ImportError('teradatasql driver unavailable')
    with mock.patch('datadog_checks.teradata.check.TERADATASQL_IMPORT_ERROR', import_error):
        with pytest.raises(ImportError):
            with check.connect():
                pass
    assert 'Teradata SQL Driver module is unavailable' in caplog.text


def test_connect_closes_connection_on_success(instance):
    # Kills the core/AddNot mutant at check.py:145 (`if conn:` inverted would skip closing the connection).
    check = TeradataCheck(CHECK_NAME, {}, [instance])
    check.load_configuration_models()
    conn = mock.MagicMock()
    teradatasql_mock = mock.MagicMock()
    teradatasql_mock.connect.return_value = conn

    mocks = [
        ('datadog_checks.teradata.check.teradatasql', teradatasql_mock),
        ('datadog_checks.teradata.check.TERADATASQL_IMPORT_ERROR', None),
    ]
    with ExitStack() as stack:
        for mock_call in mocks:
            stack.enter_context(mock.patch(*mock_call))
        with check.connect() as yielded_conn:
            assert yielded_conn == conn
            assert conn.close.called is False

    assert conn.close.called is True


def test_connect_logs_and_reraises_on_connection_exception(instance, caplog, cursor_factory):
    # Kills the core/ExceptionReplacer mutant at check.py:141 (the log before re-raising would never execute).
    check = TeradataCheck(CHECK_NAME, {}, [instance])
    check.load_configuration_models()
    with cursor_factory(exception=True):
        with pytest.raises(Exception, match="Unable to connect to Teradata"):
            with check.connect():
                pass
    assert 'Unable to connect to Teradata.' in caplog.text


def test_execute_query_raw_rowcount_boundary(instance):
    # Kills the core/ReplaceComparisonOperator_Lt_LtE mutant at check.py:106 (`rowcount < 1` vs `rowcount <= 1`).
    check = TeradataCheck(CHECK_NAME, {}, [instance])
    check.load_configuration_models()
    cursor = mock.MagicMock()
    cursor.rowcount = 1
    cursor.fetchall.return_value = []
    connection = mock.MagicMock()
    connection.cursor.return_value = cursor
    check._connection = connection

    result = list(check._execute_query_raw('SELECT * FROM DBC.DiskSpaceV'))

    assert result == []
    assert check._query_errors == 0


def test_execute_query_raw_recovers_from_row_processing_error(instance, caplog):
    # Kills the core/ExceptionReplacer mutant at check.py:114 (the per-row exception would no longer be caught).
    caplog.set_level(logging.DEBUG)
    check = TeradataCheck(CHECK_NAME, {}, [instance])
    check.load_configuration_models()
    row = ['bad_row']
    cursor = mock.MagicMock()
    cursor.rowcount = 1
    cursor.fetchall.return_value = [row]
    connection = mock.MagicMock()
    connection.cursor.return_value = cursor
    check._connection = connection
    check._queries_processor = mock.Mock(side_effect=ValueError('boom'))

    result = list(check._execute_query_raw('SELECT * FROM DBC.DiskSpaceV'))

    assert result == [row]
    assert 'Unable to process row returned from query' in caplog.text


def test_executor_error_handler_increments_and_returns_error(instance):
    # Kills the core/NumberReplacer mutant at check.py:122 (`self._query_errors += 1` becoming `+= -1` or similar).
    check = TeradataCheck(CHECK_NAME, {}, [instance])
    error = 'teradatasql.Error: boom'

    result = check._executor_error_handler(error)

    assert result == error
    assert check._query_errors == 1


def test_queries_processor_routes_version_query(instance):
    # Kills the core/ReplaceComparisonOperator_Eq_Is mutant at check.py:164 (query_name is never the same object
    # as the literal, so an `is` comparison would wrongly skip the version route).
    check = TeradataCheck(CHECK_NAME, {}, [instance])
    check.load_configuration_models()
    check.initialize_config()
    check.set_metadata = mock.Mock()
    query_name = query_name_from('DBC.DBCInfoV')

    result = check._queries_processor(['17.10.03.01'], query_name)

    assert result == ['17.10.03.01']
    assert check.set_metadata.called


def test_queries_processor_routes_resource_usage_query(instance):
    # Kills the core/ReplaceComparisonOperator_Eq_Is mutant at check.py:169 (same identity-vs-equality issue for
    # the resource usage route).
    check = TeradataCheck(CHECK_NAME, {}, [instance])
    check.load_configuration_models()
    check.initialize_config()
    query_name = query_name_from('DBC.ResSpmaView')

    result = check._queries_processor(['not-a-timestamp', 1.0], query_name)

    assert result == []
    assert check._query_errors == 1


def test_queries_processor_skips_special_routes_for_lexically_smaller_name(instance):
    # Kills core/ReplaceComparisonOperator_{Lt,LtE,NotEq}_Eq and core/ReplaceComparisonOperator_Eq_IsNot mutants
    # at check.py:164,169,175 (a query name lexically below all three literals would wrongly match them).
    check = TeradataCheck(CHECK_NAME, {}, [instance])
    check.load_configuration_models()
    check.initialize_config()
    check.set_metadata = mock.Mock()
    query_name = query_name_from('DBC.AAA')
    row = ['amp', 'acct', 'db', 'tbl']

    result = check._queries_processor(row, query_name)

    assert result == ['amp', 'acct', 'db', 'tbl']
    assert not check.set_metadata.called
    assert check._query_errors == 0


def test_queries_processor_skips_special_routes_for_lexically_larger_name(instance):
    # Kills core/ReplaceComparisonOperator_{Gt,GtE}_Eq mutants at check.py:164,169,175 (a query name lexically
    # above all three literals would wrongly match them).
    check = TeradataCheck(CHECK_NAME, {}, [instance])
    check.load_configuration_models()
    check.initialize_config()
    check.set_metadata = mock.Mock()
    query_name = query_name_from('DBC.ZZZ')
    row = ['amp', 'acct', 'db', 'tbl']

    result = check._queries_processor(row, query_name)

    assert result == ['amp', 'acct', 'db', 'tbl']
    assert not check.set_metadata.called
    assert check._query_errors == 0


def test_queries_processor_all_space_requires_disk_metrics_flag(instance):
    # Kills the core/ReplaceAndWithOr mutant at check.py:174-178 (with the flag off, an `or` would wrongly enter
    # the table-filtering branch and discard the row).
    instance = dict(instance)
    instance['collect_table_disk_metrics'] = False
    instance['tables'] = {'exclude': ['ExcludedTable']}
    check = TeradataCheck(CHECK_NAME, {}, [instance])
    check.load_configuration_models()
    check.initialize_config()
    query_name = query_name_from('DBC.AllSpaceV')
    row = ['amp', 'acct', 'db', 'ExcludedTable']

    result = check._queries_processor(row, query_name)

    assert result == ['amp', 'acct', 'db', 'ExcludedTable']


def test_timestamp_validator_rejects_non_int_type(caplog, instance):
    # Kills the core/AddNot mutant at utils.py:62 (`type(row_ts) is not int` inverted would let a float through).
    check = TeradataCheck(CHECK_NAME, {}, [instance])
    row = [3.5, 100]

    result = timestamp_validator(check, row)

    assert result == []
    assert 'is invalid' in caplog.text
    assert check._query_errors == 1


def test_timestamp_validator_valid_at_upper_boundary(caplog, instance):
    # Kills the core/{NumberReplacer,ReplaceComparisonOperator_Gt_GtE} mutants at utils.py:69,71 (an exact
    # 3600s-old timestamp is still valid).
    check = TeradataCheck(CHECK_NAME, {}, [instance])
    row = [1700000000 - 3600, 1.0]

    with mock.patch('datadog_checks.teradata.utils.time.time', return_value=1700000000):
        result = timestamp_validator(check, row)

    assert result == row
    assert caplog.text == ''
    assert check._query_errors == 0


def test_timestamp_validator_invalid_just_past_upper_boundary(caplog, instance):
    # Kills the core/{NumberReplacer,ReplaceComparisonOperator_Gt_GtE} mutants at utils.py:69,71 (3601s old must
    # be flagged as invalid with the "1h in the past" message).
    check = TeradataCheck(CHECK_NAME, {}, [instance])
    row = [1700000000 - 3601, 1.0]

    with mock.patch('datadog_checks.teradata.utils.time.time', return_value=1700000000):
        result = timestamp_validator(check, row)

    assert result == []
    assert 'Row timestamp is more than 1h in the past' in caplog.text
    assert check._query_errors == 1


def test_timestamp_validator_valid_at_lower_boundary(caplog, instance):
    # Kills the core/{NumberReplacer,ReplaceComparisonOperator_Lt_LtE} mutants at utils.py:69,73 (an exact
    # 600s-in-the-future timestamp is still valid).
    check = TeradataCheck(CHECK_NAME, {}, [instance])
    row = [1700000000 + 600, 1.0]

    with mock.patch('datadog_checks.teradata.utils.time.time', return_value=1700000000):
        result = timestamp_validator(check, row)

    assert result == row
    assert caplog.text == ''
    assert check._query_errors == 0


def test_timestamp_validator_invalid_just_past_lower_boundary(caplog, instance):
    # Kills the core/{NumberReplacer,ReplaceComparisonOperator_Lt_LtE} mutants at utils.py:69,73 (601s in the
    # future must be flagged as invalid with the "10 min in the future" message).
    check = TeradataCheck(CHECK_NAME, {}, [instance])
    row = [1700000000 + 601, 1.0]

    with mock.patch('datadog_checks.teradata.utils.time.time', return_value=1700000000):
        result = timestamp_validator(check, row)

    assert result == []
    assert 'Row timestamp is more than 10 min in the future' in caplog.text
    assert check._query_errors == 1


def test_tags_normalizer_flags_empty_amp_for_disk_space(instance):
    # Kills row-index mutants at utils.py:83 (td_amp must read row[0], not another index).
    query_name = query_name_from('DBC.DiskSpaceV')

    result = tags_normalizer(["", "acct", "db", "unused"], query_name)

    assert result == ["undefined", "acct", "db", "unused"]


def test_tags_normalizer_flags_empty_account_for_disk_space(instance):
    # Kills row-index mutants at utils.py:83 (td_account must read row[1], not another index).
    query_name = query_name_from('DBC.DiskSpaceV')

    result = tags_normalizer(["amp", "", "db", "unused"], query_name)

    assert result == ["amp", "undefined", "db", "unused"]


def test_tags_normalizer_flags_empty_table_for_all_space(instance):
    # Kills row-index mutants at utils.py:88 (td_table must read row[3], not another index).
    query_name = query_name_from('DBC.AllSpaceV')

    result = tags_normalizer(["amp", "acct", "db", ""], query_name)

    assert result == ["amp", "acct", "db", "undefined"]


def test_tags_normalizer_flags_empty_database_for_all_space(instance):
    # Kills row-index mutants at utils.py:88 (td_database must read row[2], not another index).
    query_name = query_name_from('DBC.AllSpaceV')

    result = tags_normalizer(["amp", "acct", "", "tbl"], query_name)

    assert result == ["amp", "acct", "undefined", "tbl"]


def test_tags_normalizer_flags_empty_user_for_amp_usage(instance):
    # Kills row-index mutants at utils.py:92 (td_user must read row[2], not another index).
    query_name = query_name_from('DBC.AMPUsageV')

    result = tags_normalizer(["amp", "acct", "", "tbl"], query_name)

    assert result == ["amp", "acct", "undefined", "tbl"]


def test_tags_normalizer_ignores_lexically_smaller_query_name(instance):
    # Kills core/ReplaceComparisonOperator_{Lt,LtE,NotEq,IsNot}_Eq mutants at utils.py:97 (a query name lexically
    # below every known stats_name would wrongly match one of them).
    query_name = query_name_from('DBC.AAA')

    result = tags_normalizer(["", "acct", "db", "tbl"], query_name)

    assert result == ["", "acct", "db", "tbl"]


def test_tags_normalizer_ignores_lexically_larger_query_name(instance):
    # Kills core/ReplaceComparisonOperator_{Gt,GtE}_Eq mutants at utils.py:97 (a query name lexically above every
    # known stats_name would wrongly match one of them).
    query_name = query_name_from('DBC.ZZZ')

    result = tags_normalizer(["", "acct", "db", "tbl"], query_name)

    assert result == ["", "acct", "db", "tbl"]


def test_submit_version_uses_first_row_element(instance):
    # Kills the core/NumberReplacer mutant at utils.py:113 (`row[0]` becoming `row[1]`/`row[-1]`).
    check = TeradataCheck(CHECK_NAME, {}, [instance])
    check.set_metadata = mock.Mock()

    submit_version(check, ['1.2.3.4', '9.9.9.9'])

    check.set_metadata.assert_called_once()
    assert check.set_metadata.call_args.args[1] == '1.2.3.4'


def test_submit_version_recovers_from_processing_error(instance, caplog):
    # Kills the core/ExceptionReplacer mutant at utils.py:121 (the malformed-row exception would no longer be
    # caught).
    check = TeradataCheck(CHECK_NAME, {}, [instance])

    submit_version(check, [])

    assert 'Could not collect version info' in caplog.text


def test_submit_version_skips_when_metadata_collection_disabled(instance, caplog):
    # Kills the core/RemoveDecorator mutant at utils.py:105 (without `@AgentCheck.metadata_entrypoint`, the
    # function would run even though metadata collection is disabled).
    check = TeradataCheck(CHECK_NAME, {}, [instance])
    with mock.patch.object(check, 'is_metadata_collection_enabled', return_value=False):
        submit_version(check, [])

    assert caplog.text == ''
