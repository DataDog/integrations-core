import pytest
import os
import subprocess
import requests
import time
import logging
import copy

from datadog_checks.haproxy import HAProxy

import common

BASE_CONFIG = {
    'url': 'http://localhost/admin?stats',
    'collect_status_metrics': True,
}


def _assert_agg_statuses(aggregator, count_status_by_service=True, collate_status_tags_per_host=False):
    expected_statuses = common.AGG_STATUSES_BY_SERVICE if count_status_by_service else common.AGG_STATUSES
    for tags, value in expected_statuses:
        if collate_status_tags_per_host:
            # Assert that no aggregate statuses are sent
            aggregator.assert_metric('haproxy.count_per_status', tags=tags, count=0)
        else:
            aggregator.assert_metric('haproxy.count_per_status', value=value, tags=tags)


def test_count_per_status_agg_only(aggregator, haproxy_mock):
    config = copy.deepcopy(BASE_CONFIG)
    # with count_status_by_service set to False
    config['count_status_by_service'] = False

    haproxy_check = HAProxy(common.CHECK_NAME, {}, {})
    haproxy_check.check(config)

    aggregator.assert_metric('haproxy.count_per_status', value=2, tags=['status:open'])
    aggregator.assert_metric('haproxy.count_per_status', value=4, tags=['status:up'])
    aggregator.assert_metric('haproxy.count_per_status', value=2, tags=['status:down'])
    aggregator.assert_metric('haproxy.count_per_status', value=1, tags=['status:maint'])
    aggregator.assert_metric('haproxy.count_per_status', value=0, tags=['status:nolb'])
    aggregator.assert_metric('haproxy.count_per_status', value=1, tags=['status:no_check'])

    _assert_agg_statuses(aggregator, count_status_by_service=False)


def test_count_per_status_by_service(aggregator, haproxy_mock):
    config = copy.deepcopy(BASE_CONFIG)
    haproxy_check = HAProxy(common.CHECK_NAME, {}, {})
    haproxy_check.check(config)

    aggregator.assert_metric('haproxy.count_per_status',
                                value=1,
                                tags=['status:open',
                                      'service:a'])
    aggregator.assert_metric('haproxy.count_per_status',
                                value=3,
                                tags=['status:up',
                                      'service:b'])
    aggregator.assert_metric('haproxy.count_per_status',
                                value=1,
                                tags=['status:open',
                                      'service:b'])
    aggregator.assert_metric('haproxy.count_per_status',
                                value=1,
                                tags=['status:down',
                                      'service:b'])
    aggregator.assert_metric('haproxy.count_per_status',
                                value=1,
                                tags=[
                                        'status:maint',
                                        'service:b'])
    aggregator.assert_metric('haproxy.count_per_status',
                                value=1,
                                tags=['status:up',
                                      'service:be_edge_http_sre-production_elk-kibana'])
    aggregator.assert_metric('haproxy.count_per_status',
                                value=1,
                                tags=['status:down',
                                      'service:be_edge_http_sre-production_elk-kibana'])
    aggregator.assert_metric('haproxy.count_per_status',
                                value=1,
                                tags=['status:no_check',
                                      'service:be_edge_http_sre-production_elk-kibana'])
    _assert_agg_statuses(aggregator)


def test_count_per_status_by_service_and_host(aggregator, haproxy_mock):
    haproxy_check = HAProxy(common.CHECK_NAME, {}, {})
    config = copy.deepcopy(BASE_CONFIG)
    config['collect_status_metrics_by_host'] = True
    haproxy_check.check(config)

    aggregator.assert_metric('haproxy.count_per_status', value=1, tags=['backend:FRONTEND', 'status:open', 'service:a'])
    aggregator.assert_metric('haproxy.count_per_status', value=1, tags=['backend:FRONTEND', 'status:open', 'service:b'])
    for backend in ['i-1', 'i-2', 'i-3']:
        aggregator.assert_metric('haproxy.count_per_status', value=1, tags=['backend:%s' % backend, 'status:up', 'service:b'])
    aggregator.assert_metric('haproxy.count_per_status', value=1, tags=['backend:i-4', 'status:down', 'service:b'])
    aggregator.assert_metric('haproxy.count_per_status', value=1, tags=['backend:i-5', 'status:maint', 'service:b'])
    aggregator.assert_metric('haproxy.count_per_status', value=1, tags=['backend:i-1', 'status:up', 'service:be_edge_http_sre-production_elk-kibana'])
    aggregator.assert_metric('haproxy.count_per_status', value=1, tags=['backend:i-2', 'status:down', 'service:be_edge_http_sre-production_elk-kibana'])
    aggregator.assert_metric('haproxy.count_per_status', value=1, tags=['backend:i-3', 'status:no_check', 'service:be_edge_http_sre-production_elk-kibana'])

    _assert_agg_statuses(aggregator)


def test_count_per_status_by_service_and_collate_per_host(aggregator, haproxy_mock):
    haproxy_check = HAProxy(common.CHECK_NAME, {}, {})
    config = copy.deepcopy(BASE_CONFIG)
    config['collect_status_metrics_by_host'] = True
    config['collate_status_tags_per_host'] = True
    haproxy_check.check(config)

    aggregator.assert_metric('haproxy.count_per_status', value=1, tags=['backend:FRONTEND', 'status:available', 'service:a'])
    aggregator.assert_metric('haproxy.count_per_status', value=1, tags=['backend:FRONTEND', 'status:available', 'service:b'])
    for backend in ['i-1', 'i-2', 'i-3']:
        aggregator.assert_metric('haproxy.count_per_status', value=1, tags=['backend:%s' % backend, 'status:available', 'service:b'])
    aggregator.assert_metric('haproxy.count_per_status', value=1, tags=['backend:i-4', 'status:unavailable', 'service:b'])
    aggregator.assert_metric('haproxy.count_per_status', value=1, tags=['backend:i-5', 'status:unavailable', 'service:b'])
    aggregator.assert_metric('haproxy.count_per_status', value=1, tags=['backend:i-1', 'status:available', 'service:be_edge_http_sre-production_elk-kibana'])
    aggregator.assert_metric('haproxy.count_per_status', value=1, tags=['backend:i-2', 'status:unavailable', 'service:be_edge_http_sre-production_elk-kibana'])
    aggregator.assert_metric('haproxy.count_per_status', value=1, tags=['backend:i-3', 'status:unavailable', 'service:be_edge_http_sre-production_elk-kibana'])

    _assert_agg_statuses(aggregator, collate_status_tags_per_host=True)


# def test_count_per_status_by_service_and_collate_per_host_evil(aggregator, haproxy_mock_evil):
#     haproxy_check = HAProxy(common.CHECK_NAME, {}, {})
#     config = copy.deepcopy(BASE_CONFIG)
#     config['collect_status_metrics_by_host'] = True
#     config['collate_status_tags_per_host'] = True
#     haproxy_check.check(config)
#
#     aggregator.assert_metric('haproxy.count_per_status', value=1, tags=['backend:FRONTEND', 'status:available', 'service:a'])
#     aggregator.assert_metric('haproxy.count_per_status', value=1, tags=['backend:FRONTEND', 'status:available', 'service:b'])
#     for backend in ['i-1', 'i-2', 'i-3']:
#         aggregator.assert_metric('haproxy.count_per_status', value=1, tags=['backend:%s' % backend, 'status:available', 'service:b'])
#     aggregator.assert_metric('haproxy.count_per_status', value=1, tags=['backend:i-4', 'status:unavailable', 'service:b'])
#     aggregator.assert_metric('haproxy.count_per_status', value=1, tags=['backend:i-5', 'status:unavailable', 'service:b'])
#     aggregator.assert_metric('haproxy.count_per_status', value=1, tags=['backend:i-1', 'status:available', 'service:be_edge_http_sre-production_elk-kibana'])
#     aggregator.assert_metric('haproxy.count_per_status', value=1, tags=['backend:i-2', 'status:unavailable', 'service:be_edge_http_sre-production_elk-kibana'])
#     aggregator.assert_metric('haproxy.count_per_status', value=1, tags=['backend:i-3', 'status:unavailable', 'service:be_edge_http_sre-production_elk-kibana'])
#
#     _assert_agg_statuses(aggregator, collate_status_tags_per_host=True)
#

def test_count_per_status_collate_per_host(aggregator, haproxy_mock):
    haproxy_check = HAProxy(common.CHECK_NAME, {}, {})
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


# # # This mock is only useful to make the first `run_check` run w/o errors (which in turn is useful only to initialize the check)
# def test_count_hosts_statuses(self, mock_requests):
#     self.run_check(self.BASE_CONFIG)
#
#     data = """# pxname,svname,qcur,qmax,scur,smax,slim,stot,bin,bout,dreq,dresp,ereq,econ,eresp,wretr,wredis,status,weight,act,bck,chkfail,chkdown,lastchg,downtime,qlimit,pid,iid,sid,throttle,lbtot,tracked,type,rate,rate_lim,rate_max,check_status,check_code,check_duration,hrsp_1xx,hrsp_2xx,hrsp_3xx,hrsp_4xx,hrsp_5xx,hrsp_other,hanafail,req_rate,req_rate_max,req_tot,cli_abrt,srv_abrt,
# a,FRONTEND,,,1,2,12,1,11,11,0,0,0,,,,,OPEN,,,,,,,,,1,1,0,,,,0,1,0,2,,,,0,1,0,0,0,0,,1,1,1,,,
# a,BACKEND,0,0,0,0,12,0,11,11,0,0,,0,0,0,0,UP,0,0,0,,0,1221810,0,,1,1,0,,0,,1,0,,0,,,,0,0,0,0,0,0,,,,,0,0,
# b,FRONTEND,,,1,2,12,11,11,0,0,0,0,,,,,OPEN,,,,,,,,,1,2,0,,,,0,0,0,1,,,,,,,,,,,0,0,0,,,
# b,i-1,0,0,0,1,,1,1,0,,0,,0,0,0,0,UP 1/2,1,1,0,0,1,1,30,,1,3,1,,70,,2,0,,1,1,,0,,,,,,,0,,,,0,0,
# b,i-2,0,0,1,1,,1,1,0,,0,,0,0,0,0,UP 1/2,1,1,0,0,0,1,0,,1,3,2,,71,,2,0,,1,1,,0,,,,,,,0,,,,0,0,
# b,i-3,0,0,0,1,,1,1,0,,0,,0,0,0,0,UP,1,1,0,0,0,1,0,,1,3,3,,70,,2,0,,1,1,,0,,,,,,,0,,,,0,0,
# b,i-4,0,0,0,1,,1,1,0,,0,,0,0,0,0,DOWN,1,1,0,0,0,1,0,,1,3,3,,70,,2,0,,1,1,,0,,,,,,,0,,,,0,0,
# b,i-5,0,0,0,1,,1,1,0,,0,,0,0,0,0,MAINT,1,1,0,0,0,1,0,,1,3,3,,70,,2,0,,1,1,,0,,,,,,,0,,,,0,0,
# b,BACKEND,0,0,1,2,0,421,1,0,0,0,,0,0,0,0,UP,6,6,0,,0,1,0,,1,3,0,,421,,1,0,,1,,,,,,,,,,,,,,0,0,
# """.split('\n')
#
#     # per service
#     self.check._process_data(data, True, False, collect_status_metrics=True,
#                              collect_status_metrics_by_host=False)
#
#     expected_hosts_statuses = defaultdict(int)
#     expected_hosts_statuses[('b', 'open')] = 1
#     expected_hosts_statuses[('b', 'up')] = 3
#     expected_hosts_statuses[('b', 'down')] = 1
#     expected_hosts_statuses[('b', 'maint')] = 1
#     expected_hosts_statuses[('a', 'open')] = 1
#     self.assertEquals(self.check.hosts_statuses, expected_hosts_statuses)
#
#     # backend hosts
#     agg_statuses = self.check._process_backend_hosts_metric(expected_hosts_statuses)
#     expected_agg_statuses = {
#         'a': {'available': 0, 'unavailable': 0},
#         'b': {'available': 3, 'unavailable': 2},
#     }
#     self.assertEquals(expected_agg_statuses, dict(agg_statuses))
#
#     # with process_events set to True
#     self.check._process_data(data, True, True, collect_status_metrics=True,
#                              collect_status_metrics_by_host=False)
#     self.assertEquals(self.check.hosts_statuses, expected_hosts_statuses)
#
#     # per host
#     self.check._process_data(data, True, False, collect_status_metrics=True,
#                              collect_status_metrics_by_host=True)
#     expected_hosts_statuses = defaultdict(int)
#     expected_hosts_statuses[('b', 'FRONTEND', 'open')] = 1
#     expected_hosts_statuses[('a', 'FRONTEND', 'open')] = 1
#     expected_hosts_statuses[('b', 'i-1', 'up')] = 1
#     expected_hosts_statuses[('b', 'i-2', 'up')] = 1
#     expected_hosts_statuses[('b', 'i-3', 'up')] = 1
#     expected_hosts_statuses[('b', 'i-4', 'down')] = 1
#     expected_hosts_statuses[('b', 'i-5', 'maint')] = 1
#     self.assertEquals(self.check.hosts_statuses, expected_hosts_statuses)
#
#     self.check._process_data(data, True, True, collect_status_metrics=True,
#                              collect_status_metrics_by_host=True)
#     self.assertEquals(self.check.hosts_statuses, expected_hosts_statuses)


def test_optional_tags(aggregator, haproxy_mock):
    config = copy.deepcopy(BASE_CONFIG)
    config['tags'] = ['new-tag', 'my:new:tag']
    haproxy_check = HAProxy(common.CHECK_NAME, {}, {})
    haproxy_check.check(config)

    # aggregator.assert_metricTag('haproxy.backend.session.current', 'new-tag')
    # aggregator.assert_metricTag('haproxy.backend.session.current', 'my:new:tag')
    # aggregator.assert_metricTag('haproxy.count_per_status', 'my:new:tag')
    aggregator.assert_service_check('haproxy.backend_up', tags=['service:a', 'new-tag', 'my:new:tag', 'backend:BACKEND'])


def test_regex_tags(aggregator, haproxy_mock):
    config = copy.deepcopy(BASE_CONFIG)
    config['tags'] = ['region:infra']
    # OS3 service: be_edge_http_sre-production_elk-kibana
    config['tags_regex'] = 'be_(?P<security>edge_http|http)?_(?P<team>[a-z]+)\-(?P<env>[a-z]+)_(' \
                                           '?P<app>.*)'
    haproxy_check = HAProxy(common.CHECK_NAME, {}, {})
    haproxy_check.check(config)

    expected_tags = ['service:be_edge_http_sre-production_elk-kibana',
                     'type:BACKEND',
                     'instance_url:http://localhost/admin?stats',
                     'region:infra',
                     'security:edge_http',
                     'app:elk-kibana',
                     'env:production',
                     'team:sre',
                     'backend:BACKEND'
                     ]
    aggregator.assert_metric('haproxy.backend.session.current', value=1, count=1, tags=expected_tags)
    # aggregator.assert_metricTag('haproxy.backend.session.current', 'app:elk-kibana', 1)
    aggregator.assert_service_check('haproxy.backend_up', tags=['service:be_edge_http_sre-production_elk-kibana',
       'region:infra',
       'security:edge_http',
       'app:elk-kibana',
       'env:production',
       'team:sre',
       'backend:i-1'])
