# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import subprocess
import os
import time
import re
import threading
from distutils.version import LooseVersion

import pytest
import docker
from kafka import (
    KafkaConsumer,
    KafkaProducer,
)
from kazoo.client import KazooClient

from .common import (
    KAFKA_LEGACY,
    ZK_CONNECT_STR,
    ZK_INSTANCE,
    KAFKA_INSTANCE,
    KAFKA_CONNECT_STR,
    PARTITIONS,
    TOPICS,
)


MAX_ITERATIONS = 60

HERE = os.path.dirname(os.path.abspath(__file__))

docker_client = docker.from_env()


class StoppableThread(threading.Thread):

    def __init__(self):
        self._shutdown_event = threading.Event()
        super(StoppableThread, self).__init__()

    def send_shutdown(self):
        self._shutdown_event.set()


class Producer(StoppableThread):

    def run(self):
        producer = KafkaProducer(bootstrap_servers=ZK_INSTANCE['kafka_connect_str'])

        iteration = 0
        while not self._shutdown_event.is_set() and iteration < MAX_ITERATIONS:
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
                except Exception:
                    pass

            iteration += 1
            time.sleep(1)


class ZKConsumer(StoppableThread):

    def __init__(self, topics, partitions):
        self.zk_connect_str = ZK_CONNECT_STR
        self.kafka_connect_str = KAFKA_CONNECT_STR
        self.topics = topics
        self.partitions = partitions
        super(ZKConsumer, self).__init__()

    def run(self):
        zk_path_topic_tmpl = '/consumers/my_consumer/offsets/'
        zk_path_partition_tmpl = zk_path_topic_tmpl + '{topic}/{partition}'

        zk_conn = KazooClient(self.zk_connect_str, timeout=10)
        zk_conn.start()

        for topic in self.topics:
            for partition in self.partitions:
                node_path = zk_path_partition_tmpl.format(topic=topic, partition=partition)
                node = zk_conn.exists(node_path)
                if not node:
                    zk_conn.ensure_path(node_path)
                    zk_conn.set(node_path, str(0))

        consumer = KafkaConsumer(bootstrap_servers=[self.kafka_connect_str],
                                 group_id="my_consumer",
                                 auto_offset_reset='earliest',
                                 enable_auto_commit=False)
        consumer.subscribe(self.topics)

        iteration = 0
        while not self._shutdown_event.is_set() and iteration < MAX_ITERATIONS:
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
            iteration += 1

        zk_conn.stop()


class KConsumer(StoppableThread):

    def __init__(self, topics):
        self.kafka_connect_str = KAFKA_CONNECT_STR
        self.topics = topics
        super(KConsumer, self).__init__()

    def run(self):
        consumer = KafkaConsumer(bootstrap_servers=[self.kafka_connect_str],
                                 group_id="my_consumer",
                                 auto_offset_reset='earliest')
        consumer.subscribe(self.topics)

        iteration = 0
        while not self._shutdown_event.is_set() and iteration < MAX_ITERATIONS:
            consumer.poll(timeout_ms=500, max_records=10)
            iteration += 1


# might block indefinitely - watchout
def wait_for_logs(container_id, pattern, timeout=30):
    container = docker_client.containers.get(container_id)
    if not container:
        return False

    regex = re.compile(pattern)
    now = time.time()
    while time.time() < (now + timeout):
        loglines = container.logs().splitlines()
        for line in loglines:
            result = regex.match(line)
            if result:
                return True

        time.sleep(1)

    return False


@pytest.fixture(scope="session")
def kafka_cluster():
    """
    Start a kafka cluster.
    """
    env = os.environ
    args = [
        "docker-compose",
        "-f", os.path.join(HERE, 'compose', 'kafka-cluster.compose')
    ]

    subprocess.check_call(args + ["up", "-d"], env=env)

    clean = True
    clean &= wait_for_logs('compose_kafka_1', '.*started \(kafka.server.KafkaServer\).*', timeout=20)
    clean &= wait_for_logs('compose_zookeeper_1', '.*NoNode for \/brokers.*', timeout=20)
    if LooseVersion(env.get('KAFKA_VERSION')) > KAFKA_LEGACY:
        clean &= wait_for_logs('compose_kafka_1', '.*Created topic "marvel".*', timeout=20)
        clean &= wait_for_logs('compose_kafka_1', '.*Created topic "dc".*', timeout=20)

    env['EXTERNAL_JMX_PORT'] = '9998'
    env['EXTERNAL_PORT'] = '9091'
    subprocess.check_call(args + ["scale", "kafka=2"], env=env)
    clean &= wait_for_logs('compose_kafka_2', '.*started \(kafka.server.KafkaServer\).*', timeout=20)
    yield clean

    subprocess.check_call(args + ["down"], env=env)


@pytest.fixture(scope="session")
def kafka_producer(kafka_cluster):
    producer = Producer()
    yield producer
    if producer.is_alive():
        producer.send_shutdown()
        producer.join(5)


@pytest.fixture(scope="session")
def kafka_consumer(kafka_producer):
    consumer = KConsumer(TOPICS)
    yield consumer
    if consumer.is_alive():
        consumer.send_shutdown()
        consumer.join(5)


@pytest.fixture(scope="session")
def zk_consumer(kafka_producer):
    consumer = ZKConsumer(TOPICS, PARTITIONS)
    yield consumer
    if consumer.is_alive():
        consumer.send_shutdown()
        consumer.join(5)


@pytest.fixture
def aggregator():
    from datadog_checks.stubs import aggregator
    aggregator.reset()
    return aggregator


@pytest.fixture
def zk_instance():
    return ZK_INSTANCE


@pytest.fixture
def kafka_instance():
    return KAFKA_INSTANCE
