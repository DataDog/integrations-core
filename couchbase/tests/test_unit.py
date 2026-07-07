# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from urllib.parse import urljoin

import mock
import pytest
import requests

from datadog_checks.couchbase import Couchbase
from datadog_checks.dev.http import MockResponse
from datadog_checks.dev.utils import get_metadata_metrics

from .common import MOCKED_COUCHBASE_METRICS, QUERY_STATS
from .conftest import mock_http_responses

pytestmark = pytest.mark.unit


def make_create_metrics_data(tasks=None):
    return {
        'stats': {'storageTotals': {}},
        'buckets': {},
        'nodes': {},
        'query': {},
        'tasks': tasks or {},
    }


def make_pools_default(version, buckets_uri='/pools/default/buckets'):
    return {
        'storageTotals': {},
        'buckets': {'uri': buckets_uri},
        'nodes': [
            {
                'hostname': 'node1',
                'version': version,
                'interestingStats': {},
                'clusterMembership': 'active',
                'status': 'healthy',
            }
        ],
    }


def stub_http(mocker, responses):
    def handler(url, **_params):
        if url not in responses:
            pytest.fail("url `{}` not registered".format(url))
        return responses[url]

    mocker.patch("requests.Session.get", side_effect=handler)


def test_camel_case_to_joined_lower(instance):
    couchbase = Couchbase('couchbase', {}, [instance])

    CAMEL_CASE_TEST_PAIRS = {
        'camelCase': 'camel_case',
        'FirstCapital': 'first_capital',
        'joined_lower': 'joined_lower',
        'joined_Upper1': 'joined_upper1',
        'Joined_upper2': 'joined_upper2',
        'Joined_Upper3': 'joined_upper3',
        '_leading_Underscore': 'leading_underscore',
        'Trailing_Underscore_': 'trailing_underscore',
        'DOubleCAps': 'd_ouble_c_aps',
        '@@@super--$$-Funky__$__$$%': 'super_funky',
    }

    for test_input, expected_output in CAMEL_CASE_TEST_PAIRS.items():
        test_output = couchbase.camel_case_to_joined_lower(test_input)
        assert test_output == expected_output, 'Input was {}, expected output was {}, actual output was {}'.format(
            test_input, expected_output, test_output
        )


def test_extract_seconds_value(instance):
    couchbase = Couchbase('couchbase', {}, [instance])

    extract_seconds_test_pairs = {
        '3.45s': 3.45,
        '12ms': 0.012,
        '700.5us': 0.0007005,
        '733.364\u00c2s': 0.000733364,
        '0': 0,
    }

    for test_input, expected_output in extract_seconds_test_pairs.items():
        test_output = couchbase.extract_seconds_value(test_input)
        assert test_output == expected_output, 'Input was {}, expected output was {}, actual output was {}'.format(
            test_input, expected_output, test_output
        )


def test__get_query_monitoring_data(instance_query):
    """
    `query_monitoring_url` can potentially fail, be sure we don't raise when the
    endpoint is not reachable
    """
    couchbase = Couchbase('couchbase', {}, [instance_query])
    couchbase._get_query_monitoring_data()


@pytest.mark.parametrize(
    'test_case, extra_config, expected_http_kwargs',
    [
        (
            "new auth config",
            {'username': 'new_foo', 'password': 'bar', 'tls_verify': False},
            {'auth': ('new_foo', 'bar'), 'verify': False},
        ),
        ("legacy config", {'user': 'new_foo', 'ssl_verify': False}, {'auth': ('new_foo', 'password'), 'verify': False}),
    ],
)
def test_config(test_case, extra_config, expected_http_kwargs, instance):
    """
    Test that the legacy and new auth configurations are both supported.
    """
    instance.update(extra_config)

    check = Couchbase('couchbase', {}, [instance])

    http_wargs = {
        'auth': mock.ANY,
        'cert': mock.ANY,
        'headers': mock.ANY,
        'proxies': mock.ANY,
        'timeout': mock.ANY,
        'verify': mock.ANY,
        'allow_redirects': mock.ANY,
    }
    http_wargs.update(expected_http_kwargs)
    assert check.http.options == http_wargs


@pytest.mark.parametrize(
    'test_input, expected_tags',
    [
        ('partition', []),
        ('bucket:index_name', ['bucket:bucket', 'scope:default', 'collection:default', 'index_name:index_name']),
        (
            'bucket:collection:index_name',
            ['bucket:bucket', 'scope:default', 'collection:collection', 'index_name:index_name'],
        ),
        (
            'bucket:scope:collection:index_name',
            ['bucket:bucket', 'scope:scope', 'collection:collection', 'index_name:index_name'],
        ),
        (
            'foo:baz:bar:fiz:buz',
            [],
        ),
    ],
)
def test_extract_index_tags(instance, test_input, expected_tags):
    couchbase = Couchbase('couchbase', {}, [instance])
    """
    Test to ensure that tags are extracted properly from keyspaces. Takes into account the different
    forms of the keyspace and extract the tags from them accordingly. Docs:
    https://docs.couchbase.com/server/current/rest-api/rest-index-stats.html#responses-3
    https://docs.couchbase.com/server/current/n1ql/n1ql-language-reference/createprimaryindex.html#keyspace-ref
    """
    test_output = couchbase._extract_index_tags(test_input)
    assert eval(str(test_output)) == expected_tags


def test_unit(dd_run_check, check, instance, mocker, aggregator):
    mocker.patch("requests.Session.get", wraps=mock_http_responses)

    dd_run_check(check(instance))

    for metric in MOCKED_COUCHBASE_METRICS:
        aggregator.assert_metric("couchbase." + metric)

    aggregator.assert_service_check('couchbase.can_connect', Couchbase.OK)
    aggregator.assert_service_check('couchbase.by_node.cluster_membership', Couchbase.OK)
    aggregator.assert_service_check('couchbase.by_node.health', Couchbase.OK)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


def test_unit_query_metrics(dd_run_check, check, instance_query, mocker, aggregator):
    mocker.patch("requests.Session.get", wraps=mock_http_responses)

    dd_run_check(check(instance_query))

    for metric in MOCKED_COUCHBASE_METRICS + QUERY_STATS:
        aggregator.assert_metric("couchbase." + metric)

    aggregator.assert_service_check('couchbase.can_connect', Couchbase.OK)
    aggregator.assert_service_check('couchbase.by_node.cluster_membership', Couchbase.OK)
    aggregator.assert_service_check('couchbase.by_node.health', Couchbase.OK)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


def test_create_metrics_bucket_uses_first_sample(instance, aggregator):
    couchbase = Couchbase('couchbase', {}, [instance])
    data = make_create_metrics_data()
    data['buckets'] = {'cb_bucket': {'ops': [111, 222, 333]}}

    couchbase._create_metrics(data)

    # Kills the core/NumberReplacer mutant at couchbase.py:78 (val[0] -> val[1]/val[-1]).
    aggregator.assert_metric('couchbase.by_bucket.ops', value=111)


def test_create_metrics_rebalance_no_event_on_first_seen_none_status(instance, aggregator):
    couchbase = Couchbase('couchbase', {}, [instance])
    couchbase._previous_status = 'rebalance'
    data = make_create_metrics_data(tasks={})

    couchbase._create_metrics(data)

    # Kills the core/AddNot, ReplaceComparisonOperator_IsNot_Is, and ReplaceAndWithOr mutants at couchbase.py:108.
    assert aggregator.events == []
    assert couchbase._previous_status == 'rebalance'


def test_create_metrics_rebalance_no_event_when_status_unchanged(instance, aggregator):
    couchbase = Couchbase('couchbase', {}, [instance])
    couchbase._previous_status = 'rebalance'
    data = make_create_metrics_data(tasks={'rebalance': ('rebalance', None)})

    couchbase._create_metrics(data)

    # Kills the core/ReplaceComparisonOperator_NotEq_Eq and NotEq_Is mutants at couchbase.py:108.
    assert aggregator.events == []


def test_create_metrics_rebalance_notrunning_suppressed_on_first_run(instance, aggregator):
    couchbase = Couchbase('couchbase', {}, [instance])
    couchbase._previous_status = None
    data = make_create_metrics_data(tasks={'rebalance': ('notRunning', None)})

    couchbase._create_metrics(data)

    # Kills the core/ReplaceComparisonOperator_IsNot_Is mutant at couchbase.py:119 (previous-status-is-not-None guard).
    assert aggregator.events == []


@pytest.mark.parametrize(
    'status, expected_title, expected_type',
    [
        ('error', 'Encountered an error while rebalancing', 'error'),
        ('notRunning', 'Stopped rebalancing', 'info'),
        ('gracefulFailover', 'Failing over gracefully', 'info'),
        ('rebalance', 'Rebalancing', 'info'),
        ('aaaa', None, None),
        ('zzzz', None, None),
    ],
)
def test_create_metrics_rebalance_event_by_status(instance, aggregator, status, expected_title, expected_type):
    couchbase = Couchbase('couchbase', {}, [instance])
    couchbase._previous_status = 'previous'
    data = make_create_metrics_data(tasks={'rebalance': (status, 'boom')})

    couchbase._create_metrics(data)

    # Kills the core/ReplaceComparisonOperator_{Lt,LtE,Gt,GtE,Eq,NotEq,Is,IsNot} and AddNot mutants at
    # couchbase.py:112/119/126/130 (status-branch routing for rebalance events).
    if expected_title is None:
        assert aggregator.events == []
    else:
        assert len(aggregator.events) == 1
        assert expected_title in aggregator.events[0]['msg_title']
        assert aggregator.events[0]['alert_type'] == expected_type


def test_collect_version_no_nodes(instance):
    couchbase = Couchbase('couchbase', {}, [instance])
    data = {'stats': {'nodes': []}}

    couchbase._collect_version(data)

    # Kills the core/AddNot mutant at couchbase.py:202 (nodes-truthy guard), which would raise IndexError otherwise.
    assert couchbase._version is None


def test_collect_version_uses_first_node(instance):
    couchbase = Couchbase('couchbase', {}, [instance])
    data = {'stats': {'nodes': [{'version': '5.5.3-1-2'}, {'version': '9.9.9-3-4'}]}}

    couchbase._collect_version(data)

    # Kills the core/NumberReplacer mutant at couchbase.py:205 (nodes[0] -> nodes[-1]).
    assert couchbase._version == '5.5.3-1+2'


@pytest.mark.parametrize(
    'version, expected',
    [
        ('5.5.3-4039-enterprise', '5.5.3-4039+enterprise'),
        ('5.5.3enterprise', None),
        ('5.5.3-enterprise', None),
        ('5.5.3-4039-enterprise-extra', None),
    ],
)
def test_collect_version_dash_count(instance, version, expected):
    couchbase = Couchbase('couchbase', {}, [instance])
    data = {'stats': {'nodes': [{'version': version}]}}

    couchbase._collect_version(data)

    # Kills the core/ReplaceComparisonOperator_Eq_* and NumberReplacer mutants at couchbase.py:209 (dash-count == 2).
    assert couchbase._version == expected


@pytest.mark.parametrize(
    'version, index_stats_called',
    [
        ('6.13.20-9999-enterprise', False),
        ('7.3.50-1234-enterprise', True),
        ('9.1.0-1234-enterprise', True),
    ],
)
def test_check_gates_index_stats_on_major_version(instance_index_stats, mocker, aggregator, version, index_stats_called):
    couchbase = Couchbase('couchbase', {}, [instance_index_stats])
    server = instance_index_stats['server']
    responses = {
        '{}/pools/default'.format(server): MockResponse(json_data=make_pools_default(version)),
        '{}/pools/default/buckets'.format(server): MockResponse(json_data=[]),
        '{}/pools/default/tasks'.format(server): MockResponse(json_data=[]),
        urljoin(instance_index_stats['index_stats_url'], '/api/v1/stats'): MockResponse(json_data={}),
    }
    stub_http(mocker, responses)

    couchbase.check(None)

    # Kills the core/ReplaceComparisonOperator_GtE_* and NumberReplacer mutants at couchbase.py:194
    # (major-version >= 7 gate for index stats collection).
    if index_stats_called:
        aggregator.assert_service_check('couchbase.index_stats.can_connect', Couchbase.OK)
    else:
        aggregator.assert_service_check('couchbase.index_stats.can_connect', count=0)


def test_check_swallows_error_from_malformed_version(instance_index_stats, mocker):
    couchbase = Couchbase('couchbase', {}, [instance_index_stats])
    server = instance_index_stats['server']
    responses = {
        '{}/pools/default'.format(server): MockResponse(json_data=make_pools_default('vv-1-2')),
        '{}/pools/default/buckets'.format(server): MockResponse(json_data=[]),
        '{}/pools/default/tasks'.format(server): MockResponse(json_data=[]),
    }
    stub_http(mocker, responses)

    # Kills the core/ExceptionReplacer mutant at couchbase.py:196 (broad except around the version-gate int() cast).
    couchbase.check(None)


def test_get_data_normalizes_none_service_check_tags(instance, mocker, aggregator):
    couchbase = Couchbase('couchbase', {}, [instance])
    couchbase._tags = None
    server = instance['server']
    responses = {
        '{}/pools/default'.format(server): MockResponse(json_data=make_pools_default('7.1.3-3479-enterprise')),
        '{}/pools/default/buckets'.format(server): MockResponse(json_data=[]),
        '{}/pools/default/tasks'.format(server): MockResponse(json_data=[]),
    }
    stub_http(mocker, responses)

    couchbase.get_data()

    # Kills the core/AddNot and ReplaceComparisonOperator_Is_IsNot mutants at couchbase.py:226 (tags-is-None check).
    aggregator.assert_service_check('couchbase.can_connect', Couchbase.OK, tags=[])


def test_get_data_raises_http_error_and_sets_critical(instance, mocker, aggregator):
    couchbase = Couchbase('couchbase', {}, [instance])
    server = instance['server']
    stub_http(mocker, {'{}/pools/default'.format(server): MockResponse(status_code=500)})

    # Kills the core/ExceptionReplacer mutant at couchbase.py:235 (HTTPError-specific except clause).
    with pytest.raises(requests.exceptions.HTTPError):
        couchbase.get_data()
    aggregator.assert_service_check('couchbase.can_connect', Couchbase.CRITICAL)


def test_get_data_raises_generic_error_and_sets_critical(instance, mocker, aggregator):
    couchbase = Couchbase('couchbase', {}, [instance])
    server = instance['server']
    stub_http(mocker, {'{}/pools/default'.format(server): MockResponse(content='null')})

    # Kills the core/ExceptionReplacer mutant at couchbase.py:238 (generic Exception except clause).
    with pytest.raises(Exception, match="No data returned"):
        couchbase.get_data()
    aggregator.assert_service_check('couchbase.can_connect', Couchbase.CRITICAL)


def test_get_data_falls_back_to_backup_bucket_url_on_http_error(instance, mocker):
    couchbase = Couchbase('couchbase', {}, [instance])
    server = instance['server']
    pools_default = make_pools_default('7.1.3-3479-enterprise')
    buckets_list = [{'name': 'cb_bucket', 'stats': {'uri': '/pools/default/buckets/cb_bucket/stats'}}]
    backup_url = '{}/pools/nodes/buckets/cb_bucket/stats'.format(server)
    responses = {
        '{}/pools/default'.format(server): MockResponse(json_data=pools_default),
        '{}/pools/default/buckets'.format(server): MockResponse(json_data=buckets_list),
        '{}/pools/default/buckets/cb_bucket/stats'.format(server): MockResponse(status_code=500),
        backup_url: MockResponse(json_data={'op': {'samples': {'ops': [42]}}}),
        '{}/pools/default/tasks'.format(server): MockResponse(json_data=[]),
    }
    stub_http(mocker, responses)

    data = couchbase.get_data()

    # Kills the core/ExceptionReplacer mutant at couchbase.py:269 (HTTPError fallback to the backup bucket-stats URL).
    assert data['buckets']['cb_bucket'] == {'ops': [42]}


def test_get_data_tasks_loop_filters_and_stops_at_first_rebalance(instance, mocker):
    couchbase = Couchbase('couchbase', {}, [instance])
    server = instance['server']
    tasks = [
        {'type': 'aaaa', 'status': 'running'},
        {'type': 'zzzz', 'status': 'running'},
        {'type': 'rebalance', 'status': 'running', 'subtype': 'rebalance'},
        {'type': 'rebalance', 'status': 'notRunning'},
    ]
    responses = {
        '{}/pools/default'.format(server): MockResponse(json_data=make_pools_default('7.1.3-3479-enterprise')),
        '{}/pools/default/buckets'.format(server): MockResponse(json_data=[]),
        '{}/pools/default/tasks'.format(server): MockResponse(json_data=tasks),
    }
    stub_http(mocker, responses)

    data = couchbase.get_data()

    # Kills the core/ZeroIterationForLoop, ReplaceComparisonOperator_NotEq_*, ReplaceContinueWithBreak, and
    # ReplaceBreakWithContinue mutants at couchbase.py:286/290/291/305 (task-type filtering and loop termination).
    assert data['tasks'] == {'rebalance': ('rebalance', None)}


@pytest.mark.parametrize(
    'task, expected_tasks',
    [
        ({'type': 'rebalance', 'errorMessage': 'boom', 'status': 'notRunning'}, {'rebalance': ('error', 'boom')}),
        ({'type': 'rebalance', 'status': 'notRunning'}, {'rebalance': ('notRunning', None)}),
        ({'type': 'rebalance', 'status': 'running', 'subtype': 'gracefulFailover'}, {'rebalance': ('gracefulFailover', None)}),
        ({'type': 'rebalance', 'status': 'aaaa'}, {}),
        ({'type': 'rebalance', 'status': 'zzzz'}, {}),
    ],
)
def test_get_data_task_status_branches(instance, mocker, task, expected_tasks):
    couchbase = Couchbase('couchbase', {}, [instance])
    server = instance['server']
    responses = {
        '{}/pools/default'.format(server): MockResponse(json_data=make_pools_default('7.1.3-3479-enterprise')),
        '{}/pools/default/buckets'.format(server): MockResponse(json_data=[]),
        '{}/pools/default/tasks'.format(server): MockResponse(json_data=[task]),
    }
    stub_http(mocker, responses)

    data = couchbase.get_data()

    # Kills the core/ReplaceComparisonOperator_Eq_* mutants at couchbase.py:296 and :301 (task-status branches).
    assert data['tasks'] == expected_tasks


def test_get_data_tasks_http_error_is_swallowed(instance, mocker):
    couchbase = Couchbase('couchbase', {}, [instance])
    server = instance['server']
    responses = {
        '{}/pools/default'.format(server): MockResponse(json_data=make_pools_default('7.1.3-3479-enterprise')),
        '{}/pools/default/buckets'.format(server): MockResponse(json_data=[]),
        '{}/pools/default/tasks'.format(server): MockResponse(status_code=500),
    }
    stub_http(mocker, responses)

    # Kills the core/ExceptionReplacer mutant at couchbase.py:307 (HTTPError swallowed for the tasks endpoint).
    data = couchbase.get_data()
    assert data['tasks'] == {}


def test_collect_sync_gateway_metrics_request_error(instance_sg, mocker, aggregator):
    couchbase = Couchbase('couchbase', {}, [instance_sg])
    mocker.patch("requests.Session.get", side_effect=requests.exceptions.RequestException("boom"))

    # Kills the core/ExceptionReplacer mutant at couchbase.py:332 and the ReplaceBinaryOperator_Mod_* mutants at
    # couchbase.py:333 (RequestException handling and the resulting error-message formatting).
    couchbase._collect_sync_gateway_metrics()
    aggregator.assert_service_check('couchbase.sync_gateway.can_connect', Couchbase.CRITICAL)


def test_collect_sync_gateway_metrics_global_and_per_db(instance_sg, aggregator, mocker):
    couchbase = Couchbase('couchbase', {}, [instance_sg])
    sg_data = {
        'syncgateway': {
            'global': {'resource_utilization': {'num_goroutines': 5, 'bad_metric': {'unexpected': 'dict'}}},
            'per_db': {
                'db1': {
                    'cache': {'abandoned_seqs': 3},
                    'database': {'cache_feed': {'sub1': 7}},
                },
            },
        }
    }
    mocker.patch("requests.Session.get", return_value=MockResponse(json_data=sg_data))

    # Kills the core/ZeroIterationForLoop mutants at couchbase.py:341/348/350/352 (global/per-db metric iteration)
    # and the core/Exception-handling mutants at couchbase.py:344/355 (bad metric values are logged and skipped).
    couchbase._collect_sync_gateway_metrics()

    aggregator.assert_metric('couchbase.sync_gateway.num_goroutines', value=5)
    aggregator.assert_metric(
        'couchbase.sync_gateway.cache.abandoned_seqs', value=3, tags=['db:db1'] + couchbase._tags
    )
    aggregator.assert_metric(
        'couchbase.sync_gateway.database.cache_feed.sub1',
        value=7,
        tags=['db:db1'] + couchbase._tags,
        metric_type=aggregator.MONOTONIC_COUNT,
    )


def test_submit_gateway_metrics_gsi_views_match(instance, mocker):
    couchbase = Couchbase('couchbase', {}, [instance])
    monotonic_mock = mocker.patch.object(couchbase, 'monotonic_count')

    couchbase._submit_gateway_metrics(
        '{myDesignDoc}-access_query_count:sync_gateway', 9, couchbase._tags, prefix='gsi_views'
    )

    # Kills the core/AddNot mutant at couchbase.py:372 and the NumberReplacer mutants at :373/:375 (regex groups).
    monotonic_mock.assert_called_once_with(
        'couchbase.sync_gateway.gsi_views.myDesignDoc', tags=['design_doc_name:myDesignDoc'] + couchbase._tags
    )


def test_submit_gateway_metrics_gsi_views_no_match_submits_nothing(instance, mocker):
    couchbase = Couchbase('couchbase', {}, [instance])
    gauge_spy = mocker.spy(couchbase, 'gauge')
    monotonic_spy = mocker.spy(couchbase, 'monotonic_count')

    couchbase._submit_gateway_metrics('not_a_matching_metric_name', 9, couchbase._tags, prefix='gsi_views')

    # Kills the core/AddNot mutant at couchbase.py:372 (regex-match guard), which would otherwise crash on
    # match.groups() for a non-matching metric name.
    assert not gauge_spy.called
    assert not monotonic_spy.called


@pytest.mark.parametrize('prefix', ['aaaa', 'zzzz'])
def test_submit_gateway_metrics_falls_back_to_gauge_for_other_prefixes(instance, aggregator, prefix):
    couchbase = Couchbase('couchbase', {}, [instance])

    couchbase._submit_gateway_metrics('custom_metric', 5, couchbase._tags, prefix=prefix)

    # Kills the core/ReplaceComparisonOperator_Eq_{Lt,LtE,Gt,GtE} mutants at couchbase.py:368 (gsi_views prefix check).
    aggregator.assert_metric('couchbase.sync_gateway.{}.custom_metric'.format(prefix), value=5, tags=couchbase._tags)


def test_collect_index_stats_metrics_indexer_and_index_branches(instance_index_stats, mocker, aggregator):
    couchbase = Couchbase('couchbase', {}, [instance_index_stats])
    index_data = {
        'indexer': {'indexer_state': 'Active', 'memory_used': 123},
        'gamesim-sample:default:default:gamesim_primary': {'num_requests': 4, 'items_count': 10},
    }
    mocker.patch("requests.Session.get", return_value=MockResponse(json_data=index_data))

    couchbase._collect_index_stats_metrics()

    # Kills the core/ZeroIterationForLoop mutants at couchbase.py:429/432/436 (keyspace and per-keyspace loops).
    aggregator.assert_metric('couchbase.indexer.memory_used', value=123, tags=couchbase._tags)
    aggregator.assert_metric('couchbase.index.num_requests', value=4, metric_type=aggregator.MONOTONIC_COUNT)
    aggregator.assert_metric('couchbase.index.items_count', value=10, metric_type=aggregator.MONOTONIC_COUNT)


@pytest.mark.parametrize('keyspace', ['aaaa', 'zzzz'])
def test_collect_index_stats_non_indexer_keyspace_uses_index_branch(instance_index_stats, mocker, aggregator, keyspace):
    couchbase = Couchbase('couchbase', {}, [instance_index_stats])
    index_data = {keyspace: {'num_requests': 7}}
    mocker.patch("requests.Session.get", return_value=MockResponse(json_data=index_data))

    couchbase._collect_index_stats_metrics()

    # Kills the core/ReplaceComparisonOperator_{Lt,LtE,Gt,GtE} mutants at couchbase.py:430 (indexer-keyspace check)
    # and the core/ReplaceBinaryOperator_Add_* mutants at couchbase.py:435 (index-tag concatenation).
    aggregator.assert_metric(
        'couchbase.index.num_requests', value=7, tags=couchbase._tags, metric_type=aggregator.MONOTONIC_COUNT
    )


@pytest.mark.parametrize(
    'mname, mval, expected_value',
    [
        ('indexer_state', 'Active', 0),
        ('indexer_state', 'Pause', 1),
        ('indexer_state', 'Warmup', 2),
        ('memory_used', 555, 555),
        ('aaaa', 1, 1),
        ('zzzz', 1, 1),
    ],
)
def test_submit_index_node_metrics(instance, aggregator, mname, mval, expected_value):
    couchbase = Couchbase('couchbase', {}, [instance])

    couchbase._submit_index_node_metrics(mname, mval)

    # Kills the core/ReplaceComparisonOperator_Eq_* and AddNot mutants at couchbase.py:474 (indexer_state check)
    # and the core/NumberReplacer mutants on INDEXER_STATE_MAP in couchbase_consts.py:377.
    aggregator.assert_metric('couchbase.indexer.{}'.format(mname), value=expected_value, tags=couchbase._tags)


@pytest.mark.parametrize(
    'mname, expect_monotonic',
    [
        ('num_requests', True),
        ('items_count', True),
        ('some_gauge_metric', False),
    ],
)
def test_submit_per_index_metrics_routes_by_metric_name(instance, aggregator, mname, expect_monotonic):
    couchbase = Couchbase('couchbase', {}, [instance])

    couchbase._submit_per_index_metrics(mname, 3, couchbase._tags)

    metric_type = aggregator.MONOTONIC_COUNT if expect_monotonic else aggregator.GAUGE
    # Kills the core/AddNot mutant at couchbase.py:482 (count-vs-gauge metric routing).
    aggregator.assert_metric('couchbase.index.{}'.format(mname), value=3, metric_type=metric_type)


def test_extract_seconds_value_nanoseconds(instance):
    couchbase = Couchbase('couchbase', {}, [instance])

    # Kills the core/NumberReplacer mutants at couchbase_consts.py:238 (TO_SECONDS['ns'] = 1e9).
    assert couchbase.extract_seconds_value('5000000000ns') == 5.0
