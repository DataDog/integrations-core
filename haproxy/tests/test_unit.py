import copy
import os
from collections import defaultdict

import mock

from . import common

BASE_CONFIG = {'url': 'http://localhost/admin?stats', 'collect_status_metrics': True, 'enable_service_check': True}


def _assert_agg_statuses(
    aggregator, count_status_by_service=True, collate_status_tags_per_host=False, disable_service_tag=False
):
    if disable_service_tag:
        expected_statuses = common.AGG_STATUSES_BY_SERVICE_DISABLE_SERVICE_TAG
    else:
        expected_statuses = common.AGG_STATUSES_BY_SERVICE if count_status_by_service else common.AGG_STATUSES
    for tags, value in expected_statuses:
        if collate_status_tags_per_host:
            # Assert that no aggregate statuses are sent
            aggregator.assert_metric('haproxy.count_per_status', tags=tags, count=0)
        else:
            aggregator.assert_metric('haproxy.count_per_status', value=value, tags=tags)


def test_count_per_status_agg_only(aggregator, check, haproxy_mock):
    config = copy.deepcopy(BASE_CONFIG)
    # with count_status_by_service set to False
    config['count_status_by_service'] = False

    haproxy_check = check(config)
    haproxy_check.check(config)

    aggregator.assert_metric('haproxy.count_per_status', value=2, tags=['status:open'])
    aggregator.assert_metric('haproxy.count_per_status', value=4, tags=['status:up'])
    aggregator.assert_metric('haproxy.count_per_status', value=2, tags=['status:down'])
    aggregator.assert_metric('haproxy.count_per_status', value=1, tags=['status:maint'])
    aggregator.assert_metric('haproxy.count_per_status', value=0, tags=['status:nolb'])
    aggregator.assert_metric('haproxy.count_per_status', value=1, tags=['status:no_check'])

    _assert_agg_statuses(aggregator, count_status_by_service=False)


def test_count_per_status_by_service(aggregator, check, haproxy_mock):
    config = copy.deepcopy(BASE_CONFIG)
    haproxy_check = check(config)
    haproxy_check.check(config)

    aggregator.assert_metric(
        'haproxy.count_per_status', value=1, tags=['status:open', 'service:a', 'haproxy_service:a']
    )
    aggregator.assert_metric('haproxy.count_per_status', value=3, tags=['status:up', 'service:b', 'haproxy_service:b'])
    aggregator.assert_metric(
        'haproxy.count_per_status', value=1, tags=['status:open', 'service:b', 'haproxy_service:b']
    )
    aggregator.assert_metric(
        'haproxy.count_per_status', value=1, tags=['status:down', 'service:b', 'haproxy_service:b']
    )
    aggregator.assert_metric(
        'haproxy.count_per_status', value=1, tags=['status:maint', 'service:b', 'haproxy_service:b']
    )
    tags = [
        'status:up',
        'service:be_edge_http_sre-production_elk-kibana',
        'haproxy_service:be_edge_http_sre-production_elk-kibana',
    ]
    aggregator.assert_metric('haproxy.count_per_status', value=1, tags=tags)
    tags = [
        'status:down',
        'service:be_edge_http_sre-production_elk-kibana',
        'haproxy_service:be_edge_http_sre-production_elk-kibana',
    ]
    aggregator.assert_metric('haproxy.count_per_status', value=1, tags=tags)
    tags = [
        'status:no_check',
        'service:be_edge_http_sre-production_elk-kibana',
        'haproxy_service:be_edge_http_sre-production_elk-kibana',
    ]
    aggregator.assert_metric('haproxy.count_per_status', value=1, tags=tags)
    _assert_agg_statuses(aggregator)


def test_count_per_status_by_service_and_host(aggregator, check, haproxy_mock):
    config = copy.deepcopy(BASE_CONFIG)
    config['collect_status_metrics_by_host'] = True
    haproxy_check = check(config)
    haproxy_check.check(config)

    tags = ['backend:FRONTEND', 'status:open', 'service:a', 'haproxy_service:a']
    aggregator.assert_metric('haproxy.count_per_status', value=1, tags=tags)
    tags = ['backend:FRONTEND', 'status:open', 'service:b', 'haproxy_service:b']
    aggregator.assert_metric('haproxy.count_per_status', value=1, tags=tags)
    for backend in ['i-1', 'i-2', 'i-3']:
        tags = ['backend:%s' % backend, 'status:up', 'service:b', 'haproxy_service:b']
        aggregator.assert_metric('haproxy.count_per_status', value=1, tags=tags)
    tags = ['backend:i-4', 'status:down', 'service:b', 'haproxy_service:b']
    aggregator.assert_metric('haproxy.count_per_status', value=1, tags=tags)
    tags = ['backend:i-5', 'status:maint', 'service:b', 'haproxy_service:b']
    aggregator.assert_metric('haproxy.count_per_status', value=1, tags=tags)
    tags = [
        'backend:i-1',
        'status:up',
        'service:be_edge_http_sre-production_elk-kibana',
        'haproxy_service:be_edge_http_sre-production_elk-kibana',
    ]
    aggregator.assert_metric('haproxy.count_per_status', value=1, tags=tags)
    tags = [
        'backend:i-2',
        'status:down',
        'service:be_edge_http_sre-production_elk-kibana',
        'haproxy_service:be_edge_http_sre-production_elk-kibana',
    ]
    aggregator.assert_metric('haproxy.count_per_status', value=1, tags=tags)
    tags = [
        'backend:i-3',
        'status:no_check',
        'service:be_edge_http_sre-production_elk-kibana',
        'haproxy_service:be_edge_http_sre-production_elk-kibana',
    ]
    aggregator.assert_metric('haproxy.count_per_status', value=1, tags=tags)

    _assert_agg_statuses(aggregator)


def test_count_per_status_by_service_and_collate_per_host(aggregator, check, haproxy_mock):
    haproxy_check = check(BASE_CONFIG)
    config = copy.deepcopy(BASE_CONFIG)
    config['collect_status_metrics_by_host'] = True
    config['collate_status_tags_per_host'] = True
    haproxy_check.check(config)

    tags = ['backend:FRONTEND', 'status:available', 'service:a', 'haproxy_service:a']
    aggregator.assert_metric('haproxy.count_per_status', value=1, tags=tags)
    tags = ['backend:FRONTEND', 'status:available', 'service:b', 'haproxy_service:b']
    aggregator.assert_metric('haproxy.count_per_status', value=1, tags=tags)
    for backend in ['i-1', 'i-2', 'i-3']:
        tags = ['backend:%s' % backend, 'status:available', 'service:b', 'haproxy_service:b']
        aggregator.assert_metric('haproxy.count_per_status', value=1, tags=tags)
    tags = ['backend:i-4', 'status:unavailable', 'service:b', 'haproxy_service:b']
    aggregator.assert_metric('haproxy.count_per_status', value=1, tags=tags)
    tags = ['backend:i-5', 'status:unavailable', 'service:b', 'haproxy_service:b']
    aggregator.assert_metric('haproxy.count_per_status', value=1, tags=tags)
    tags = [
        'backend:i-1',
        'status:available',
        'service:be_edge_http_sre-production_elk-kibana',
        'haproxy_service:be_edge_http_sre-production_elk-kibana',
    ]
    aggregator.assert_metric('haproxy.count_per_status', value=1, tags=tags)
    tags = [
        'backend:i-2',
        'status:unavailable',
        'service:be_edge_http_sre-production_elk-kibana',
        'haproxy_service:be_edge_http_sre-production_elk-kibana',
    ]
    aggregator.assert_metric('haproxy.count_per_status', value=1, tags=tags)
    tags = [
        'backend:i-3',
        'status:unavailable',
        'service:be_edge_http_sre-production_elk-kibana',
        'haproxy_service:be_edge_http_sre-production_elk-kibana',
    ]
    aggregator.assert_metric('haproxy.count_per_status', value=1, tags=tags)

    _assert_agg_statuses(aggregator, collate_status_tags_per_host=True)


def test_count_per_status_by_service_and_collate_per_host_evil(aggregator, check, haproxy_mock_evil):
    haproxy_check = check(BASE_CONFIG)
    config = copy.deepcopy(BASE_CONFIG)
    config['collect_status_metrics_by_host'] = True
    config['collate_status_tags_per_host'] = True
    haproxy_check.check(config)

    tags = ['backend:FRONTEND', 'status:available', 'service:a', 'haproxy_service:a']
    aggregator.assert_metric('haproxy.count_per_status', value=1, tags=tags)
    tags = ['backend:FRONTEND', 'status:available', 'service:b', 'haproxy_service:b']
    aggregator.assert_metric('haproxy.count_per_status', value=1, tags=tags)
    for backend in ['i-1', 'i-2', 'i-3']:
        tags = ['backend:%s' % backend, 'status:available', 'service:b', 'haproxy_service:b']
        aggregator.assert_metric('haproxy.count_per_status', value=1, tags=tags)
    tags = ['backend:i-4', 'status:unavailable', 'service:b', 'haproxy_service:b']
    aggregator.assert_metric('haproxy.count_per_status', value=1, tags=tags)
    tags = ['backend:i-5', 'status:unavailable', 'service:b', 'haproxy_service:b']
    aggregator.assert_metric('haproxy.count_per_status', value=1, tags=tags)
    tags = [
        'backend:i-1',
        'status:available',
        'service:be_edge_http_sre-production_elk-kibana',
        'haproxy_service:be_edge_http_sre-production_elk-kibana',
    ]
    aggregator.assert_metric('haproxy.count_per_status', value=1, tags=tags)
    tags = [
        'backend:i-2',
        'status:unavailable',
        'service:be_edge_http_sre-production_elk-kibana',
        'haproxy_service:be_edge_http_sre-production_elk-kibana',
    ]
    aggregator.assert_metric('haproxy.count_per_status', value=1, tags=tags)
    tags = [
        'backend:i-3',
        'status:unavailable',
        'service:be_edge_http_sre-production_elk-kibana',
        'haproxy_service:be_edge_http_sre-production_elk-kibana',
    ]
    aggregator.assert_metric('haproxy.count_per_status', value=1, tags=tags)

    _assert_agg_statuses(aggregator, collate_status_tags_per_host=True)


def test_count_per_status_collate_per_host(aggregator, check, haproxy_mock):
    haproxy_check = check(BASE_CONFIG)
    config = copy.deepcopy(BASE_CONFIG)
    config['collect_status_metrics_by_host'] = True
    config['collate_status_tags_per_host'] = True
    config['count_status_by_service'] = False
    haproxy_check.check(config)

    aggregator.assert_metric('haproxy.count_per_status', value=2, tags=['backend:FRONTEND', 'status:available'])
    aggregator.assert_metric('haproxy.count_per_status', value=2, tags=['backend:i-1', 'status:available'])
    aggregator.assert_metric('haproxy.count_per_status', value=1, tags=['backend:i-2', 'status:available'])
    aggregator.assert_metric('haproxy.count_per_status', value=1, tags=['backend:i-2', 'status:unavailable'])
    aggregator.assert_metric('haproxy.count_per_status', value=1, tags=['backend:i-3', 'status:available'])
    aggregator.assert_metric('haproxy.count_per_status', value=1, tags=['backend:i-3', 'status:unavailable'])
    aggregator.assert_metric('haproxy.count_per_status', value=1, tags=['backend:i-4', 'status:unavailable'])
    aggregator.assert_metric('haproxy.count_per_status', value=1, tags=['backend:i-5', 'status:unavailable'])

    _assert_agg_statuses(aggregator, count_status_by_service=False, collate_status_tags_per_host=True)


# This mock is only useful to make the first `run_check` run w/o errors
# (which in turn is useful only to initialize the check)
def test_count_hosts_statuses(aggregator, check, haproxy_mock):
    haproxy_check = check(BASE_CONFIG)
    haproxy_check.check(BASE_CONFIG)

    filepath = os.path.join(common.HERE, 'fixtures', 'statuses_mock')
    with open(filepath, 'r') as f:
        data = f.read()
    data = data.split('\n')

    # per service
    haproxy_check._process_data(data, True, False, collect_status_metrics=True, collect_status_metrics_by_host=False)

    expected_hosts_statuses = defaultdict(int)
    expected_hosts_statuses[('b', 'FRONTEND', 'open')] = 1
    expected_hosts_statuses[('b', 'BACKEND', 'up')] = 3
    expected_hosts_statuses[('b', 'BACKEND', 'down')] = 1
    expected_hosts_statuses[('b', 'BACKEND', 'maint')] = 1
    expected_hosts_statuses[('a', 'FRONTEND', 'open')] = 1
    assert haproxy_check.hosts_statuses == expected_hosts_statuses

    # backend hosts
    agg_statuses = haproxy_check._process_backend_hosts_metric(expected_hosts_statuses)
    expected_agg_statuses = {'b': {'available': 3, 'unavailable': 2}}

    assert expected_agg_statuses == dict(agg_statuses)

    # with process_events set to True
    haproxy_check._process_data(data, True, True, collect_status_metrics=True, collect_status_metrics_by_host=False)
    assert haproxy_check.hosts_statuses == expected_hosts_statuses

    # per host
    haproxy_check._process_data(data, True, False, collect_status_metrics=True, collect_status_metrics_by_host=True)
    expected_hosts_statuses = defaultdict(int)
    expected_hosts_statuses[('b', 'FRONTEND', 'FRONTEND', 'open')] = 1
    expected_hosts_statuses[('a', 'FRONTEND', 'FRONTEND', 'open')] = 1
    expected_hosts_statuses[('b', 'BACKEND', 'i-1', 'up')] = 1
    expected_hosts_statuses[('b', 'BACKEND', 'i-2', 'up')] = 1
    expected_hosts_statuses[('b', 'BACKEND', 'i-3', 'up')] = 1
    expected_hosts_statuses[('b', 'BACKEND', 'i-4', 'down')] = 1
    expected_hosts_statuses[('b', 'BACKEND', 'i-5', 'maint')] = 1
    assert haproxy_check.hosts_statuses == expected_hosts_statuses

    haproxy_check._process_data(data, True, True, collect_status_metrics=True, collect_status_metrics_by_host=True)
    assert haproxy_check.hosts_statuses, expected_hosts_statuses


def test_optional_tags(aggregator, check, haproxy_mock):
    config = copy.deepcopy(BASE_CONFIG)
    config['tags'] = ['new-tag', 'my:new:tag']
    haproxy_check = check(BASE_CONFIG)
    haproxy_check.check(config)

    aggregator.assert_metric_has_tag('haproxy.backend.session.current', 'new-tag')
    aggregator.assert_metric_has_tag('haproxy.backend.session.current', 'my:new:tag')
    aggregator.assert_metric_has_tag('haproxy.count_per_status', 'my:new:tag')
    tags = ['service:a', 'haproxy_service:a', 'new-tag', 'my:new:tag', 'backend:BACKEND']
    aggregator.assert_service_check('haproxy.backend_up', tags=tags)


def test_regex_tags(aggregator, check, haproxy_mock):
    config = copy.deepcopy(BASE_CONFIG)
    config['tags'] = ['region:infra']
    # OS3 service: be_edge_http_sre-production_elk-kibana
    config['tags_regex'] = r'be_(?P<security>edge_http|http)?_(?P<team>[a-z]+)\-(?P<env>[a-z]+)_(?P<app>.*)'
    haproxy_check = check(BASE_CONFIG)
    haproxy_check.check(config)

    expected_tags = [
        'service:be_edge_http_sre-production_elk-kibana',
        'haproxy_service:be_edge_http_sre-production_elk-kibana',
        'type:BACKEND',
        'instance_url:http://localhost/admin?stats',
        'region:infra',
        'security:edge_http',
        'app:elk-kibana',
        'env:production',
        'team:sre',
        'backend:BACKEND',
    ]
    aggregator.assert_metric('haproxy.backend.session.current', value=1, count=1, tags=expected_tags)
    aggregator.assert_metric_has_tag('haproxy.backend.session.current', 'app:elk-kibana', 1)
    tags = [
        'service:be_edge_http_sre-production_elk-kibana',
        'haproxy_service:be_edge_http_sre-production_elk-kibana',
        'region:infra',
        'security:edge_http',
        'app:elk-kibana',
        'env:production',
        'team:sre',
        'backend:i-1',
    ]
    aggregator.assert_service_check('haproxy.backend_up', tags=tags)


def test_version_failure(aggregator, check, datadog_agent):
    config = copy.deepcopy(BASE_CONFIG)
    haproxy_check = check(config)
    filepath = os.path.join(common.HERE, 'fixtures', 'mock_data')
    with open(filepath, 'rb') as f:
        data = f.read()
    with mock.patch('requests.get') as m:
        m.side_effect = [RuntimeError("Ooops"), mock.Mock(content=data)]
        haproxy_check.check(config)

    # Version failed, but we should have some metrics
    aggregator.assert_metric(
        'haproxy.count_per_status', value=1, tags=['status:open', 'service:a', 'haproxy_service:a']
    )
    # But no metadata
    datadog_agent.assert_metadata_count(0)


def test_count_per_status_by_service_disable_service_tag(aggregator, check, haproxy_mock):
    config = copy.deepcopy(BASE_CONFIG)
    config['disable_legacy_service_tag'] = True
    haproxy_check = check(config)
    haproxy_check.check(config)

    aggregator.assert_metric('haproxy.count_per_status', value=1, tags=['status:open', 'haproxy_service:a'])
    aggregator.assert_metric('haproxy.count_per_status', value=3, tags=['status:up', 'haproxy_service:b'])
    aggregator.assert_metric('haproxy.count_per_status', value=1, tags=['status:open', 'haproxy_service:b'])
    aggregator.assert_metric('haproxy.count_per_status', value=1, tags=['status:down', 'haproxy_service:b'])
    aggregator.assert_metric('haproxy.count_per_status', value=1, tags=['status:maint', 'haproxy_service:b'])
    tags = [
        'status:up',
        'haproxy_service:be_edge_http_sre-production_elk-kibana',
    ]
    aggregator.assert_metric('haproxy.count_per_status', value=1, tags=tags)
    tags = [
        'status:down',
        'haproxy_service:be_edge_http_sre-production_elk-kibana',
    ]
    aggregator.assert_metric('haproxy.count_per_status', value=1, tags=tags)
    tags = [
        'status:no_check',
        'haproxy_service:be_edge_http_sre-production_elk-kibana',
    ]
    aggregator.assert_metric('haproxy.count_per_status', value=1, tags=tags)
    _assert_agg_statuses(aggregator, disable_service_tag=True)


def test_enterprise_version_collection(datadog_agent, check, haproxy_mock_enterprise_version_info):
    config = copy.deepcopy(BASE_CONFIG)
    haproxy_check = check(config)
    haproxy_check.check_id = 'test:123'
    haproxy_check._collect_info_from_http("http://the_url_does_not_matter/")
    expected_version_metadata = {
        'version.scheme': 'semver',
        'version.major': '2',
        'version.minor': '1',
        'version.patch': '0',
        'version.raw': '2.1.0-1.0.0-223.130',
        'version.release': '1.0.0',
    }
    datadog_agent.assert_metadata('test:123', expected_version_metadata)
