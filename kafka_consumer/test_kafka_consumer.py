# (C) Datadog, Inc. 2010-2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# stdlib
from nose.plugins.attrib import attr

# 3p

# project
from tests.checks.common import AgentCheckTest


instance = [{
    'kafka_connect_str': 'localhost:9092',
    'zk_connect_str': 'localhost:2181',
    # 'zk_prefix': '/0.8',
    'consumer_groups': {
        'my_consumer': {
            'test': [0]
        }
    }
}]

METRICS = [
    'kafka.broker_offset',
    'kafka.consumer_offset',
    'kafka.consumer_lag',
]

# NOTE: Feel free to declare multiple test classes if needed

@attr(requires='kafka_consumer')
class TestKafka(AgentCheckTest):
    """Basic Test for kafka_consumer integration."""
    CHECK_NAME = 'kafka_consumer'

    def test_check(self):
        """
        Testing Kafka_consumer check w/ zookeeper.
        """
        self.run_check({'instances': instance})

        for mname in METRICS:
            self.assertMetric(mname, at_least=1)

        self.coverage_report()

    def test_kafka_nozk(self):
        """
        Testing Kafka_consumer check without zookeeper
        """
        config = {'instances': instance}
        config['instances'][0]['zk_offsets'] = False
        self.run_check(config)

        for mname in METRICS:
            self.assertMetric(mname, at_least=1)

        self.coverage_report()
