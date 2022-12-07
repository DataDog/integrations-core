# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import logging

import mock
import pytest

try:
    from contextlib import ExitStack
except ImportError:
    from contextlib2 import ExitStack

from datadog_checks.base.constants import ServiceCheck
from datadog_checks.teradata.check import TeradataCheck

from .common import CHECK_NAME, EXPECTED_TAGS, SERVICE_CHECK_CONNECT, SERVICE_CHECK_QUERY, TABLE_DISK_METRICS


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
