# (C) Datadog, Inc. 2010-2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# stdlib
import copy
import os
import time
import threading

# 3p
from nose.plugins.attrib import attr
from nose import SkipTest
from kafka import KafkaConsumer, KafkaProducer

# project
from tests.checks.common import AgentCheckTest


instance = [{
    'kafka_connect_str': '172.17.0.1:9092',
    'zk_connect_str': 'localhost:2181',
    # 'zk_prefix': '/0.8',
    'consumer_groups': {
        'my_consumer': {
            'marvel': [0]
        }
    }
}]

METRICS = [
    'kafka.broker_offset',
    'kafka.consumer_offset',
    'kafka.consumer_lag',
]

class Producer(threading.Thread):
    daemon = True

    def run(self):
        producer = KafkaProducer(bootstrap_servers=instance[0]['kafka_connect_str'])

        while True:
            producer.send('marvel', b"Peter Parker")
            producer.send('marvel', b"Bruce Banner")
            producer.send('marvel', b"Tony Stark")
            producer.send('marvel', b"Johhny Blaze")
            producer.send('marvel', b"\xc2BoomShakalaka")
            producer.send('dc', b"Diana Prince")
            producer.send('dc', b"Bruce Wayne")
            producer.send('dc', b"Clark Kent")
            producer.send('dc', b"Arthur Curry")
            producer.send('dc', b"\xc2ShakalakaBoom")
            time.sleep(1)


class Consumer(threading.Thread):
    daemon = True

    def run(self):
        consumer = KafkaConsumer(bootstrap_servers=instance[0]['kafka_connect_str'],
                                 group_id="my_consumer",
                                 auto_offset_reset='earliest')
        consumer.subscribe(['marvel'])

        for message in consumer:
            pass

@attr(requires='kafka_consumer')
class TestKafka(AgentCheckTest):
    """Basic Test for kafka_consumer integration."""
    CHECK_NAME = 'kafka_consumer'

    def setUp(self):
        threads = [
            Producer(),
            Consumer()
        ]

        for t in threads:
            t.start()

        # let's generate a few before running test.
        time.sleep(10)

    def test_check(self):
        """
        Testing Kafka_consumer check.
        """

        if os.environ.get('FLAVOR_OPTIONS','').lower() == "kafka":
            raise SkipTest("Skipping test - environment not configured for ZK consumer offsets")

        self.run_check({'instances': instance})

        for mname in METRICS:
            self.assertMetric(mname, at_least=1)

        self.coverage_report()


    def test_check_nogroups(self):
        """
        Testing Kafka_consumer check grabbing groups from ZK
        """

        if os.environ.get('FLAVOR_OPTIONS','').lower() == "kafka":
            raise SkipTest("Skipping test - environment not configured for ZK consumer offsets")

        nogroup_instance = copy.copy(instance)
        nogroup_instance[0].pop('consumer_groups')
        nogroup_instance[0]['monitor_unlisted_consumer_groups'] = True

        self.run_check({'instances': instance})

        for mname in METRICS:
            self.assertMetric(mname, at_least=1)

        self.coverage_report()
