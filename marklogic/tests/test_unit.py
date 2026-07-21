# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging
import re
from typing import Any, Dict  # noqa: F401

import mock
import pytest
from requests.exceptions import ConnectionError, HTTPError

from datadog_checks.base import AgentCheck, ConfigurationError
from datadog_checks.marklogic import MarklogicCheck
from datadog_checks.marklogic.api import MarkLogicApi
from datadog_checks.marklogic.config import Config, ResourceFilter
from datadog_checks.marklogic.constants import RESOURCE_METRICS_AVAILABLE
from datadog_checks.marklogic.parsers.common import MarkLogicParserException, build_metric_to_submit, is_metric
from datadog_checks.marklogic.parsers.health import parse_summary_health
from datadog_checks.marklogic.parsers.request import _parse_request_metrics
from datadog_checks.marklogic.parsers.resources import parse_resources
from datadog_checks.marklogic.parsers.status import _parse_status_metrics, parse_summary_status_base_metrics
from datadog_checks.marklogic.parsers.storage import parse_per_resource_storage_metrics, parse_summary_storage_base_metrics
from datadog_checks.marklogic.utils import is_resource_included

from .common import API_URL

pytestmark = pytest.mark.unit


class MockResponseWrapper:
    def __init__(self, return_value):
        # type: (Dict[str, Any]) -> None
        self.ret = return_value

    def raise_for_status(self):
        # type: () -> None
        pass

    def json(self):
        # type: () -> Dict[str, Any]
        return self.ret


class MockRequestsWrapper:
    def __init__(self, return_value):
        # type: (Dict[str, Any]) -> None
        self.ret = MockResponseWrapper(return_value)

    def get(self, url, params):
        # type: (str, Dict[str, str]) -> MockResponseWrapper
        self.url = url
        self.params = params
        return self.ret


STORAGE_DATA = {
    'forest-storage-list': {
        'relations': {
            'relation-group': [
                {'typeref': 'hosts', 'relation': [{'idref': 'host1', 'nameref': 'HostOne'}]},
                {'typeref': 'forests', 'relation': [{'idref': 'ignored', 'nameref': 'ignored'}]},
            ]
        },
        'storage-list-items': {
            'storage-host': [
                {
                    'relation-id': 'host1',
                    'locations': {
                        'location': [
                            {
                                'path': '/var/data',
                                'capacity': {'units': '%', 'value': 42.0},
                                'location-forests': {
                                    'location-forest': [
                                        {'idref': 'f1', 'nameref': 'ForestOne', 'disk-size': 5},
                                        {'idref': 'f2', 'nameref': 'ForestTwo', 'other-field': 1},
                                    ]
                                },
                            }
                        ]
                    },
                }
            ]
        },
    }
}


# --- api.py ---


def test_base_url_strips_trailing_slash():
    # Kills the ComparisonOperatorReplacer mutants at api.py:17 and the slice mutants at api.py:18.
    api_with_slash = MarkLogicApi(MockRequestsWrapper({}), 'http://localhost:8002/')
    api_without_slash = MarkLogicApi(MockRequestsWrapper({}), 'http://localhost:8002')

    assert api_with_slash._base_url == 'http://localhost:8002/manage/v2'
    assert api_without_slash._base_url == 'http://localhost:8002/manage/v2'


def test_http_get_defaults_params_and_always_sets_json_format():
    # Kills the AddNot mutant at api.py:23 and the ReplaceBinaryOperator_Add mutant at api.py:27.
    http = MockRequestsWrapper({'foo': 'bar'})
    api = MarkLogicApi(http, 'http://localhost:8000')

    assert api.http_get('/custom') == {'foo': 'bar'}
    assert http.url == 'http://localhost:8000/manage/v2/custom'
    assert http.params == {'format': 'json'}

    assert api.http_get('/custom', {'view': 'status'}) == {'foo': 'bar'}
    assert http.params == {'view': 'status', 'format': 'json'}


def test_get_status_data_builds_route_only_when_resource_given():
    # Kills the AddNot mutant at api.py:41 and the ReplaceBinaryOperator_Add mutant at api.py:42.
    http = MockRequestsWrapper({'foo': 'bar'})
    api = MarkLogicApi(http, 'http://localhost:8000')

    api.get_status_data()
    assert http.url == 'http://localhost:8000/manage/v2'

    api.get_status_data(resource='servers')
    assert http.url == 'http://localhost:8000/manage/v2/servers'


def test_get_requests_data_only_sets_resource_id_when_name_present():
    # Kills the ReplaceAndWithOr mutant at api.py:58 and the AddNot mutant at api.py:60.
    http = MockRequestsWrapper({'foo': 'bar'})
    api = MarkLogicApi(http, 'http://localhost:8000')

    api.get_requests_data(resource='server')
    assert 'server-id' not in http.params

    api.get_requests_data(resource='server', name='Admin')
    assert http.params['server-id'] == 'Admin'
    assert 'group-id' not in http.params

    api.get_requests_data(resource='server', name='Admin', group='Default')
    assert http.params['group-id'] == 'Default'


def test_get_storage_data_only_sets_resource_id_when_name_present():
    # Kills the ReplaceAndWithOr mutant at api.py:79 and the AddNot mutant at api.py:81.
    http = MockRequestsWrapper({'foo': 'bar'})
    api = MarkLogicApi(http, 'http://localhost:8000')

    api.get_storage_data(resource='database')
    assert 'database-id' not in http.params

    api.get_storage_data(resource='database', name='Documents')
    assert http.params['database-id'] == 'Documents'
    assert 'group-id' not in http.params

    api.get_storage_data(resource='database', name='Documents', group='Default')
    assert http.params['group-id'] == 'Default'


# --- check.py ---


@pytest.mark.parametrize('exception_cls', [HTTPError, ConnectionError])
def test_check_reports_critical_and_reraises_on_connection_errors(exception_cls, aggregator):
    # Kills the ExceptionReplacer mutants at check.py:56 (`except (HTTPError, ConnectionError)`).
    check = MarklogicCheck('marklogic', {}, [{'url': API_URL, 'tags': ['foo:bar']}])
    check.api.get_resources = mock.Mock(side_effect=exception_cls('boom'))

    with pytest.raises(exception_cls):
        check.check({})

    aggregator.assert_service_check('marklogic.can_connect', MarklogicCheck.CRITICAL, tags=['foo:bar'], count=1)


def test_check_invokes_all_collectors_and_toggles_health_service_checks():
    # Kills the ZeroIterationForLoop mutant at check.py:70 and the AddNot mutant at check.py:76.
    check = MarklogicCheck('marklogic', {}, [{'url': API_URL}])
    check.api.get_resources = mock.Mock(return_value={'cluster-query': {'relations': {'relation-group': []}}})
    check.submit_health_service_checks = mock.Mock()
    check.collectors = [mock.Mock() for _ in range(4)]

    check.check({})

    for collector_mock in check.collectors:
        collector_mock.assert_called_once()
        collector_mock.reset_mock()
    check.submit_health_service_checks.assert_not_called()

    check._config.enable_health_service_checks = True
    check.check({})

    for collector_mock in check.collectors:
        collector_mock.assert_called_once()
    check.submit_health_service_checks.assert_called_once()


def test_collect_summary_status_resource_metrics_queries_forest_status(aggregator):
    # Kills the ZeroIterationForLoop mutant at check.py:87 (`for resource_type in ['forest']`).
    check = MarklogicCheck('marklogic', {}, [{'url': API_URL, 'tags': ['foo:bar']}])
    check.api.get_status_data = mock.Mock(
        return_value={'forest-status-list': {'status-list-summary': {'total-forests': 3}}}
    )

    check.collect_summary_status_resource_metrics()

    check.api.get_status_data.assert_called_once_with('forests')
    aggregator.assert_metric('marklogic.forests.total-forests', value=3, tags=['foo:bar'])


def test_get_resources_to_monitor_filters_included_resources():
    # Kills the ZeroIterationForLoop mutant at check.py:127 and the AddNot mutant at check.py:128.
    check = MarklogicCheck(
        'marklogic',
        {},
        [{'url': API_URL, 'resource_filters': [{'resource_type': 'forest', 'pattern': '^Included'}]}],
    )
    included_forest = {'type': 'forest', 'name': 'IncludedForest', 'id': '1', 'uri': '/forests/IncludedForest'}
    excluded_forest = {'type': 'forest', 'name': 'ExcludedForest', 'id': '2', 'uri': '/forests/ExcludedForest'}
    check.resources = [included_forest, excluded_forest]

    filtered = check.get_resources_to_monitor()

    assert filtered['forest'] == [included_forest]


def test_collect_per_resource_metrics_respects_availability_and_tags(aggregator):
    # Kills the ZeroIterationForLoop/ReplaceBinaryOperator_Add/AddNot mutants at check.py:140-159.
    check = MarklogicCheck('marklogic', {}, [{'url': API_URL, 'tags': ['foo:bar']}])
    check.resources_to_monitor = {
        'forest': [{'type': 'forest', 'name': 'Forest1', 'uri': '/forests/Forest1', 'group': 'Grp'}],
        'database': [],
        'host': [{'type': 'host', 'name': 'Host1', 'uri': '/hosts/Host1'}],
        'server': [],
    }
    check.api.http_get = mock.Mock(
        return_value={
            'forest-status': {'status-properties': {'sample-metric': 5}},
            'host-status': {'status-properties': {'sample-metric': 7}},
        }
    )
    check.api.get_storage_data = mock.Mock(return_value=STORAGE_DATA)
    check.api.get_requests_data = mock.Mock(
        return_value={'request-default-list': {'list-summary': {'total-requests': 9}}}
    )

    check.collect_per_resource_metrics()

    forest_tags = ['forest_name:Forest1', 'foo:bar', 'group_name:Grp']
    host_tags = ['marklogic_host_name:Host1', 'foo:bar']

    aggregator.assert_metric('marklogic.forests.sample-metric', value=5, tags=forest_tags)
    aggregator.assert_metric_has_tag('marklogic.forests.storage.host.capacity', 'group_name:Grp')
    aggregator.assert_metric('marklogic.hosts.sample-metric', value=7, tags=host_tags)
    aggregator.assert_metric('marklogic.requests.total-requests', value=9, tags=host_tags)

    # Forest has requests disabled and host has storage disabled (RESOURCE_METRICS_AVAILABLE gating).
    check.api.get_requests_data.assert_called_once_with(resource='host', name='Host1', group=None)
    check.api.get_storage_data.assert_called_once_with(resource='forest', name='Forest1', group='Grp')


def test_collect_per_resource_metrics_logs_and_swallows_exceptions(caplog):
    # Kills the ExceptionReplacer mutants at check.py:149/155/161 (the three per-resource try/except blocks).
    caplog.at_level(logging.WARNING)
    check = MarklogicCheck('marklogic', {}, [{'url': API_URL}])
    check.resources_to_monitor = {
        'forest': [{'type': 'forest', 'name': 'Forest1', 'uri': '/forests/Forest1'}],
        'database': [],
        'host': [{'type': 'host', 'name': 'Host1', 'uri': '/hosts/Host1'}],
        'server': [],
    }
    check.api.http_get = mock.Mock(side_effect=ValueError('status failed'))
    check.api.get_storage_data = mock.Mock(side_effect=ValueError('storage failed'))
    check.api.get_requests_data = mock.Mock(side_effect=ValueError('requests failed'))

    check.collect_per_resource_metrics()

    assert 'Status information unavailable for resource' in caplog.text
    assert 'Storage information unavailable for resource' in caplog.text
    assert 'Requests information unavailable for resource' in caplog.text


def test_submit_metrics_submits_every_tuple(aggregator):
    # Kills the ZeroIterationForLoop mutant at check.py:187.
    check = MarklogicCheck('marklogic', {}, [{'url': API_URL}])

    check.submit_metrics([('gauge', 'custom.metric_one', 1, ['a:b']), ('gauge', 'custom.metric_two', 2, ['a:b'])])

    aggregator.assert_metric('marklogic.custom.metric_one', value=1, tags=['a:b'])
    aggregator.assert_metric('marklogic.custom.metric_two', value=2, tags=['a:b'])


def test_submit_version_metadata_sets_metadata_and_survives_bad_data(datadog_agent):
    # Kills the RemoveDecorator mutant at check.py:190 and the ExceptionReplacer mutant at check.py:202.
    datadog_agent.reset()
    check = MarklogicCheck('marklogic', {}, [{'url': API_URL}])
    check.check_id = 'test:123'

    datadog_agent._config['enable_metadata_collection'] = False
    check.submit_version_metadata({'local-cluster-status': {'version': '11.0-3'}})
    datadog_agent.assert_metadata_count(0)

    datadog_agent._config['enable_metadata_collection'] = True
    check.submit_version_metadata({'local-cluster-status': {'version': '11.0-3'}})
    datadog_agent.assert_metadata('test:123', {'version.raw': '11.0-3'})

    # Missing data must not raise, only be logged as a warning.
    check.submit_version_metadata({})


def test_submit_health_service_checks_reports_message_only_for_non_ok(aggregator, caplog):
    # Kills the mutants at check.py:220 and the ExceptionReplacer mutants at check.py:225/227.
    check = MarklogicCheck('marklogic', {}, [{'url': API_URL, 'tags': ['foo:bar']}])
    check.resources = [
        {'id': '1', 'type': 'database', 'name': 'Healthy', 'uri': '/databases/Healthy'},
        {'id': '2', 'type': 'database', 'name': 'Sick', 'uri': '/databases/Sick'},
    ]
    health_data = {
        'cluster-health-report': [
            {
                'state': 'critical',
                'resource-type': 'database',
                'resource-name': 'Sick',
                'code': 'HEALTH-DATABASE-OFFLINE',
                'message': 'Database is offline.',
            }
        ]
    }

    with mock.patch('datadog_checks.marklogic.api.MarkLogicApi.get_health', return_value=health_data):
        check.submit_health_service_checks()

    aggregator.assert_service_check(
        'marklogic.database.health', MarklogicCheck.OK, tags=['foo:bar', 'database_name:Healthy'], message=None
    )
    aggregator.assert_service_check(
        'marklogic.database.health',
        MarklogicCheck.CRITICAL,
        tags=['foo:bar', 'database_name:Sick'],
        message=re.escape('HEALTH-DATABASE-OFFLINE (critical): Database is offline.'),
    )

    aggregator.reset()
    with mock.patch(
        'datadog_checks.marklogic.api.MarkLogicApi.get_health', return_value={'code': 'HEALTH-CLUSTER-ERROR'}
    ):
        check.submit_health_service_checks()
    assert 'manage-admin' in caplog.text

    caplog.clear()
    with mock.patch('datadog_checks.marklogic.api.MarkLogicApi.get_health', side_effect=Exception('boom')):
        check.submit_health_service_checks()
    assert 'Failed to monitor databases health' in caplog.text


# --- config.py ---


def test_config_requires_non_empty_url():
    # Kills the ComparisonOperatorReplacer mutants at config.py:17 and the ReplaceTrueWithFalse mutant at config.py:20.
    with pytest.raises(ConfigurationError, match="url is a required configuration."):
        Config({})

    conf = Config({'url': API_URL})
    assert conf.url == API_URL
    assert conf.enable_health_service_checks is False


def test_build_resource_filters_validates_and_splits_included_excluded():
    # Kills the AddNot mutants at config.py:30/32 and the boolean mutants at config.py:36.
    with pytest.raises(ConfigurationError, match='A resource filter requires at least a pattern and a resource_type'):
        Config.build_resource_filters([{'pattern': 'abc'}])
    with pytest.raises(ConfigurationError, match='A resource filter requires at least a pattern and a resource_type'):
        Config.build_resource_filters([{'resource_type': 'forest'}])
    with pytest.raises(ConfigurationError, match='Unknown resource_type: datadog'):
        Config.build_resource_filters([{'pattern': 'abc', 'resource_type': 'datadog'}])

    filters = Config.build_resource_filters(
        [
            {'resource_type': 'forest', 'pattern': '^Doc'},
            {'resource_type': 'database', 'pattern': '^Sec', 'include': False},
        ]
    )
    assert len(filters['included']) == 1
    assert filters['included'][0].resource_type == 'forest'
    assert len(filters['excluded']) == 1
    assert filters['excluded'][0].resource_type == 'database'


def test_resource_filter_defaults_to_included():
    # Kills the ReplaceTrueWithFalse mutant at config.py:47 (`is_included=True` default parameter).
    resource_filter = ResourceFilter('forest', re.compile('.*'))
    assert resource_filter.is_included is True


def test_resource_filter_match_requires_type_pattern_and_group():
    # Kills the ReplaceAndWithOr and comparison mutants at config.py:56-58 (`ResourceFilter.match`).
    resource_filter = ResourceFilter('forest', re.compile('^Sec'), group='Default')

    assert resource_filter.match('forest', 'Security', 'Default') is True
    assert resource_filter.match('database', 'Security', 'Default') is False
    assert resource_filter.match('forest', 'Documents', 'Default') is False
    assert resource_filter.match('forest', 'Security', 'Other') is False


# --- constants.py ---


def test_resource_metrics_available_exact_values():
    # Kills the ReplaceTrueWithFalse/ReplaceFalseWithTrue mutants at constants.py:29-32.
    assert RESOURCE_METRICS_AVAILABLE == {
        'forest': {'status': True, 'storage': True, 'requests': False},
        'database': {'status': True, 'storage': False, 'requests': False},
        'host': {'status': True, 'storage': False, 'requests': True},
        'server': {'status': False, 'storage': False, 'requests': True},
    }


# --- parsers/common.py ---


def test_build_metric_to_submit_int_gauge():
    # Kills the AddNot mutant at parsers/common.py:15 (`isinstance(value_data, (int, float))`).
    assert build_metric_to_submit('metric', 5, ['a:b']) == ('gauge', 'metric', 5, ['a:b'])


def test_build_metric_to_submit_requires_both_units_and_value_keys():
    # Kills the ReplaceAndWithOr mutant at parsers/common.py:17 (`'units' in value_data and 'value' in value_data`).
    with pytest.raises(MarkLogicParserException):
        build_metric_to_submit('metric', {'units': 'MB'})
    with pytest.raises(MarkLogicParserException):
        build_metric_to_submit('metric', {'value': 5})

    assert build_metric_to_submit('metric', {'units': 'MB', 'value': 5}) == ('gauge', 'metric', 5, None)


def test_build_metric_to_submit_skips_unknown_units():
    # Kills the AddNot mutant at parsers/common.py:20 (`if units in GAUGE_UNITS`).
    assert build_metric_to_submit('metric', {'units': 'unknown-unit', 'value': 5}) is None


def test_is_metric_requires_both_units_and_value_keys():
    # Kills the ReplaceOrWithAnd and ReplaceAndWithOr mutants at parsers/common.py:31.
    assert is_metric(5) is True
    assert is_metric(5.5) is True
    assert is_metric({'units': 'MB', 'value': 5}) is True
    assert is_metric({'units': 'MB'}) is False
    assert is_metric({'value': 5}) is False
    assert is_metric({}) is False


# --- parsers/health.py ---


def test_parse_summary_health_filters_resource_types_and_merges_messages():
    # Kills the ReplaceOrWithAnd mutant at health.py:22 and the ReplaceBinaryOperator_Add mutant at health.py:33.
    data = {
        'cluster-health-report': [
            {
                'state': 'critical',
                'resource-type': 'forest',
                'resource-name': 'Documents',
                'code': 'HEALTH-FOREST-UNMOUNTED',
                'message': 'Forest unmounted.',
            },
            {
                'state': 'info',
                'resource-type': 'forest',
                'resource-name': 'Documents',
                'code': 'HEALTH-FOREST-OK',
                'message': 'Recovered.',
            },
            {
                'state': 'info',
                'resource-type': 'host',
                'resource-name': 'SomeHost',
                'code': 'HEALTH-HOST-OK',
                'message': 'Ignored resource type.',
            },
        ]
    }

    result = parse_summary_health(data)

    assert result == {
        'database': {},
        'forest': {
            'Documents': {
                'code': AgentCheck.CRITICAL,
                'message': 'HEALTH-FOREST-UNMOUNTED (critical): Forest unmounted. '
                'HEALTH-FOREST-OK (info): Recovered.',
            }
        },
    }


# --- parsers/request.py ---


def test_parse_request_metrics_filters_metrics_and_skips_none_results():
    # Kills the AddNot mutants at request.py:24 and request.py:26.
    data = {
        'request-default-list': {
            'list-summary': {
                'total-requests': 3,
                'not-a-metric': {'foo': 'bar'},
                'unknown-unit-metric': {'units': 'unknown-unit', 'value': 1},
            }
        }
    }

    result = list(_parse_request_metrics(data, ['foo:bar']))

    assert result == [('gauge', 'requests.total-requests', 3, ['foo:bar'])]


# --- parsers/resources.py ---


def test_parse_resources_builds_ids_types_and_uris_per_group():
    # Kills the ZeroIterationForLoop mutants at resources.py:13/15 and the AddNot mutant at resources.py:23.
    data = {
        'cluster-query': {
            'relations': {
                'relation-group': [
                    {
                        'typeref': 'databases',
                        'relation': [
                            {'uriref': '/manage/v2/databases/Documents', 'idref': '111', 'nameref': 'Documents'},
                        ],
                    },
                    {
                        'typeref': 'servers',
                        'relation': [
                            {
                                'uriref': '/manage/v2/servers/Admin?group-id=Default',
                                'idref': '222',
                                'nameref': 'Admin',
                                'qualifiers': {'qualifier': [{'nameref': 'Default'}]},
                            },
                        ],
                    },
                ]
            }
        }
    }

    result = parse_resources(data)

    assert result == [
        {'id': '111', 'type': 'database', 'name': 'Documents', 'uri': '/databases/Documents'},
        {
            'id': '222',
            'type': 'server',
            'name': 'Admin',
            'uri': '/servers/Admin?group-id=Default',
            'group': 'Default',
        },
    ]


def test_parse_resources_break_stops_after_first_matching_qualifier():
    # Kills the ReplaceBreakWithContinue mutant at resources.py:28.
    data = {
        'cluster-query': {
            'relations': {
                'relation-group': [
                    {
                        'typeref': 'servers',
                        'relation': [
                            {
                                'uriref': '/manage/v2/servers/Admin?group-id=Default&group-id=Other',
                                'idref': '222',
                                'nameref': 'Admin',
                                'qualifiers': {
                                    'qualifier': [
                                        {'nameref': 'Default'},
                                        {'nameref': 'Other'},
                                    ]
                                },
                            },
                        ],
                    },
                ]
            }
        }
    }

    result = parse_resources(data)

    assert result[0]['group'] == 'Default'


# --- parsers/status.py ---


def test_parse_summary_status_base_metrics_skips_non_status_keys_and_forest_type():
    # Kills the AddNot mutant at status.py:29 and the boolean mutant at status.py:34.
    data = {
        'local-cluster-status': {
            'status-relations': {
                'hosts-status': {
                    'typeref': 'hosts',
                    'hosts-status-summary': {'total-hosts': 3},
                },
                'forests-status': {
                    'typeref': 'forests',
                    'forests-status-summary': {'total-forests': 10},
                },
                'cluster-timestamp': '2024-01-01T00:00:00Z',
            }
        }
    }

    result = list(parse_summary_status_base_metrics(data, ['foo:bar']))

    assert result == [('gauge', 'hosts.total-hosts', 3, ['foo:bar'])]


def test_parse_status_metrics_handles_rate_load_and_cache_properties():
    # Kills the recursion/boolean mutants at status.py:42-56 (`_parse_status_metrics`).
    metrics = {
        'rate-properties': {
            'total-rate': 5,
            'rate-detail': {'read-rate': 1},
        },
        'load-properties': {
            'total-load': 7,
            'load-detail': {'write-load': 2},
        },
        'cache-properties': {
            'cache-hit-rate': 9,
        },
        'plain-metric': 11,
        'non-metric-field': 'ignored',
    }

    result = list(_parse_status_metrics('forests', metrics, ['foo:bar']))

    assert sorted(result) == sorted(
        [
            ('gauge', 'forests.total-rate', 5, ['foo:bar']),
            ('gauge', 'forests.read-rate', 1, ['foo:bar']),
            ('gauge', 'forests.total-load', 7, ['foo:bar']),
            ('gauge', 'forests.write-load', 2, ['foo:bar']),
            ('gauge', 'forests.cache-hit-rate', 9, ['foo:bar']),
            ('gauge', 'forests.plain-metric', 11, ['foo:bar']),
        ]
    )


# --- parsers/storage.py ---


def test_parse_summary_storage_base_metrics_includes_forest_disk_size():
    # Kills the ReplaceTrueWithFalse mutant at storage.py:11 and the recursion/boolean mutants at storage.py:26-60.
    result = list(parse_summary_storage_base_metrics(STORAGE_DATA, ['foo:bar']))

    assert sorted(result) == sorted(
        [
            (
                'gauge',
                'forests.storage.host.capacity',
                42.0,
                ['foo:bar', 'marklogic_host_id:host1', 'marklogic_host_name:HostOne', 'storage_path:/var/data'],
            ),
            (
                'gauge',
                'forests.storage.disk-size',
                5,
                [
                    'foo:bar',
                    'marklogic_host_id:host1',
                    'marklogic_host_name:HostOne',
                    'storage_path:/var/data',
                    'forest_id:f1',
                    'forest_name:ForestOne',
                ],
            ),
        ]
    )


def test_parse_per_resource_storage_metrics_excludes_forest_disk_size():
    # Kills the ReplaceFalseWithTrue mutant at storage.py:16 (`include_location_forest=False`).
    result = list(parse_per_resource_storage_metrics(STORAGE_DATA, ['foo:bar']))

    assert result == [
        (
            'gauge',
            'forests.storage.host.capacity',
            42.0,
            ['foo:bar', 'marklogic_host_id:host1', 'marklogic_host_name:HostOne', 'storage_path:/var/data'],
        )
    ]


# --- utils.py ---


def test_is_resource_included_exclude_filter_wins_over_include():
    # Kills the ZeroIterationForLoop/AddNot/boolean mutants at utils.py:12-20.
    config = Config(
        {
            'url': API_URL,
            'resource_filters': [
                {'resource_type': 'forest', 'pattern': '^Doc'},
                {'resource_type': 'forest', 'pattern': '^Documents$', 'include': False},
            ],
        }
    )

    included = {'type': 'forest', 'name': 'Documents'}
    other_included = {'type': 'forest', 'name': 'DocsOther'}
    unmatched = {'type': 'database', 'name': 'Security'}

    assert is_resource_included(included, config) is False  # excluded filter takes precedence
    assert is_resource_included(other_included, config) is True
    assert is_resource_included(unmatched, config) is False
