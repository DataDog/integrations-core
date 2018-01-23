# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# stdlib
import os

# 3p
import simplejson as json

# project
from tests.checks.common import AgentCheckTest, Fixtures
from checks import AgentCheck

class TestCeph(AgentCheckTest):
    """Basic Test for ceph integration."""
    CHECK_NAME = 'ceph'
    FIXTURE_DIR = os.path.join(os.path.dirname(__file__), 'ci')

    def test_simple_metrics(self):
        mocks = {
            '_collect_raw': lambda x,y,z: json.loads(Fixtures.read_file('raw.json', sdk_dir=self.FIXTURE_DIR)),
        }
        config = {
            'instances': [{'host': 'foo'}]
        }

        self.run_check_twice(config, mocks=mocks, force_reload=True)
        expected_tags = ['ceph_fsid:e0efcf84-e8ed-4916-8ce1-9c70242d390a',
                         'ceph_mon_state:peon']
        expected_metrics = ['ceph.num_mons', 'ceph.total_objects', 'ceph.pgstate.active_clean']

        for metric in expected_metrics:
            self.assertMetric(metric, count=1, tags=expected_tags)

        self.assertServiceCheck('ceph.overall_status', status=AgentCheck.OK)

    def test_warn_health(self):
        mocks = {
            '_collect_raw': lambda x,y,z: json.loads(
                Fixtures.read_file('warn.json', sdk_dir=self.FIXTURE_DIR)),
        }
        config = {
            'instances': [{'host': 'foo'}]
        }

        self.run_check_twice(config, mocks=mocks, force_reload=True)
        expected_tags = ['ceph_fsid:e0efcf84-e8ed-4916-8ce1-9c70242d390a',
                         'ceph_mon_state:peon']
        expected_metrics = ['ceph.num_mons', 'ceph.total_objects', 'ceph.pgstate.active_clean']

        for metric in expected_metrics:
            self.assertMetric(metric, count=1, tags=expected_tags)

        self.assertServiceCheck('ceph.overall_status', status=AgentCheck.WARNING)

    def test_luminous_warn_health(self):
        mocks = {
            '_collect_raw': lambda x,y,z: json.loads(
                Fixtures.read_file('ceph_luminous_warn.json', sdk_dir=self.FIXTURE_DIR)),
        }
        config = {
            'instances': [{
                'host': 'foo',
                'collect_service_check_for': ['OSD_NEARFULL', 'OSD_FULL'],
            }]
        }

        self.run_check(config, mocks=mocks, force_reload=True)
        self.assertServiceCheck('ceph.overall_status', status=AgentCheck.CRITICAL)
        self.assertServiceCheck('ceph.osd_nearfull', status=AgentCheck.WARNING)
        self.assertServiceCheck('ceph.osd_full', status=AgentCheck.CRITICAL)

    def test_luminous_ok_health(self):
        mocks = {
            '_collect_raw': lambda x,y,z: json.loads(
                Fixtures.read_file('ceph_luminous_ok.json', sdk_dir=self.FIXTURE_DIR)),
        }
        config = {
            'instances': [{
                'host': 'foo',
                'collect_service_check_for': ['OSD_NEARFULL'],
            }]
        }

        self.run_check(config, mocks=mocks, force_reload=True)
        self.assertServiceCheck('ceph.overall_status', status=AgentCheck.OK)
        self.assertServiceCheck('ceph.osd_nearfull', status=AgentCheck.OK)
        self.assertServiceCheck('ceph.pool_app_not_enabled', count=0)

    def test_luminous_osd_full_metrics(self):
        mocks = {
            '_collect_raw': lambda x,y,z: json.loads(
                Fixtures.read_file('ceph_luminous_warn.json', sdk_dir=self.FIXTURE_DIR)),
        }
        config = {
            'instances': [{'host': 'foo'}]
        }

        self.run_check(config, mocks=mocks, force_reload=True)
        self.assertMetric('ceph.num_full_osds', value=1)
        self.assertMetric('ceph.num_near_full_osds', value=1)

    def test_tagged_metrics(self):
        mocks = {
            '_collect_raw': lambda x,y,z: json.loads(
                Fixtures.read_file('raw.json', sdk_dir=self.FIXTURE_DIR)),
        }
        config = {
            'instances': [{'host': 'foo'}]
        }

        self.run_check_twice(config, mocks=mocks, force_reload=True)
        for osd in ['osd0', 'osd1', 'osd2']:
            expected_tags = ['ceph_fsid:e0efcf84-e8ed-4916-8ce1-9c70242d390a',
                             'ceph_mon_state:peon',
                             'ceph_osd:%s' % osd]

            for metric in ['ceph.commit_latency_ms', 'ceph.apply_latency_ms']:
                self.assertMetric(metric, count=1, tags=expected_tags)

        for pool in ['pool0', 'rbd']:
            expected_tags = ['ceph_fsid:e0efcf84-e8ed-4916-8ce1-9c70242d390a',
                             'ceph_mon_state:peon',
                             'ceph_pool:%s' % pool]
            for metric in ['ceph.read_bytes', 'ceph.write_bytes', 'ceph.pct_used', 'ceph.num_objects']:
                self.assertMetric(metric, count=1, tags=expected_tags)

    def test_osd_status_metrics(self):
        mocks = {
            '_collect_raw': lambda x,y,z: json.loads(
                Fixtures.read_file('ceph_10.2.2.json', sdk_dir=self.FIXTURE_DIR)),
        }
        config = {
            'instances': [{'host': 'foo'}]
        }

        self.run_check_twice(config, mocks=mocks, force_reload=True)

        for osd, pct_used in [('osd1', 94), ('osd2', 95)]:
            expected_tags = ['ceph_fsid:e0efcf84-e8ed-4916-8ce1-9c70242d390a','ceph_mon_state:leader',
                             'ceph_osd:%s' % osd]

            for metric in ['ceph.osd.pct_used']:
                self.assertMetric(metric, value=pct_used, count=1, tags=expected_tags)

        self.assertMetric('ceph.num_full_osds', value=1, count=1,
                          tags=['ceph_fsid:e0efcf84-e8ed-4916-8ce1-9c70242d390a', 'ceph_mon_state:leader'])
        self.assertMetric('ceph.num_near_full_osds', value=1, count=1,
                          tags=['ceph_fsid:e0efcf84-e8ed-4916-8ce1-9c70242d390a', 'ceph_mon_state:leader'])

        for pool in ['rbd', 'scbench']:
            expected_tags = ['ceph_fsid:e0efcf84-e8ed-4916-8ce1-9c70242d390a','ceph_mon_state:leader',
                 'ceph_pool:%s' % pool]
            expected_metrics = ['ceph.read_op_per_sec', 'ceph.write_op_per_sec', 'ceph.op_per_sec']
            for metric in expected_metrics:
                self.assertMetric(metric, count=1, tags=expected_tags)

    def test_osd_status_metrics_non_osd_health(self):
        """
        The `detail` key of `health detail` can contain info on the health of non-osd units:
        shouldn't make the check fail
        """
        mocks = {
            '_collect_raw': lambda x,y,z: json.loads(
                Fixtures.read_file('ceph_10.2.2_mon_health.json', sdk_dir=self.FIXTURE_DIR)),
        }
        config = {
            'instances': [{'host': 'foo'}]
        }

        self.run_check_twice(config, mocks=mocks, force_reload=True)

        self.assertMetric('ceph.num_full_osds', value=0, count=1,
                          tags=['ceph_fsid:7d375c2a-902a-4990-93fd-ce21a296f444', 'ceph_mon_state:leader'])
        self.assertMetric('ceph.num_near_full_osds', value=0, count=1,
                          tags=['ceph_fsid:7d375c2a-902a-4990-93fd-ce21a296f444', 'ceph_mon_state:leader'])
