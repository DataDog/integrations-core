# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import json

import pytest

from datadog_checks.postgres.remote_query import StaticPostgresCheckRegistry, execute_remote_query


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_agent_local_executor_select_1_reuses_integration_check_credentials(integration_check, pg_instance):
    check = integration_check(pg_instance)
    request = {
        'target': {
            'host': pg_instance['host'],
            'port': int(pg_instance['port']),
            'dbname': pg_instance['dbname'],
        },
        'query': 'SELECT 1 AS value',
        'limits': {'maxRows': 10, 'maxBytes': 1048576, 'timeoutMs': 5000},
    }

    response = execute_remote_query(request, StaticPostgresCheckRegistry([check]))

    assert response['status'] == 'SUCCEEDED'
    assert response['columns'][0]['name'] == 'value'
    assert response['rows'] == [{'value': 1}]
    assert response['truncated'] is False
    assert response['stats']['rowCount'] == 1
    assert 'password' not in json.dumps(request).lower()
