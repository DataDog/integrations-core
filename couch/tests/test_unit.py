# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from copy import deepcopy
from unittest.mock import MagicMock

import pytest

from datadog_checks.base.utils.http_exceptions import HTTPStatusError
from datadog_checks.couch import CouchDb
from datadog_checks.couch.couch import CouchDB1, CouchDB2

from . import common


@pytest.mark.parametrize(
    'test_case, extra_config, expected_http_kwargs',
    [
        (
            "legacy auth config",
            {'user': 'legacy_foo', 'password': 'legacy_bar'},
            {'auth': ('legacy_foo', 'legacy_bar')},
        ),
        ("new auth config", {'username': 'new_foo', 'password': 'new_bar'}, {'auth': ('new_foo', 'new_bar')}),
        ("timeout", {'timeout': 17}, {'timeout': (17, 17)}),
    ],
)
def test_config(test_case, extra_config, expected_http_kwargs):
    instance = deepcopy(common.BASIC_CONFIG)
    instance.update(extra_config)
    check = CouchDb(common.CHECK_NAME, {}, instances=[instance])

    for key, value in expected_http_kwargs.items():
        assert check.http.options[key] == value


def test_new_version_system_metrics(load_test_data):
    # Testing the _build_system_metrics method I'm feeding it a json that has a the updated
    # keys that was added in version 3.4 that was causing the check to break. The idea here
    # is that I'm going to give the method the json then assert that it's able to go through
    # it thhorougly by the number of function calls and debug log calls.

    # Mock everything needed for the function to run
    mock_agent_check = MagicMock()
    mock_agent_check.gauge = MagicMock()
    mock_agent_check.log = MagicMock()

    couchdb_check = CouchDB2(mock_agent_check)
    tags = ["test:tag"]

    # The fixture file json is loaded as a fixture in the confest.py file
    couchdb_check._build_system_metrics(load_test_data, tags)

    assert mock_agent_check.gauge.call_count >= 183
    mock_agent_check.log.debug.assert_any_call("Skipping distribution events")


def test_v1_status_error_without_response_is_not_an_attribute_error():
    """The auth-token seam raises without a response, so the exclusion guard must not dereference None."""
    mock_agent_check = MagicMock()
    mock_agent_check.instance = {}
    mock_agent_check.MAX_DB = 50
    mock_agent_check.get.side_effect = [{}, ['db1'], HTTPStatusError('403 Client Error')]

    couchdb_check = CouchDB1(mock_agent_check)

    data = couchdb_check.get_data('http://localhost:5984', [])

    # The database is unresolved, so it is absent rather than present with a None placeholder
    # that _create_metric would dereference.
    assert data['databases'] == {}
    mock_agent_check.warning.assert_not_called()


def test_v1_unresolved_database_still_emits_overall_stats():
    """A per-database status the exclusion guard cannot act on must not cost the whole run.

    The auth-token seam raises with no response at all, so the guard has no status to read and the
    database stays unresolved. The overall stats still have to reach the aggregator.
    """
    mock_agent_check = MagicMock()
    mock_agent_check.instance = {}
    mock_agent_check.MAX_DB = 50
    mock_agent_check.get_server.return_value = 'http://localhost:5984'
    mock_agent_check.get_config_tags.return_value = []
    overall_stats = {'httpd': {'requests': {'current': 12}}}
    mock_agent_check.get.side_effect = [overall_stats, ['db1'], HTTPStatusError('404 Client Error')]

    couchdb_check = CouchDB1(mock_agent_check)

    couchdb_check.check()

    mock_agent_check.gauge.assert_called_once_with(
        'couchdb.httpd.requests', 12, tags=['instance:http://localhost:5984']
    )
