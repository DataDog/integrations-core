# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import re
from copy import deepcopy
from unittest.mock import MagicMock

import pytest

from datadog_checks.base.utils.http_exceptions import HTTPClientConnectionError, HTTPClientReadTimeoutError
from datadog_checks.couch import CouchDb
from datadog_checks.couch.couch import CouchDB2

from . import common


@pytest.mark.parametrize(
    'test_case, extra_config, expected_options',
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
def test_config(test_case, extra_config, expected_options):
    instance = deepcopy(common.BASIC_CONFIG)
    instance.update(extra_config)
    check = CouchDb(common.CHECK_NAME, {}, instances=[instance])

    # Without the fake_http fixture, this is the client the check sends every request with
    for name, value in expected_options.items():
        assert check.http.options[name] == value


def test_unreadable_database_is_excluded(aggregator, dd_run_check, fake_http, fake_http_response):
    server = common.URL
    fake_http_response(server, json_data={'version': '1.6.1'})
    fake_http_response(f'{server}/_stats/', json_data={'couchdb': {'open_databases': {'current': 2}}})
    fake_http_response(f'{server}/_all_dbs/', json_data=['kennel', 'secret'])
    fake_http_response(f'{server}/kennel', json_data={'doc_count': 3, 'disk_size': 1024})
    fake_http_response(f'{server}/secret', status_code=403)
    check = CouchDb(common.CHECK_NAME, {}, instances=[{'server': server}])

    dd_run_check(check)

    db_tags = [f'instance:{server}', 'db:kennel', 'device:kennel']
    aggregator.assert_metric('couchdb.by_db.doc_count', value=3, tags=db_tags)
    aggregator.assert_metric('couchdb.by_db.disk_size', value=1024, tags=db_tags)
    aggregator.assert_metric('couchdb.couchdb.open_databases', value=2, tags=[f'instance:{server}'])
    aggregator.assert_all_metrics_covered()
    assert check.checker.db_exclude[server] == ['secret']
    fake_http.assert_all_responses_consumed()


@pytest.mark.parametrize(
    'outcome, expected_message',
    [
        pytest.param(
            HTTPClientReadTimeoutError('read timed out'), 'Request timeout: {url}, read timed out', id='timeout'
        ),
        pytest.param({'status_code': 500}, '500 Server Error', id='error-status'),
        pytest.param(HTTPClientConnectionError('connection refused'), 'connection refused', id='connection-error'),
    ],
)
def test_server_failure_reports_critical(
    aggregator, dd_run_check, fake_http, fake_http_response, outcome, expected_message
):
    server = common.URL
    if isinstance(outcome, Exception):
        fake_http.register_response('GET', server, outcome)
    else:
        fake_http_response(server, **outcome)
    check = CouchDb(common.CHECK_NAME, {}, instances=[{'server': server}])

    with pytest.raises(Exception, match='Unable to talk to the server'):
        dd_run_check(check)

    aggregator.assert_service_check(
        CouchDb.SERVICE_CHECK_NAME,
        CouchDb.CRITICAL,
        tags=[f'instance:{server}'],
        message=re.escape(expected_message.format(url=server)),
        count=1,
    )
    fake_http.assert_all_responses_consumed()


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
