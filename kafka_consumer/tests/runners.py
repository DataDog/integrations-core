# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import os
import threading
import time

from kafka import KafkaConsumer, KafkaProducer
from kazoo.client import KazooClient
from six import iteritems

from .common import KAFKA_CONNECT_STR, PARTITIONS, ZK_CONNECT_STR

DEFAULT_SLEEP = 5
DEFAULT_TIMEOUT = 5


class StoppableThread(threading.Thread):
    def __init__(self, sleep=DEFAULT_SLEEP, timeout=DEFAULT_TIMEOUT):
        super(StoppableThread, self).__init__()
        self._shutdown_event = threading.Event()
        self._sleep = sleep
        self._timeout = timeout

    def __enter__(self):
        self.start()
        time.sleep(self._sleep)
        return self

    def __exit__(self, *args, **kwargs):
        self._shutdown_event.set()
        self.join(self._timeout)


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


class KConsumer(StoppableThread):
    def __init__(self, topics, sleep=DEFAULT_SLEEP, timeout=DEFAULT_TIMEOUT):
        super(KConsumer, self).__init__(sleep=sleep, timeout=timeout)
        self.kafka_connect_str = KAFKA_CONNECT_STR
        self.topics = topics

    def run(self):
        consumer = KafkaConsumer(bootstrap_servers=self.kafka_connect_str,
                                 group_id="my_consumer",
                                 auto_offset_reset='earliest')
        consumer.subscribe(self.topics)

        iteration = 0
        while not self._shutdown_event.is_set():
            consumer.poll(timeout_ms=500, max_records=10)
            iteration += 1


class ZKConsumer(StoppableThread):
    def __init__(self, topics, partitions, sleep=DEFAULT_SLEEP, timeout=DEFAULT_TIMEOUT):
        super(ZKConsumer, self).__init__(sleep=sleep, timeout=timeout)
        self.zk_connect_str = ZK_CONNECT_STR
        self.kafka_connect_str = KAFKA_CONNECT_STR
        self.topics = topics
        self.partitions = partitions

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
            for tp, records in iteritems(response):
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
