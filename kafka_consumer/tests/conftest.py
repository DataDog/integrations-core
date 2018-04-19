# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import subprocess
import os
import time
import threading
import sys

import pytest
from kafka import KafkaConsumer, KafkaProducer
from kazoo.client import KazooClient

from .common import ZK_CONNECT_STR, KAFKA_CONNECT_STR, PARTITIONS, TOPICS, HOST_IP


HERE = os.path.dirname(os.path.abspath(__file__))


class StoppableThread(threading.Thread):

    def __init__(self):
        self._shutdown_event = threading.Event()
        super(StoppableThread, self).__init__()

    def send_shutdown(self):
        self._shutdown_event.set()


class Producer(StoppableThread):

    def run(self):
        producer = KafkaProducer(bootstrap_servers=KAFKA_CONNECT_STR)

        iteration = 0
        while not self._shutdown_event.is_set():
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
        while not self._shutdown_event.is_set():
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
        consumer = KafkaConsumer(bootstrap_servers=self.kafka_connect_str,
                                 group_id="my_consumer",
                                 auto_offset_reset='earliest')
        consumer.subscribe(self.topics)

        iteration = 0
        while not self._shutdown_event.is_set():
            consumer.poll(timeout_ms=500, max_records=10)
            iteration += 1


@pytest.fixture(scope="session")
def kafka_cluster():
    """
    Start a kafka cluster and wait for it to be up and running.
    """
    env = os.environ
    # Advertising the hostname doesn't work on docker:dind so we manually
    # resolve the IP address. This seems to also work outside docker:dind
    # so we got that goin for us.
    env['KAFKA_HOST'] = HOST_IP

    args = [
        "docker-compose",
        "-f", os.path.join(HERE, 'docker-compose.yml')
    ]

    subprocess.check_call(args + ["up", "-d"], env=env)

    # wait for Kafka to be up and running
    attempts = 0
    while True:
        # This is useful to debug Kafka booting and not too verbose when
        # everything runs smooth, let's leave it here
        sys.stderr.write("Attempt number {}\n".format(attempts+1))

        # this brings a total of 90s to timeout
        if attempts >= 30:
            # print the whole compose log in case of timeout to help diagnose
            subprocess.check_call(args + ["logs"], env=env)
            subprocess.check_call(args + ["down"], env=env)
            raise Exception("Kafka boot timed out!")

        try:
            consumer = KafkaConsumer(bootstrap_servers=KAFKA_CONNECT_STR)
            topics = consumer.topics()
            sys.stderr.write("Got topics: {}\n".format(topics))
        except Exception as e:
            sys.stderr.write(str(e)+'\n')
            topics = {}

        # we expect to find 2 topics, "dc" and "marvel"
        if len(topics) == 2:
            break

        attempts += 1
        time.sleep(3)

    yield

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
    return {
        'kafka_connect_str': KAFKA_CONNECT_STR,
        'zk_connect_str': ZK_CONNECT_STR,
        'consumer_groups': {
            'my_consumer': {
                'marvel': [0]
            }
        }
    }


@pytest.fixture
def kafka_instance():
    return {
        'kafka_connect_str': KAFKA_CONNECT_STR,
        'kafka_consumer_offsets': True,
        'tags': ['optional:tag1'],
        'consumer_groups': {
            'my_consumer': {
                'marvel': [0]
            }
        }
    }
