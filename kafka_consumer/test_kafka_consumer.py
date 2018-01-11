# (C) Datadog, Inc. 2010-2017
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
from docker import Client  # required by test setup

# project
from tests.checks.common import AgentCheckTest, log


zk_instance = {
    'kafka_connect_str': '172.17.0.1:9092',
    'zk_connect_str': 'localhost:2181',
    # 'zk_prefix': '/0.8',
    'consumer_groups': {
        'my_consumer': {
            'marvel': [0]
        }
    }
}

kafka_instance = {
    'kafka_connect_str': '172.17.0.1:9092',
    'kafka_consumer_offsets': True,
    'consumer_groups': {
        'my_consumer': {
            'marvel': [0]
        }
    }
}


BROKER_METRICS = [
    'kafka.broker_offset',
]

CONSUMER_METRICS = [
    'kafka.consumer_offset',
    'kafka.consumer_lag',
]

TOPICS = ['marvel', 'dc', '__consumer_offsets']
PARTITIONS = [0, 1]

SHUTDOWN = threading.Event()
CLUSTER_READY = 'Stabilized group my_consumer'
KAFKA_IMAGE_NAME = 'wurstmeister/kafka'
DOCKER_TO = 10

class Producer(threading.Thread):

    def run(self):
        producer = KafkaProducer(bootstrap_servers=zk_instance['kafka_connect_str'])

        while not SHUTDOWN.is_set():
            for partition in PARTITIONS:
                try:
                    producer.send('marvel', b"Peter Parker", partition=partition)
                    producer.send('marvel', b"Bruce Banner", partition=partition)
                    producer.send('marvel', b"Tony Stark", partition=partition)
                    producer.send('marvel', b"Johhny Blaze", partition=partition)
                    producer.send('marvel', b"\xc2BoomShakalaka", partition=partition)
                    producer.send('dc', b"Diana Prince", partition=partition)
                    producer.send('dc', b"Bruce Wayne", partition=partition)
                    producer.send('dc', b"Clark Kent", partition=partition)
                    producer.send('dc', b"Arthur Curry", partition=partition)
                    producer.send('dc', b"\xc2ShakalakaBoom", partition=partition)
                    time.sleep(1)
                except Exception:
                    pass


class ZKConsumer(threading.Thread):

    def run(self):
        zk_path_topic_tmpl = '/consumers/my_consumer/offsets/'
        zk_path_partition_tmpl = zk_path_topic_tmpl + '{topic}/{partition}'

        zk_conn = KazooClient(zk_instance['zk_connect_str'], timeout=10)
        zk_conn.start()

        for topic in TOPICS:
            for partition in PARTITIONS:
                node_path = zk_path_partition_tmpl.format(topic=topic, partition=partition)
                node = zk_conn.exists(node_path)
                if not node:
                    zk_conn.ensure_path(node_path)
                    zk_conn.set(node_path, str(0))

        consumer = KafkaConsumer(bootstrap_servers=zk_instance['kafka_connect_str'],
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
        consumer = KafkaConsumer(bootstrap_servers=kafka_instance['kafka_connect_str'],
                                 group_id="my_consumer",
                                 auto_offset_reset='earliest')
        consumer.subscribe(TOPICS)

        while not SHUTDOWN.is_set():
            consumer.poll(timeout_ms=500, max_records=10)


@attr(requires='kafka_consumer')
class TestKafka(AgentCheckTest):
    """Basic Test for kafka_consumer integration."""
    CHECK_NAME = 'kafka_consumer'
    MAX_SETUP_WAIT = 60
    THREADS = [Producer()]

    def __init__(self, *args, **kwargs):
        super(TestKafka, self).__init__(*args, **kwargs)

        if os.environ.get('FLAVOR_OPTIONS','').lower() == "kafka":
            self.THREADS.append(KConsumer())
        else:
            self.THREADS.append(ZKConsumer())

    @classmethod
    def setUpClass(cls):
        """
        Setup the consumer + producer, and wait for cluster
        """
        start = time.time()

        cls.THREADS[0].start()
        time.sleep(5)
        cls.THREADS[1].start()
        time.sleep(5)

        try:
            cli = Client(base_url='unix://var/run/docker.sock',
                         timeout=DOCKER_TO)
            containers = cli.containers()

            nodes = []
            for c in containers:
                if KAFKA_IMAGE_NAME in c.get('Image'):
                    nodes.append(c)

            elapsed = time.time() - start
            while elapsed < cls.MAX_SETUP_WAIT:
                for node in nodes:
                    _log = cli.logs(node.get('Id'))
                    if CLUSTER_READY in _log:
                        return

                time.sleep(1)
                elapsed = time.time() - start
        except Exception:
            pass

        log.info('Unable to verify kafka cluster status - tests may fail')

    @classmethod
    def tearDownClass(cls):
        SHUTDOWN.set()
        for t in cls.THREADS:
            if t.is_alive():
                t.join(5)

    def is_supported(self, flavors):
        supported = False
        version = os.environ.get('FLAVOR_VERSION')
        flavor = os.environ.get('FLAVOR_OPTIONS','').lower()

        if not version:
            return False

        for f in flavors:
            if f == flavor:
                supported = True

        if not supported:
            return False

        if version is not 'latest':
            version = version.split('-')[0]
            version = tuple(s for s in version.split('.') if s.strip())
            if flavor is 'kafka' and version <= self.check.LAST_ZKONLY_VERSION:
                supported = False

        return supported


    def test_check_zk(self):
        """
        Testing Kafka_consumer check.
        """

        if not self.is_supported(['zookeeper']):
            raise SkipTest("Skipping test - not supported in current environment")

        instances = [zk_instance]
        self.run_check({'instances': instances})

        for instance in instances:
            for name, consumer_group in instance['consumer_groups'].iteritems():
                for topic, partitions in consumer_group.iteritems():
                    for partition in partitions:
                        tags = ["topic:{}".format(topic),
                                "partition:{}".format(partition)]
                        for mname in BROKER_METRICS:
                            self.assertMetric(mname, tags=tags, at_least=1)
                        for mname in CONSUMER_METRICS:
                            self.assertMetric(mname, tags=tags + ["source:zk", "consumer_group:{}".format(name)], at_least=1)

        # let's reassert for the __consumer_offsets - multiple partitions
        self.assertMetric('kafka.broker_offset', at_least=1)
        self.coverage_report()

    def test_multiple_servers_zk(self):
        """
        Testing Kafka_consumer check.
        """

        if not self.is_supported(['zookeeper']):
            raise SkipTest("Skipping test - not supported in current environment")

        multiple_server_zk_instance = copy.deepcopy(zk_instance)
        multiple_server_zk_instance['kafka_connect_str'] = [
            multiple_server_zk_instance['kafka_connect_str'],
            'localhost:9092']

        instances = [multiple_server_zk_instance]
        self.run_check({'instances': instances})

        for instance in instances:
            for name, consumer_group in instance['consumer_groups'].iteritems():
                for topic, partitions in consumer_group.iteritems():
                    for partition in partitions:
                        tags = ["topic:{}".format(topic),
                                "partition:{}".format(partition)]
                        for mname in BROKER_METRICS:
                            self.assertMetric(mname, tags=tags, at_least=1)
                        for mname in CONSUMER_METRICS:
                            self.assertMetric(mname, tags=tags + ["source:zk", "consumer_group:{}".format(name)], at_least=1)


    def test_check_nogroups_zk(self):
        """
        Testing Kafka_consumer check grabbing groups from ZK
        """

        if not self.is_supported(['zookeeper']):
            raise SkipTest("Skipping test - not supported in current environment")

        nogroup_instance = copy.deepcopy(zk_instance)
        nogroup_instance.pop('consumer_groups')
        nogroup_instance['monitor_unlisted_consumer_groups'] = True

        instances = [nogroup_instance]
        self.run_check({'instances': instances})

        for instance in instances:
            for topic in TOPICS:
                if topic is not '__consumer_offsets':
                    for partition in PARTITIONS:
                        tags = ["topic:{}".format(topic),
                                "partition:{}".format(partition)]
                        for mname in BROKER_METRICS:
                            self.assertMetric(mname, tags=tags, at_least=1)
                            for mname in CONSUMER_METRICS:
                                self.assertMetric(mname, tags=tags + ["source:zk", "consumer_group:my_consumer"], at_least=1)
                else:
                    for mname in BROKER_METRICS + CONSUMER_METRICS:
                        self.assertMetric(mname, at_least=1)

        self.coverage_report()

    def test_check_kafka(self):
        """
        Testing Kafka_consumer check.
        """

        if not self.is_supported(['kafka']):
            raise SkipTest("Skipping test - not supported in current environment")

        instances = [kafka_instance]
        self.run_check({'instances': instances})

        for instance in instances:
            for name, consumer_group in instance['consumer_groups'].iteritems():
                for topic, partitions in consumer_group.iteritems():
                    for partition in partitions:
                        tags = ["topic:{}".format(topic),
                                "partition:{}".format(partition)]
                        for mname in BROKER_METRICS:
                            self.assertMetric(mname, tags=tags, at_least=1)
                        for mname in CONSUMER_METRICS:
                            self.assertMetric(mname, tags=tags + ["source:kafka", "consumer_group:{}".format(name)], at_least=1)

        # let's reassert for the __consumer_offsets - multiple partitions
        self.assertMetric('kafka.broker_offset', at_least=1)
        self.coverage_report()
