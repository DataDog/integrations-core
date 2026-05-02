# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import json

import pytest

from datadog_checks.postgres.remote_query import StaticPostgresCheckRegistry, execute_remote_query


def remote_query_request(pg_instance: dict[str, object], query: str) -> dict[str, object]:
    return {
        'target': {
            'host': pg_instance['host'],
            'port': int(pg_instance['port']),
            'dbname': pg_instance['dbname'],
        },
        'query': query,
        'limits': {'maxRows': 10, 'maxBytes': 1048576, 'timeoutMs': 5000},
    }


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_agent_local_executor_select_1_reuses_integration_check_credentials(integration_check, pg_instance):
    check = integration_check(pg_instance)
    request = remote_query_request(pg_instance, 'SELECT 1 AS value')

    response = execute_remote_query(request, StaticPostgresCheckRegistry([check]))

    assert response['status'] == 'SUCCEEDED'
    assert response['columns'][0]['name'] == 'value'
    assert response['rows'] == [{'value': 1}]
    assert response['truncated'] is False
    assert response['stats']['rowCount'] == 1
    assert 'password' not in json.dumps(request).lower()


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_agent_local_executor_fixture_table_query_returns_city_rows(integration_check, pg_instance):
    bob_instance = dict(pg_instance, username='bob', password='bob')
    check = integration_check(bob_instance)
    request = remote_query_request(bob_instance, 'SELECT city, country FROM cities ORDER BY city')

    response = execute_remote_query(request, StaticPostgresCheckRegistry([check]))

    assert response['status'] == 'SUCCEEDED'
    assert response['columns'] == [{'name': 'city', 'type': 'string'}, {'name': 'country', 'type': 'string'}]
    assert response['rows'] == [
        {'city': 'Beautiful city of lights', 'country': 'France'},
        {'city': 'New York', 'country': 'USA'},
    ]
    assert response['truncated'] is False
    assert response['stats']['rowCount'] == 2
    assert 'password' not in json.dumps(request).lower()
