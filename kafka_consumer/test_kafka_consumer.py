# (C) Datadog, Inc. 2010-2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# stdlib
import threading, time

# 3p
from nose.plugins.attrib import attr
from kafka import KafkaConsumer, KafkaProducer

# project
from tests.checks.common import AgentCheckTest


instance = [{
    'kafka_connect_str': 'localhost:9092',
    'zk_connect_str': 'localhost:2181',
    # 'zk_prefix': '/0.8',
    'consumer_groups': {
        'my_consumer': {
            'my_topic': [0]
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
            producer.send('my_topic', b"test")
            producer.send('my_topic', b"\xc2BoomShakalaka")
            time.sleep(1)


class Consumer(threading.Thread):
    daemon = True

    def run(self):
        consumer = KafkaConsumer(bootstrap_servers=instance[0]['kafka_connect_str'],
                                 group_id="my_consumer",
                                 auto_offset_reset='earliest')
        consumer.subscribe(['my_topic'])

        for message in consumer:
            print (message)


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
