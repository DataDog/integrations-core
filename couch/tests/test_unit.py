# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import base64
import re
from copy import deepcopy
from unittest.mock import MagicMock

import pytest

from datadog_checks.base.utils.http_exceptions import HTTPClientConnectionError, HTTPClientReadTimeoutError
from datadog_checks.couch import CouchDb
from datadog_checks.couch.couch import CouchDB2

from . import common


def register_couch_v1(fake_http_response, server):
    """Serve a CouchDB 1.x server with no databases."""
    fake_http_response(server, json_data={'version': '1.6.1'})
    fake_http_response(f'{server}/_stats/', json_data={})
    fake_http_response(f'{server}/_all_dbs/', json_data=[])


@pytest.mark.parametrize(
    'extra_config, username, password',
    [
        pytest.param({'user': 'legacy_foo', 'password': 'legacy_bar'}, 'legacy_foo', 'legacy_bar', id='legacy'),
        pytest.param({'username': 'new_foo', 'password': 'new_bar'}, 'new_foo', 'new_bar', id='new'),
    ],
)
def test_auth_config(dd_run_check, fake_http, fake_http_response, extra_config, username, password):
    register_couch_v1(fake_http_response, common.URL)
    instance = deepcopy(common.BASIC_CONFIG)
    instance.update(extra_config)
    check = CouchDb(common.CHECK_NAME, {}, instances=[instance])

    dd_run_check(check)

    credentials = base64.b64encode(f'{username}:{password}'.encode()).decode()
    assert [sent.headers.get('Authorization') for sent in fake_http.sent] == [f'Basic {credentials}'] * 3
    fake_http.assert_all_responses_consumed()


def test_timeout_config():
    instance = deepcopy(common.BASIC_CONFIG)
    instance['timeout'] = 17
    check = CouchDb(common.CHECK_NAME, {}, instances=[instance])

    assert check.http.options['timeout'] == (17, 17)


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


def test_couchdb2_collects_every_node_and_shard(aggregator, dd_run_check, fake_http, fake_http_response):
    server = common.URL
    nodes = ['couchdb@node1', 'couchdb@node2']
    indexer_task = {
        'type': 'indexer',
        'database': 'shards/00000000-1fffffff/kennel.1600000000',
        'design_document': '_design/dummy',
        'changes_done': 1,
        'progress': 50,
        'total_changes': 2,
    }
    fake_http_response(server, json_data={'version': '3.1.0'})
    # Both the node discovery and the database sharding read the membership
    fake_http_response(f'{server}/_membership', json_data={'cluster_nodes': nodes})
    fake_http_response(f'{server}/_active_tasks', json_data=[{**indexer_task, 'node': nodes[0]}])
    for index, node in enumerate(nodes):
        node_stats = {'couchdb': {'open_databases': {'value': index + 1, 'type': 'counter'}}}
        fake_http_response(f'{server}/_node/{node}/_stats', json_data=node_stats)
        fake_http_response(f'{server}/_node/{node}/_system', json_data={'run_queue': index})
    fake_http_response(f'{server}/_all_dbs', json_data=['kennel', 'users'])
    for db, doc_count in (('kennel', 3), ('users', 5)):
        db_info = {'sizes': {'file': 10, 'external': 5, 'active': 7}, 'doc_del_count': 0, 'doc_count': doc_count}
        fake_http_response(f'{server}/{db}', json_data=db_info)
    design_docs_query = '_all_docs?startkey="_design/"&endkey="_design0"'
    fake_http_response(f'{server}/kennel/{design_docs_query}', json_data={'rows': [{'id': '_design/dummy'}]})
    fake_http_response(f'{server}/users/{design_docs_query}', json_data={'rows': []})
    view_index = {'language': 'javascript', 'sizes': {'file': 4}, 'updates_pending': {'total': 1}, 'waiting_clients': 0}
    fake_http_response(f'{server}/kennel/_design/dummy/_info', json_data={'name': 'dummy', 'view_index': view_index})
    check = CouchDb(common.CHECK_NAME, {}, instances=[{'server': server}])

    dd_run_check(check)

    for index, node in enumerate(nodes):
        node_tags = [f'instance:{node}']
        aggregator.assert_metric('couchdb.couchdb.open_databases', value=index + 1, tags=node_tags)
        aggregator.assert_metric('couchdb.erlang.run_queue', value=index, tags=node_tags)
        aggregator.assert_metric('couchdb.active_tasks.indexer.count', value=1 - index, tags=node_tags)
        aggregator.assert_service_check(CouchDb.SERVICE_CHECK_NAME, CouchDb.OK, tags=node_tags, count=1)
    task_tags = [f'instance:{nodes[0]}', 'database:kennel', 'design_document:dummy']
    aggregator.assert_metric('couchdb.active_tasks.indexer.progress', value=50, tags=task_tags)
    # Each node scans its own shard of the databases
    aggregator.assert_metric('couchdb.by_db.doc_count', value=3, tags=['db:kennel'], count=1)
    aggregator.assert_metric('couchdb.by_db.doc_count', value=5, tags=['db:users'], count=1)
    ddoc_tags = ['db:kennel', 'design_document:dummy', 'language:javascript']
    aggregator.assert_metric('couchdb.by_ddoc.file_size', value=4, tags=ddoc_tags, count=1)
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
