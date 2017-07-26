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

from kazoo.client import KazooClient

# project
from tests.checks.common import AgentCheckTest


instances = [{
    'kafka_connect_str': '172.17.0.1:9092',
    'zk_connect_str': 'localhost:2181',
    # 'zk_prefix': '/0.8',
    'consumer_groups': {
        'my_consumer': {
            'marvel': [0]
        }
    }
}]

BROKER_METRICS = [
    'kafka.broker_offset',
]

CONSUMER_METRICS = [
    'kafka.consumer_offset',
    'kafka.consumer_lag',
]

TOPICS = ['marvel', 'dc', '__consumer_offsets']
PARTITIONS = [0]

SHUTDOWN = threading.Event()

class Producer(threading.Thread):

    def run(self):
        producer = KafkaProducer(bootstrap_servers=instances[0]['kafka_connect_str'])

        while not SHUTDOWN.is_set():
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


class ZKConsumer(threading.Thread):

    def run(self):
        zk_path_topic_tmpl = '/consumers/my_consumer/offsets/'
        zk_path_partition_tmpl = zk_path_topic_tmpl + '{topic}/{partition}'

        zk_conn = KazooClient(instances[0]['zk_connect_str'], timeout=10)
        zk_conn.start()

        for topic in TOPICS:
            for partition in PARTITIONS:
                node_path = zk_path_partition_tmpl.format(topic=topic, partition=partition)
                node = zk_conn.exists(node_path)
                if not node:
                    zk_conn.ensure_path(node_path)
                    zk_conn.set(node_path, str(0))

        consumer = KafkaConsumer(bootstrap_servers=instances[0]['kafka_connect_str'],
                                 group_id="my_consumer",
                                 auto_offset_reset='earliest',
                                 enable_auto_commit=False)
        consumer.subscribe(TOPICS)

        while not SHUTDOWN.is_set():
            response = consumer.poll(timeout_ms=500, max_records=10)
            zk_trans = zk_conn.transaction()
            for tp, records in response.iteritems():
                topic = tp.topic
                partition = tp.partition

                offset = None
                for record in records:
                    if offset is None or record.offset > offset:
                        offset = record.offset

                if offset:
                    zk_trans.set_data(
                        os.path.join(zk_path_topic_tmpl.format(topic), str(partition)),
                        str(offset)
                    )

            zk_trans.commit()

        zk_conn.stop()

class KConsumer(threading.Thread):

    def run(self):
        consumer = KafkaConsumer(bootstrap_servers=instances[0]['kafka_connect_str'],
                                 group_id="my_consumer",
                                 auto_offset_reset='earliest')
        consumer.subscribe(TOPICS)

        while not SHUTDOWN.is_set():
            response = consumer.poll(timeout_ms=500, max_records=10)


@attr(requires='kafka_consumer')
class TestKafka(AgentCheckTest):
    """Basic Test for kafka_consumer integration."""
    CHECK_NAME = 'kafka_consumer'
    THREADS = [Producer()]

    def __init__(self, *args, **kwargs):
        super(TestKafka, self).__init__(*args, **kwargs)

        if os.environ.get('FLAVOR_OPTIONS','').lower() == "kafka":
            self.THREADS.append(KConsumer())
        else:
            self.THREADS.append(ZKConsumer())

    @classmethod
    def setUpClass(cls):
        cls.THREADS[0].start()
        time.sleep(30)
        cls.THREADS[1].start()
        time.sleep(30)

    @classmethod
    def tearDownClass(cls):
        SHUTDOWN.set()
        for t in cls.THREADS:
            if t.is_alive():
                t.join(5)

    def test_check_zk(self):
        """
        Testing Kafka_consumer check.
        """

        if os.environ.get('FLAVOR_OPTIONS','').lower() == "kafka":
            raise SkipTest("Skipping test - environment not configured for ZK consumer offsets")

        self.run_check({'instances': instances})

        for instance in instances:
            for name, consumer_group in instance['consumer_groups'].iteritems():
                for topic, partitions in consumer_group.iteritems():
	            if topic is not '__consumer_offsets':
                        for partition in partitions:
                            tags = ["topic:{}".format(topic),
                                    "partition:{}".format(partition)]
                            for mname in BROKER_METRICS:
                                self.assertMetric(mname, tags=tags, at_least=1)
                            for mname in CONSUMER_METRICS:
                                self.assertMetric(mname, tags=tags + ["consumer_group:{}".format(name)], at_least=1)
                    else:
                        for mname in BROKER_METRICS:
                            self.assertMetric(mname, at_least=1)

        self.coverage_report()


    def test_check_nogroups_zk(self):
        """
        Testing Kafka_consumer check grabbing groups from ZK
        """

        if os.environ.get('FLAVOR_OPTIONS','').lower() == "kafka":
            raise SkipTest("Skipping test - environment not configured for ZK consumer offsets")

        nogroup_instances = copy.deepcopy(instances)
        nogroup_instances[0].pop('consumer_groups')
        nogroup_instances[0]['monitor_unlisted_consumer_groups'] = True

        self.run_check({'instances': nogroup_instances})

        for instance in nogroup_instances:
            for topic in TOPICS:
	        if topic is not '__consumer_offsets':
                    for partition in PARTITIONS:
	                tags = ["topic:{}".format(topic),
                                "partition:{}".format(partition)]
                        for mname in BROKER_METRICS:
                            self.assertMetric(mname, tags=tags, at_least=1)
                        for mname in CONSUMER_METRICS:
                            self.assertMetric(mname, tags=tags + ["consumer_group:my_consumer"], at_least=1)
                else:
                    for mname in BROKER_METRICS:
                        self.assertMetric(mname, at_least=1)

        self.coverage_report()
