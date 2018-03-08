# stdlib
import os

# Project
from tests.checks.common import AgentCheckTest, Fixtures

# 3rd Party
import mock
import json

FIXTURE_DIR = os.path.join(os.path.dirname(__file__), 'ci')

def requests_get_mock(*args, **kwargs):
    class MockResponse:
        def __init__(self, json_data, status_code):
            self.json_data = json_data
            self.status_code = status_code

        def json(self):
            print self.json_data
            return json.loads(self.json_data)

        def raise_for_status(self):
            return True


    with open(Fixtures.file('hdfs_datanode_jmx', sdk_dir=FIXTURE_DIR), 'r') as f:
        body = f.read()
        return MockResponse(body, 200)

class HDFSDataNode(AgentCheckTest):
    CHECK_NAME = 'hdfs_datanode'

    HDFS_DATANODE_CONFIG = {
        'hdfs_datanode_jmx_uri': 'http://localhost:50075',
        'tags': ['optional:tag1']
    }

    HDFS_DATANODE_METRICS_VALUES = {
        'hdfs.datanode.dfs_remaining': 27914526720,
        'hdfs.datanode.dfs_capacity': 41167421440,
        'hdfs.datanode.dfs_used': 501932032,
        'hdfs.datanode.cache_capacity': 0,
        'hdfs.datanode.cache_used': 0,
        'hdfs.datanode.last_volume_failure_date': 0,
        'hdfs.datanode.estimated_capacity_lost_total': 0,
        'hdfs.datanode.num_blocks_cached': 0,
        'hdfs.datanode.num_failed_volumes': 0,
        'hdfs.datanode.num_blocks_failed_to_cache': 0,
        'hdfs.datanode.num_blocks_failed_to_uncache': 0,
    }

    HDFS_DATANODE_METRIC_TAGS = [
        'datanode_url:' + HDFS_DATANODE_CONFIG['hdfs_datanode_jmx_uri'],
        'optional:tag1'
    ]

    @mock.patch('requests.get', side_effect=requests_get_mock)
    def test_check(self, mock_requests):
        config = {
            'instances': [self.HDFS_DATANODE_CONFIG]
        }

        self.run_check(config)

        for metric, value in self.HDFS_DATANODE_METRICS_VALUES.iteritems():
            self.assertMetric(metric, value=value, tags=self.HDFS_DATANODE_METRIC_TAGS)
