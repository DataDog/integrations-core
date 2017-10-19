# stdlib
import os
import json

# project
from tests.checks.common import AgentCheckTest, Fixtures, get_check_class


class TestMesosMaster(AgentCheckTest):
    CHECK_NAME = 'mesos_master'
    FIXTURE_DIR = os.path.join(os.path.dirname(__file__), 'ci')

    def test_checks(self):
        config = {
            'init_config': {},
            'instances': [
                {
                    'url': 'http://localhost:5050'
                }
            ]
        }

        mocks = {
            '_get_master_roles': lambda x, y, z: json.loads(
                Fixtures.read_file('roles.json', sdk_dir=self.FIXTURE_DIR)),
            '_get_master_stats': lambda x, y, z: json.loads(
                Fixtures.read_file('stats.json', sdk_dir=self.FIXTURE_DIR)),
            '_get_master_state': lambda x, y, z: json.loads(
                Fixtures.read_file('state.json', sdk_dir=self.FIXTURE_DIR)),
        }

        klass = get_check_class('mesos_master')
        check = klass('mesos_master', {}, {})
        self.run_check_twice(config, mocks=mocks)
        metrics = {}
        for d in (check.CLUSTER_TASKS_METRICS, check.CLUSTER_SLAVES_METRICS,
                  check.CLUSTER_RESOURCES_METRICS, check.CLUSTER_REGISTRAR_METRICS,
                  check.CLUSTER_FRAMEWORK_METRICS, check.SYSTEM_METRICS, check.STATS_METRICS):
            metrics.update(d)
        [self.assertMetric(v[0]) for k, v in check.FRAMEWORK_METRICS.iteritems()]
        [self.assertMetric(v[0]) for k, v in metrics.iteritems()]
        [self.assertMetric(v[0]) for k, v in check.ROLE_RESOURCES_METRICS.iteritems()]
        self.assertMetric('mesos.cluster.total_frameworks')
        self.assertMetric('mesos.framework.total_tasks')
        self.assertMetric('mesos.role.frameworks.count')
        self.assertMetric('mesos.role.weight')
