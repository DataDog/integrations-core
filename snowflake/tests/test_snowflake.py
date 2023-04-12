# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy
from decimal import Decimal
from typing import Any, Callable, Dict  # noqa: F401

import mock

from datadog_checks.base.stubs.aggregator import AggregatorStub  # noqa: F401
from datadog_checks.base.utils.db import Query
from datadog_checks.snowflake import SnowflakeCheck, queries

from .common import CHECK_NAME, EXPECTED_TAGS


def test_emits_critical_service_check_when_service_is_down(dd_run_check, aggregator, instance):
    config = copy.deepcopy(instance)
    config['login_timeout'] = 5
    check = SnowflakeCheck(CHECK_NAME, {}, [config])
    dd_run_check(check)
    aggregator.assert_service_check('snowflake.can_connect', SnowflakeCheck.CRITICAL)


def test_no_schema(dd_run_check, aggregator, instance):
    config = copy.deepcopy(instance)
    del config['schema']
    config['login_timeout'] = 5
    check = SnowflakeCheck(CHECK_NAME, {}, [config])
    dd_run_check(check)
    aggregator.assert_service_check('snowflake.can_connect', SnowflakeCheck.CRITICAL)


def test_token_path(dd_run_check, aggregator):
    instance = {
        'username': 'testuser',
        'account': 'account',
        'role': 'ACCOUNTADMIN',
        'authenticator': 'oauth',
        'token_path': '/path/to/token',
    }

    default_args = {
        'user': 'testuser',
        'password': None,
        'account': 'account',
        'database': 'SNOWFLAKE',
        'schema': 'ACCOUNT_USAGE',
        'warehouse': None,
        'role': 'ACCOUNTADMIN',
        'passcode_in_password': False,
        'passcode': None,
        'client_prefetch_threads': 4,
        'login_timeout': 60,
        'ocsp_response_cache_filename': None,
        'authenticator': 'oauth',
        'client_session_keep_alive': False,
        'private_key': None,
        'proxy_host': None,
        'proxy_port': None,
        'proxy_user': None,
        'proxy_password': None,
    }

    tokens = ['mytoken1', 'mytoken2', 'mytoken3']

    check = SnowflakeCheck(CHECK_NAME, {}, [instance])
    with mock.patch(
        'datadog_checks.snowflake.check.open',
        side_effect=[mock.mock_open(read_data=tok).return_value for tok in tokens],
    ), mock.patch('datadog_checks.snowflake.check.sf') as sf:
        dd_run_check(check)
        sf.connect.assert_called_once_with(token='mytoken1', **default_args)

        dd_run_check(check)
        sf.connect.assert_called_with(token='mytoken2', **default_args)

        dd_run_check(check)
        sf.connect.assert_called_with(token='mytoken3', **default_args)


def test_query_metrics(dd_run_check, aggregator, instance):
    # type: (Callable[[SnowflakeCheck], None], AggregatorStub, Dict[str, Any]) -> None

    expected_query_metrics = [
        (
            'USE',
            'COMPUTE_WH',
            'SNOWFLAKE',
            None,
            Decimal('4.333333'),
            Decimal('24.555556'),
            Decimal('0.000000'),
            Decimal('0.000000'),
            Decimal('0.000000'),
            Decimal('0.000000'),
            Decimal('0.000000'),
        ),
    ]

    expected_tags = EXPECTED_TAGS + ['warehouse:COMPUTE_WH', 'database:SNOWFLAKE', 'schema:None', 'query_type:USE']
    with mock.patch('datadog_checks.snowflake.SnowflakeCheck.execute_query_raw', return_value=expected_query_metrics):
        check = SnowflakeCheck(CHECK_NAME, {}, [instance])
        check._conn = mock.MagicMock()
        check._query_manager.queries = [Query(queries.QueryHistory)]
        dd_run_check(check)

    aggregator.assert_metric('snowflake.query.execution_time', value=4.333333, tags=expected_tags)
    aggregator.assert_metric('snowflake.query.compilation_time', value=24.555556, tags=expected_tags)
    aggregator.assert_metric('snowflake.query.bytes_scanned', value=0, count=1, tags=expected_tags)
    aggregator.assert_metric('snowflake.query.bytes_written', value=0, count=1, tags=expected_tags)
    aggregator.assert_metric('snowflake.query.bytes_deleted', value=0, count=1, tags=expected_tags)
    aggregator.assert_metric('snowflake.query.bytes_spilled.local', value=0, count=1, tags=expected_tags)
    aggregator.assert_metric('snowflake.query.bytes_spilled.remote', value=0, count=1, tags=expected_tags)


def test_version_metadata(dd_run_check, instance, datadog_agent):
    expected_version = [('4.30.2',)]
    version_metadata = {
        'version.major': '4',
        'version.minor': '30',
        'version.patch': '2',
        'version.raw': '4.30.2',
        'version.scheme': 'semver',
    }
    with mock.patch('datadog_checks.snowflake.SnowflakeCheck.execute_query_raw', return_value=expected_version):
        check = SnowflakeCheck(CHECK_NAME, {}, [instance])
        check.check_id = 'test:123'
        check._conn = mock.MagicMock()
        check._query_manager.queries = []
        dd_run_check(check)

    datadog_agent.assert_metadata('test:123', version_metadata)
