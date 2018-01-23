# (C) Datadog, Inc. 2012-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# stdlib
from collections import defaultdict
import copy
import os

# 3p
import mock
from nose.plugins.attrib import attr
from unittest.case import SkipTest

# project
from checks import AgentCheck
from tests.checks.common import AgentCheckTest
from utils.hostname import get_hostname
from utils.platform import Platform

MOCK_DATA = """# pxname,svname,qcur,qmax,scur,smax,slim,stot,bin,bout,dreq,dresp,ereq,econ,eresp,wretr,wredis,status,weight,act,bck,chkfail,chkdown,lastchg,downtime,qlimit,pid,iid,sid,throttle,lbtot,tracked,type,rate,rate_lim,rate_max,check_status,check_code,check_duration,hrsp_1xx,hrsp_2xx,hrsp_3xx,hrsp_4xx,hrsp_5xx,hrsp_other,hanafail,req_rate,req_rate_max,req_tot,cli_abrt,srv_abrt,
a,FRONTEND,,,1,2,12,1,11,11,0,0,0,,,,,OPEN,,,,,,,,,1,1,0,,,,0,1,0,2,,,,0,1,0,0,0,0,,1,1,1,,,
a,BACKEND,0,0,0,0,12,0,11,11,0,0,,0,0,0,0,UP,0,0,0,,0,1221810,0,,1,1,0,,0,,1,0,,0,,,,0,0,0,0,0,0,,,,,0,0,
b,FRONTEND,,,1,2,12,11,11,0,0,0,0,,,,,OPEN,,,,,,,,,1,2,0,,,,0,0,0,1,,,,,,,,,,,0,0,0,,,
b,i-1,0,0,0,1,,1,1,0,,0,,0,0,0,0,UP 1/2,1,1,0,0,1,1,30,,1,3,1,,70,,2,0,,1,1,,0,,,,,,,0,,,,0,0,
b,i-2,0,0,1,1,,1,1,0,,0,,0,0,0,0,UP 1/2,1,1,0,0,0,1,0,,1,3,2,,71,,2,0,,1,1,,0,,,,,,,0,,,,0,0,
b,i-3,0,0,0,1,,1,1,0,,0,,0,0,0,0,UP,1,1,0,0,0,1,0,,1,3,3,,70,,2,0,,1,1,,0,,,,,,,0,,,,0,0,
b,i-4,0,0,0,1,,1,1,0,,0,,0,0,0,0,DOWN,1,1,0,0,0,1,0,,1,3,3,,70,,2,0,,1,1,,0,,,,,,,0,,,,0,0,
b,i-5,0,0,0,1,,1,1,0,,0,,0,0,0,0,MAINT,1,1,0,0,0,1,0,,1,3,3,,70,,2,0,,1,1,,0,,,,,,,0,,,,0,0,
b,BACKEND,0,0,1,2,0,421,1,0,0,0,,0,0,0,0,UP,6,6,0,,0,1,0,,1,3,0,,421,,1,0,,1,,,,,"space, afterspace",,,,,,,,,0,0,
be_edge_http_sre-production_elk-kibana,i-1,0,0,0,1,,1,1,0,,0,,0,0,0,0,UP,1,1,0,0,1,1,30,,1,3,1,,70,,2,0,,1,1,,0,,,,,,,0,,,,0,0,
be_edge_http_sre-production_elk-kibana,i-2,0,0,0,1,,1,1,0,,0,,0,0,0,0,DOWN (agent),1,1,0,0,1,1,30,,1,3,1,,70,,2,0,,1,1,,0,,,,,,,0,,,,0,0,
be_edge_http_sre-production_elk-kibana,i-3,0,0,0,1,,1,1,0,,0,,0,0,0,0,NO CHECK,1,1,0,0,1,1,30,,1,3,1,,70,,2,0,,1,1,,0,,,,,,,0,,,,0,0,
be_edge_http_sre-production_elk-kibana,BACKEND,0,0,1,2,0,421,1,0,0,0,,0,0,0,0,UP,6,6,0,,0,1,0,,1,3,0,,421,,1,0,,1,,,,,,,,,,,,,,0,0,
"""

MOCK_DATA_EVIL = """# pxname,svname,qcur,qmax,scur,smax,slim,stot,bin,bout,dreq,dresp,ereq,econ,eresp,wretr,wredis,status,weight,act,bck,chkfail,chkdown,lastchg,downtime,qlimit,pid,iid,sid,throttle,lbtot,tracked,type,rate,rate_lim,rate_max,check_status,check_code,check_duration,hrsp_1xx,hrsp_2xx,hrsp_3xx,hrsp_4xx,hrsp_5xx,hrsp_other,hanafail,req_rate,req_rate_max,req_tot,cli_abrt,srv_abrt,
a,FRONTEND,,,1,2,12,1,11,11,0,0,0,,,,,OPEN,,,,,,,,,1,1,0,,,,0,1,0,2,,,,0,1,0,0,0,0,,1,1,1,,,
a,BACKEND,0,0,0,0,12,0,11,11,0,0,,0,0,0,0,UP,0,0,0,,0,1221810,0,,1,1,0,,0,,1,0,,0,,,,0,0,0,0,0,0,,,,,0,0,
b,FRONTEND,,,1,2,12,11,11,0,0,0,0,,,,,OPEN,,,,,,,,,1,2,0,,,,0,0,0,1,,,,,,,,,,,0,0,0,,,
b,i-1,0,0,0,1,,1,1,0,,0,,0,0,0,0,UP 1/2,1,1,0,0,1,1,30,,1,3,1,,70,,2,0,,1,1,,0,,,,,,,0,,,,0,0,
b,i-2,0,0,1,1,,1,1,0,,0,,0,0,0,0,UP 1/2,1,1,0,0,0,1,0,,1,3,2,,71,,2,0,,1,1,,0,,,,,,,0,,,,0,0,
b,i-3,0,0,0,1,,1,1,0,,0,,0,0,0,0,UP,1,1,0,0,0,1,0,,1,3,3,,70,,2,0,,1,1,,0,,,,,,,0,,,,0,0,
b,i-4,0,0,0,1,,1,1,0,,0,,0,0,0,0,DOWN,1,1,0,0,0,1,0,,1,3,3,,70,,2,0,,1,1,,0,,,,,,,0,,,,0,0,
b,i-5,0,0,0,1,,1,1,0,,0,,0,0,0,0,MAINT,1,1,0,0,0,1,0,,1,3,3,,70,,2,0,,1,1,,0,,,,,,,0,,,,0,0,
b,BACKEND,0,0,1,2,0,421,1,0,0,0,,0,0,0,0,UP,6,6,0,,0,1,0,,1,3,0,,421,,1,0,,1,,,,,"Now, this is just plain
EVIL",,,,,,,,,0,0,
be_edge_http_sre-production_elk-kibana,i-1,0,0,0,1,,1,1,0,,0,,0,0,0,0,UP,1,1,0,0,1,1,30,,1,3,1,,70,,2,0,,1,1,,0,,"And this is 'end of days' stuff,
am I right? ""Pure EVIL
DOIN'""
",,,,,0,,,,0,0,
be_edge_http_sre-production_elk-kibana,i-2,0,0,0,1,,1,1,0,,0,,0,0,0,0,DOWN (agent),1,1,0,0,1,1,30,,1,3,1,,70,,2,0,,1,1,,0,,,,,,,0,,,,0,0,
be_edge_http_sre-production_elk-kibana,i-3,0,0,0,1,,1,1,0,,0,,0,0,0,0,NO CHECK,1,1,0,0,1,1,30,,1,3,1,,70,,2,0,,1,1,,0,,,,,,,0,,,,0,0,
be_edge_http_sre-production_elk-kibana,BACKEND,0,0,1,2,0,421,1,0,0,0,,0,0,0,0,UP,6,6,0,,0,1,0,,1,3,0,,421,,1,0,,1,,,,,,,,,,,,,,0,0,
"""

AGG_STATUSES_BY_SERVICE = (
    (['status:available', 'service:a'], 1),
    (['status:available', 'service:b'], 4),
    (['status:unavailable', 'service:b'], 2),
    (['status:available', 'service:be_edge_http_sre-production_elk-kibana'], 1),
    (['status:unavailable', 'service:be_edge_http_sre-production_elk-kibana'], 2)
)

AGG_STATUSES = (
    (['status:available'], 6),
    (['status:unavailable'], 4)
)

@attr(requires='haproxy')
class TestCheckHAProxy(AgentCheckTest):
    CHECK_NAME = 'haproxy'

    BASE_CONFIG = {
        'init_config': None,
        'instances': [
            {
                'url': 'http://localhost/admin?stats',
                'collect_status_metrics': True,
            }
        ]
    }

    def _assert_agg_statuses(self, count_status_by_service=True, collate_status_tags_per_host=False):
        expected_statuses = AGG_STATUSES_BY_SERVICE if count_status_by_service else AGG_STATUSES
        for tags, value in expected_statuses:
            if collate_status_tags_per_host:
                # Assert that no aggregate statuses are sent
                self.assertMetric('haproxy.count_per_status', tags=tags, count=0)
            else:
                self.assertMetric('haproxy.count_per_status', value=value, tags=tags)

    @mock.patch('requests.get', return_value=mock.Mock(content=MOCK_DATA))
    def test_count_per_status_agg_only(self, mock_requests):
        config = copy.deepcopy(self.BASE_CONFIG)
        # with count_status_by_service set to False
        config['instances'][0]['count_status_by_service'] = False
        self.run_check(config)

        self.assertMetric('haproxy.count_per_status', value=2, tags=['status:open'])
        self.assertMetric('haproxy.count_per_status', value=4, tags=['status:up'])
        self.assertMetric('haproxy.count_per_status', value=2, tags=['status:down'])
        self.assertMetric('haproxy.count_per_status', value=1, tags=['status:maint'])
        self.assertMetric('haproxy.count_per_status', value=0, tags=['status:nolb'])
        self.assertMetric('haproxy.count_per_status', value=1, tags=['status:no_check'])

        self._assert_agg_statuses(count_status_by_service=False)

    @mock.patch('requests.get', return_value=mock.Mock(content=MOCK_DATA))
    def test_count_per_status_by_service(self, mock_requests):
        self.run_check(self.BASE_CONFIG)

        self.assertMetric('haproxy.count_per_status', value=1, tags=['status:open', 'service:a'])
        self.assertMetric('haproxy.count_per_status', value=3, tags=['status:up', 'service:b'])
        self.assertMetric('haproxy.count_per_status', value=1, tags=['status:open', 'service:b'])
        self.assertMetric('haproxy.count_per_status', value=1, tags=['status:down', 'service:b'])
        self.assertMetric('haproxy.count_per_status', value=1, tags=['status:maint', 'service:b'])
        self.assertMetric('haproxy.count_per_status', value=1, tags=['status:up', 'service:be_edge_http_sre-production_elk-kibana'])
        self.assertMetric('haproxy.count_per_status', value=1, tags=['status:down', 'service:be_edge_http_sre-production_elk-kibana'])
        self.assertMetric('haproxy.count_per_status', value=1, tags=['status:no_check', 'service:be_edge_http_sre-production_elk-kibana'])

        self._assert_agg_statuses()

    @mock.patch('requests.get', return_value=mock.Mock(content=MOCK_DATA))
    def test_count_per_status_by_service_and_host(self, mock_requests):
        config = copy.deepcopy(self.BASE_CONFIG)
        config['instances'][0]['collect_status_metrics_by_host'] = True
        self.run_check(config)

        self.assertMetric('haproxy.count_per_status', value=1, tags=['backend:FRONTEND', 'status:open', 'service:a'])
        self.assertMetric('haproxy.count_per_status', value=1, tags=['backend:FRONTEND', 'status:open', 'service:b'])
        for backend in ['i-1', 'i-2', 'i-3']:
            self.assertMetric('haproxy.count_per_status', value=1, tags=['backend:%s' % backend, 'status:up', 'service:b'])
        self.assertMetric('haproxy.count_per_status', value=1, tags=['backend:i-4', 'status:down', 'service:b'])
        self.assertMetric('haproxy.count_per_status', value=1, tags=['backend:i-5', 'status:maint', 'service:b'])
        self.assertMetric('haproxy.count_per_status', value=1, tags=['backend:i-1', 'status:up', 'service:be_edge_http_sre-production_elk-kibana'])
        self.assertMetric('haproxy.count_per_status', value=1, tags=['backend:i-2', 'status:down', 'service:be_edge_http_sre-production_elk-kibana'])
        self.assertMetric('haproxy.count_per_status', value=1, tags=['backend:i-3', 'status:no_check', 'service:be_edge_http_sre-production_elk-kibana'])

        self._assert_agg_statuses()

    @mock.patch('requests.get', return_value=mock.Mock(content=MOCK_DATA))
    def test_count_per_status_by_service_and_collate_per_host(self, mock_requests):
        config = copy.deepcopy(self.BASE_CONFIG)
        config['instances'][0]['collect_status_metrics_by_host'] = True
        config['instances'][0]['collate_status_tags_per_host'] = True
        self.run_check(config)

        self.assertMetric('haproxy.count_per_status', value=1, tags=['backend:FRONTEND', 'status:available', 'service:a'])
        self.assertMetric('haproxy.count_per_status', value=1, tags=['backend:FRONTEND', 'status:available', 'service:b'])
        for backend in ['i-1', 'i-2', 'i-3']:
            self.assertMetric('haproxy.count_per_status', value=1, tags=['backend:%s' % backend, 'status:available', 'service:b'])
        self.assertMetric('haproxy.count_per_status', value=1, tags=['backend:i-4', 'status:unavailable', 'service:b'])
        self.assertMetric('haproxy.count_per_status', value=1, tags=['backend:i-5', 'status:unavailable', 'service:b'])
        self.assertMetric('haproxy.count_per_status', value=1, tags=['backend:i-1', 'status:available', 'service:be_edge_http_sre-production_elk-kibana'])
        self.assertMetric('haproxy.count_per_status', value=1, tags=['backend:i-2', 'status:unavailable', 'service:be_edge_http_sre-production_elk-kibana'])
        self.assertMetric('haproxy.count_per_status', value=1, tags=['backend:i-3', 'status:unavailable', 'service:be_edge_http_sre-production_elk-kibana'])

        self._assert_agg_statuses(collate_status_tags_per_host=True)

    @mock.patch('requests.get', return_value=mock.Mock(content=MOCK_DATA_EVIL))
    def test_count_per_status_by_service_and_collate_per_host_evil(self, mock_requests):
        config = copy.deepcopy(self.BASE_CONFIG)
        config['instances'][0]['collect_status_metrics_by_host'] = True
        config['instances'][0]['collate_status_tags_per_host'] = True
        self.run_check(config)

        self.assertMetric('haproxy.count_per_status', value=1, tags=['backend:FRONTEND', 'status:available', 'service:a'])
        self.assertMetric('haproxy.count_per_status', value=1, tags=['backend:FRONTEND', 'status:available', 'service:b'])
        for backend in ['i-1', 'i-2', 'i-3']:
            self.assertMetric('haproxy.count_per_status', value=1, tags=['backend:%s' % backend, 'status:available', 'service:b'])
        self.assertMetric('haproxy.count_per_status', value=1, tags=['backend:i-4', 'status:unavailable', 'service:b'])
        self.assertMetric('haproxy.count_per_status', value=1, tags=['backend:i-5', 'status:unavailable', 'service:b'])
        self.assertMetric('haproxy.count_per_status', value=1, tags=['backend:i-1', 'status:available', 'service:be_edge_http_sre-production_elk-kibana'])
        self.assertMetric('haproxy.count_per_status', value=1, tags=['backend:i-2', 'status:unavailable', 'service:be_edge_http_sre-production_elk-kibana'])
        self.assertMetric('haproxy.count_per_status', value=1, tags=['backend:i-3', 'status:unavailable', 'service:be_edge_http_sre-production_elk-kibana'])

        self._assert_agg_statuses(collate_status_tags_per_host=True)

    @mock.patch('requests.get', return_value=mock.Mock(content=MOCK_DATA))
    def test_count_per_status_collate_per_host(self, mock_requests):
        config = copy.deepcopy(self.BASE_CONFIG)
        config['instances'][0]['collect_status_metrics_by_host'] = True
        config['instances'][0]['collate_status_tags_per_host'] = True
        config['instances'][0]['count_status_by_service'] = False
        self.run_check(config)

        self.assertMetric('haproxy.count_per_status', value=2, tags=['backend:FRONTEND', 'status:available'])
        self.assertMetric('haproxy.count_per_status', value=2, tags=['backend:i-1', 'status:available'])
        self.assertMetric('haproxy.count_per_status', value=1, tags=['backend:i-2', 'status:available'])
        self.assertMetric('haproxy.count_per_status', value=1, tags=['backend:i-2', 'status:unavailable'])
        self.assertMetric('haproxy.count_per_status', value=1, tags=['backend:i-3', 'status:available'])
        self.assertMetric('haproxy.count_per_status', value=1, tags=['backend:i-3', 'status:unavailable'])
        self.assertMetric('haproxy.count_per_status', value=1, tags=['backend:i-4', 'status:unavailable'])
        self.assertMetric('haproxy.count_per_status', value=1, tags=['backend:i-5', 'status:unavailable'])

        self._assert_agg_statuses(count_status_by_service=False, collate_status_tags_per_host=True)

    # This mock is only useful to make the first `run_check` run w/o errors (which in turn is useful only to initialize the check)
    @mock.patch('requests.get', return_value=mock.Mock(content=MOCK_DATA))
    def test_count_hosts_statuses(self, mock_requests):
        self.run_check(self.BASE_CONFIG)

        data = """# pxname,svname,qcur,qmax,scur,smax,slim,stot,bin,bout,dreq,dresp,ereq,econ,eresp,wretr,wredis,status,weight,act,bck,chkfail,chkdown,lastchg,downtime,qlimit,pid,iid,sid,throttle,lbtot,tracked,type,rate,rate_lim,rate_max,check_status,check_code,check_duration,hrsp_1xx,hrsp_2xx,hrsp_3xx,hrsp_4xx,hrsp_5xx,hrsp_other,hanafail,req_rate,req_rate_max,req_tot,cli_abrt,srv_abrt,
a,FRONTEND,,,1,2,12,1,11,11,0,0,0,,,,,OPEN,,,,,,,,,1,1,0,,,,0,1,0,2,,,,0,1,0,0,0,0,,1,1,1,,,
a,BACKEND,0,0,0,0,12,0,11,11,0,0,,0,0,0,0,UP,0,0,0,,0,1221810,0,,1,1,0,,0,,1,0,,0,,,,0,0,0,0,0,0,,,,,0,0,
b,FRONTEND,,,1,2,12,11,11,0,0,0,0,,,,,OPEN,,,,,,,,,1,2,0,,,,0,0,0,1,,,,,,,,,,,0,0,0,,,
b,i-1,0,0,0,1,,1,1,0,,0,,0,0,0,0,UP 1/2,1,1,0,0,1,1,30,,1,3,1,,70,,2,0,,1,1,,0,,,,,,,0,,,,0,0,
b,i-2,0,0,1,1,,1,1,0,,0,,0,0,0,0,UP 1/2,1,1,0,0,0,1,0,,1,3,2,,71,,2,0,,1,1,,0,,,,,,,0,,,,0,0,
b,i-3,0,0,0,1,,1,1,0,,0,,0,0,0,0,UP,1,1,0,0,0,1,0,,1,3,3,,70,,2,0,,1,1,,0,,,,,,,0,,,,0,0,
b,i-4,0,0,0,1,,1,1,0,,0,,0,0,0,0,DOWN,1,1,0,0,0,1,0,,1,3,3,,70,,2,0,,1,1,,0,,,,,,,0,,,,0,0,
b,i-5,0,0,0,1,,1,1,0,,0,,0,0,0,0,MAINT,1,1,0,0,0,1,0,,1,3,3,,70,,2,0,,1,1,,0,,,,,,,0,,,,0,0,
b,BACKEND,0,0,1,2,0,421,1,0,0,0,,0,0,0,0,UP,6,6,0,,0,1,0,,1,3,0,,421,,1,0,,1,,,,,,,,,,,,,,0,0,
""".split('\n')

        # per service
        self.check._process_data(data, True, False, collect_status_metrics=True,
                                 collect_status_metrics_by_host=False)

        expected_hosts_statuses = defaultdict(int)
        expected_hosts_statuses[('b', 'open')] = 1
        expected_hosts_statuses[('b', 'up')] = 3
        expected_hosts_statuses[('b', 'down')] = 1
        expected_hosts_statuses[('b', 'maint')] = 1
        expected_hosts_statuses[('a', 'open')] = 1
        self.assertEquals(self.check.hosts_statuses, expected_hosts_statuses)

        # backend hosts
        agg_statuses = self.check._process_backend_hosts_metric(expected_hosts_statuses)
        expected_agg_statuses = {
            'a': {'available': 0, 'unavailable': 0},
            'b': {'available': 3, 'unavailable': 2},
        }
        self.assertEquals(expected_agg_statuses, dict(agg_statuses))

        # with process_events set to True
        self.check._process_data(data, True, True, collect_status_metrics=True,
                                 collect_status_metrics_by_host=False)
        self.assertEquals(self.check.hosts_statuses, expected_hosts_statuses)

        # per host
        self.check._process_data(data, True, False, collect_status_metrics=True,
                                 collect_status_metrics_by_host=True)
        expected_hosts_statuses = defaultdict(int)
        expected_hosts_statuses[('b', 'FRONTEND', 'open')] = 1
        expected_hosts_statuses[('a', 'FRONTEND', 'open')] = 1
        expected_hosts_statuses[('b', 'i-1', 'up')] = 1
        expected_hosts_statuses[('b', 'i-2', 'up')] = 1
        expected_hosts_statuses[('b', 'i-3', 'up')] = 1
        expected_hosts_statuses[('b', 'i-4', 'down')] = 1
        expected_hosts_statuses[('b', 'i-5', 'maint')] = 1
        self.assertEquals(self.check.hosts_statuses, expected_hosts_statuses)

        self.check._process_data(data, True, True, collect_status_metrics=True,
                                 collect_status_metrics_by_host=True)
        self.assertEquals(self.check.hosts_statuses, expected_hosts_statuses)

    @mock.patch('requests.get', return_value=mock.Mock(content=MOCK_DATA))
    def test_optional_tags(self, mock_requests):
        config = copy.deepcopy(self.BASE_CONFIG)
        config['instances'][0]['tags'] = ['new-tag', 'my:new:tag']

        self.run_check(config)

        self.assertMetricTag('haproxy.backend.session.current', 'new-tag')
        self.assertMetricTag('haproxy.backend.session.current', 'my:new:tag')
        self.assertMetricTag('haproxy.count_per_status', 'my:new:tag')
        self.assertServiceCheck('haproxy.backend_up', tags=['service:a', 'new-tag', 'my:new:tag', 'backend:BACKEND'])

    @mock.patch('requests.get', return_value=mock.Mock(content=MOCK_DATA))
    def test_regex_tags(self, mock_requests):
        config = copy.deepcopy(self.BASE_CONFIG)
        config['instances'][0]['tags'] = ['region:infra']
        # OS3 service: be_edge_http_sre-production_elk-kibana
        config['instances'][0]['tags_regex'] = 'be_(?P<security>edge_http|http)?_(?P<team>[a-z]+)\-(?P<env>[a-z]+)_(' \
                                               '?P<app>.*)'
        self.run_check(config)

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
        self.assertMetric('haproxy.backend.session.current', value=1, count=1, tags=expected_tags)
        self.assertMetricTag('haproxy.backend.session.current', 'app:elk-kibana', 1)
        self.assertServiceCheck('haproxy.backend_up', tags=['service:be_edge_http_sre-production_elk-kibana',
           'region:infra',
           'security:edge_http',
           'app:elk-kibana',
           'env:production',
           'team:sre',
           'backend:i-1'])

@attr(requires='haproxy')
class HaproxyTest(AgentCheckTest):
    CHECK_NAME = 'haproxy'

    BACKEND_SERVICES = ['anotherbackend', 'datadog']

    BACKEND_LIST = ['singleton:8080', 'singleton:8081', 'otherserver']

    FRONTEND_CHECK_GAUGES = [
        'haproxy.frontend.session.current',
        'haproxy.frontend.session.limit',
        'haproxy.frontend.session.pct',
    ]

    FRONTEND_CHECK_GAUGES_POST_1_4 = [
        'haproxy.frontend.requests.rate',
    ]

    BACKEND_CHECK_GAUGES = [
        'haproxy.backend.queue.current',
        'haproxy.backend.session.current',
    ]

    BACKEND_CHECK_GAUGES_POST_1_5 = [
        'haproxy.backend.queue.time',
        'haproxy.backend.connect.time',
        'haproxy.backend.response.time',
        'haproxy.backend.session.time',
    ]

    FRONTEND_CHECK_RATES = [
        'haproxy.frontend.bytes.in_rate',
        'haproxy.frontend.bytes.out_rate',
        'haproxy.frontend.denied.req_rate',
        'haproxy.frontend.denied.resp_rate',
        'haproxy.frontend.errors.req_rate',
        'haproxy.frontend.session.rate',
    ]

    FRONTEND_CHECK_RATES_POST_1_4 = [
        'haproxy.frontend.response.1xx',
        'haproxy.frontend.response.2xx',
        'haproxy.frontend.response.3xx',
        'haproxy.frontend.response.4xx',
        'haproxy.frontend.response.5xx',
        'haproxy.frontend.response.other',
    ]

    BACKEND_CHECK_RATES = [
        'haproxy.backend.bytes.in_rate',
        'haproxy.backend.bytes.out_rate',
        'haproxy.backend.denied.resp_rate',
        'haproxy.backend.errors.con_rate',
        'haproxy.backend.errors.resp_rate',
        'haproxy.backend.session.rate',
        'haproxy.backend.warnings.redis_rate',
        'haproxy.backend.warnings.retr_rate',
    ]

    BACKEND_CHECK_RATES_POST_1_4 = [
        'haproxy.backend.response.1xx',
        'haproxy.backend.response.2xx',
        'haproxy.backend.response.3xx',
        'haproxy.backend.response.4xx',
        'haproxy.backend.response.5xx',
        'haproxy.backend.response.other',
    ]

    def __init__(self, *args, **kwargs):
        AgentCheckTest.__init__(self, *args, **kwargs)
        self.config = {
            "instances": [{
                'url': 'http://localhost:3835/stats',
                'username': 'datadog',
                'password': 'isdevops',
                'status_check': True,
                'collect_aggregates_only': False,
                'tag_service_check_by_host': True,
            }]
        }
        self.config_open = {
            'instances': [{
                'url': 'http://localhost:3836/stats',
                'collect_aggregates_only': False,
            }]
        }
        self.unixsocket_path = os.path.join(os.environ['VOLATILE_DIR'], 'haproxy/datadog-haproxy-stats.sock')
        self.unixsocket_url = 'unix://{0}'.format(self.unixsocket_path)
        self.config_unixsocket = {
            'instances': [{
                'url': self.unixsocket_url,
                'collect_aggregates_only': False,
            }]
        }

    def _test_frontend_metrics(self, shared_tag):
        frontend_tags = shared_tag + ['type:FRONTEND', 'service:public']
        for gauge in self.FRONTEND_CHECK_GAUGES:
            self.assertMetric(gauge, tags=frontend_tags, count=1)

        if os.environ.get('FLAVOR_VERSION','1.5.11').split('.')[:2] >= ['1', '4']:
            for gauge in self.FRONTEND_CHECK_GAUGES_POST_1_4:
                self.assertMetric(gauge, tags=frontend_tags, count=1)

        for rate in self.FRONTEND_CHECK_RATES:
            self.assertMetric(rate, tags=frontend_tags, count=1)

        if os.environ.get('FLAVOR_VERSION','1.5.11').split('.')[:2] >= ['1', '4']:
            for rate in self.FRONTEND_CHECK_RATES_POST_1_4:
                self.assertMetric(rate, tags=frontend_tags, count=1)

    def _test_backend_metrics(self, shared_tag, services=None):
        backend_tags = shared_tag + ['type:BACKEND']
        if not services:
            services = self.BACKEND_SERVICES
        for service in services:
            for backend in self.BACKEND_LIST:
                tags = backend_tags + ['service:' + service, 'backend:' + backend]

                for gauge in self.BACKEND_CHECK_GAUGES:
                    self.assertMetric(gauge, tags=tags, count=1)

                if os.environ.get('FLAVOR_VERSION','1.5.11').split('.')[:2] >= ['1', '5']:
                    for gauge in self.BACKEND_CHECK_GAUGES_POST_1_5:
                        self.assertMetric(gauge, tags=tags, count=1)

                for rate in self.BACKEND_CHECK_RATES:
                    self.assertMetric(rate, tags=tags, count=1)

                if os.environ.get('FLAVOR_VERSION','1.5.11').split('.')[:2] >= ['1', '4']:
                    for rate in self.BACKEND_CHECK_RATES_POST_1_4:
                        self.assertMetric(rate, tags=tags, count=1)

    def _test_service_checks(self, services=None):
        if not services:
            services = self.BACKEND_SERVICES
        for service in services:
            for backend in self.BACKEND_LIST:
                tags = ['service:' + service, 'backend:' + backend]
                self.assertServiceCheck(self.check.SERVICE_CHECK_NAME,
                                        status=AgentCheck.UNKNOWN,
                                        count=1,
                                        tags=tags)
            tags = ['service:' + service, 'backend:BACKEND']
            self.assertServiceCheck(self.check.SERVICE_CHECK_NAME,
                                    status=AgentCheck.OK,
                                    count=1,
                                    tags=tags)

    def test_check(self):
        self.run_check_twice(self.config)

        shared_tag = ['instance_url:http://localhost:3835/stats']

        self._test_frontend_metrics(shared_tag)
        self._test_backend_metrics(shared_tag)

        # check was run 2 times
        #       - FRONTEND is reporting OPEN that we ignore
        #       - only the BACKEND aggregate is reporting UP -> OK
        #       - The 3 individual servers are returning no check -> UNKNOWN
        self._test_service_checks()

        # Make sure the service checks aren't tagged with an empty hostname.
        self.assertEquals(self.service_checks[0]['host_name'], get_hostname(config=self.config))

        self.coverage_report()

    def test_check_service_filter(self):
        config = self.config
        config['instances'][0]['services_include'] = ['datadog']
        config['instances'][0]['services_exclude'] = ['.*']
        self.run_check_twice(config)
        shared_tag = ['instance_url:http://localhost:3835/stats']

        self._test_backend_metrics(shared_tag, ['datadog'])

        self._test_service_checks(['datadog'])

        self.coverage_report()

    def test_wrong_config(self):
        config = self.config
        config['instances'][0]['username'] = 'fake_username'

        self.assertRaises(Exception, lambda: self.run_check(config))

        # Test that nothing has been emitted
        self.coverage_report()

    def test_open_config(self):
        self.run_check_twice(self.config_open)

        shared_tag = ['instance_url:http://localhost:3836/stats']

        self._test_frontend_metrics(shared_tag)
        self._test_backend_metrics(shared_tag)
        self._test_service_checks()

        # This time, make sure the hostname is empty
        self.assertEquals(self.service_checks[0]['host_name'], '')

        self.coverage_report()

    def test_unixsocket_config(self):
        if not Platform.is_linux():
            raise SkipTest("Can run only on Linux because of Docker limitations on unix socket sharing")

        self.run_check_twice(self.config_unixsocket)

        shared_tag = ['instance_url:{0}'.format(self.unixsocket_url)]

        self._test_frontend_metrics(shared_tag)
        self._test_backend_metrics(shared_tag)
        self._test_service_checks()

        self.coverage_report()
