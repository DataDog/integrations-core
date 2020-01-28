# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import threading
import time

from kafka import KafkaConsumer, KafkaProducer
from kazoo.client import KazooClient
from six import binary_type, iteritems

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
    """
    A consumer that stores consumer offsets in a Kafka topic.
    """

    def __init__(self, topics, sleep=DEFAULT_SLEEP, timeout=DEFAULT_TIMEOUT):
        super(KConsumer, self).__init__(sleep=sleep, timeout=timeout)
        self.kafka_connect_str = KAFKA_CONNECT_STR
        self.topics = topics
        self.group_id = 'my_consumer'

    def run(self):
        # By default, `KafkaConsumer` automatically commits offsets to a Kafka topic in the background.
        # See: https://kafka-python.readthedocs.io/en/master/apidoc/KafkaConsumer.html#kafka.KafkaConsumer.commit
        consumer = KafkaConsumer(
            bootstrap_servers=self.kafka_connect_str, group_id=self.group_id, auto_offset_reset='earliest'
        )
        consumer.subscribe(self.topics)

        while not self._shutdown_event.is_set():
            consumer.poll(timeout_ms=500, max_records=10)


class ZKConsumer(StoppableThread):
    """
    A consumer that stores consumer offsets in ZooKeeper.
    """

    def __init__(self, topics, partitions, sleep=DEFAULT_SLEEP, timeout=DEFAULT_TIMEOUT):
        super(ZKConsumer, self).__init__(sleep=sleep, timeout=timeout)
        self.zk_connect_str = ZK_CONNECT_STR
        self.kafka_connect_str = KAFKA_CONNECT_STR
        self.topics = topics
        self.partitions = partitions
        self.group_id = 'my_consumer'

    def run(self):
        with ZooKeeperClient(self.zk_connect_str) as zk:
            zk.ensure_topics_and_partitions_exist(
                group_id=self.group_id, topics=self.topics, partitions=self.partitions
            )

            consumer = KafkaConsumer(
                bootstrap_servers=[self.kafka_connect_str],
                group_id=self.group_id,
                auto_offset_reset='earliest',
                # By default, `KafkaConsumer` automatically commits offsets in the background, but...
                # "If you need to store offsets in anything other than Kafka, this API should not be used."
                # Since we want to store offsets in ZooKeeper here, we must disable auto-commit,
                # and manage offsets manually below.
                # See also:
                # https://kafka-python.readthedocs.io/en/master/apidoc/KafkaConsumer.html#kafka.KafkaConsumer.commit
                enable_auto_commit=False,
            )
            consumer.subscribe(self.topics)

            while not self._shutdown_event.is_set():
                response = consumer.poll(timeout_ms=500, max_records=10)
                zk.update_offsets(group_id=self.group_id, response=response)


# See: https://elang2.github.io/myblog/posts/2017-09-20-Kafak-And-Zookeeper-Offsets.html
ZK_OFFSETS_PATH_TEMPLATE = '/consumers/{group_id}/offsets/{topic}/{partition}'


class ZooKeeperClient:
    """
    Thin wrapper around a `KazooClient` that encapsulates the management of topics/partitions/offsets with ZooKeeper.
    """

    def __init__(self, zk_connect):
        self._client = KazooClient(zk_connect, timeout=10)

    def ensure_topics_and_partitions_exist(self, group_id, topics, partitions):
        for topic in topics:
            for partition in partitions:
                node_path = ZK_OFFSETS_PATH_TEMPLATE.format(group_id=group_id, topic=topic, partition=partition)
                node_stat = self._client.exists(node_path)
                if node_stat is None:
                    self._client.ensure_path(node_path)
                    self._client.set(node_path, b"0")

    def update_offsets(self, group_id, response):
        with self._client.transaction() as transaction:
            # 'tp' stands for 'topic-partition', because kafka-python groups records by topic and partition.
            # See: https://kafka-python.readthedocs.io/en/master/apidoc/KafkaConsumer.html#kafka.KafkaConsumer.poll
            for tp, records in iteritems(response):
                if not records:
                    # No new records obtained for this topic-partition, so no need to update the consumer offset.
                    continue

                new_consumer_offset_for_topic_and_partition = max(record.offset for record in records)

                topic = tp.topic
                partition = tp.partition
                path = ZK_OFFSETS_PATH_TEMPLATE.format(group_id=group_id, topic=topic, partition=partition)
                value = binary_type(new_consumer_offset_for_topic_and_partition)

                transaction.set_data(path, value)

    def __enter__(self):
        self._client.start()
        return self

    def __exit__(self, typ, exc, tb):
        self._client.stop()
