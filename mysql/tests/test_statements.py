# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.mysql.statements import MySQLStatementMetrics


@pytest.mark.unit
def test_statements_get_row_tags():
    check = MySQLStatementMetrics(None)

    # Happy path test case
    assert check.get_row_tags(
        {
            'schema': 'network',
            'digest': '44e35cee979ba420eb49a8471f852bbe15b403c89742704817dfbaace0d99dbb',
            'query': 'SELECT @@`version_comment` LIMIT ?',
            'count': 41,
            'time': 66721400,
            'lock_time': 18298000,
        }
    ) == [
        'digest:44e35cee979ba420eb49a8471f852bbe15b403c89742704817dfbaace0d99dbb',
        'schema:network',
        'query:SELECT @@`version_comment` LIMIT ?',
        'query_signature:34396233428647c0',
    ]

    # Case with no digest
    assert check.get_row_tags(
        {
            'schema': None,
            'digest': None,
            'query': None,
            'count': 41,
            'time': 66721400,
            'lock_time': 18298000,
        }
    ) == [
        'digest:unavailable',
        'schema:unavailable',
        'query:unavailable',
        'query_signature:unavailable',
    ]

    # Case with no schema
    assert check.get_row_tags(
        {
            'schema': None,
            'digest': '44e35cee979ba420eb49a8471f852bbe15b403c89742704817dfbaace0d99dbb',
            'query': 'TRUNCATE TABLE network.ip_source',
            'count': 41,
            'time': 66721400,
            'lock_time': 18298000,
        }
    ) == [
        'digest:44e35cee979ba420eb49a8471f852bbe15b403c89742704817dfbaace0d99dbb',
        'query:TRUNCATE TABLE network.ip_source',
        'query_signature:e01dc7eb2ba97a26',
    ]
