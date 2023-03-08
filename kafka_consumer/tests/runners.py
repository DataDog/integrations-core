# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import threading
import time

from confluent_kafka import Consumer as KafkaConsumer
from confluent_kafka import Producer as KafkaProducer

from .common import KAFKA_CONNECT_STR, PARTITIONS

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
        producer = KafkaProducer({'bootstrap.servers': KAFKA_CONNECT_STR})

        iteration = 0
        while not self._shutdown_event.is_set():
            for partition in PARTITIONS:
                try:
                    producer.produce('marvel', b"Peter Parker", partition=partition)
                    producer.produce('marvel', b"Bruce Banner", partition=partition)
                    producer.produce('marvel', b"Tony Stark", partition=partition)
                    producer.produce('marvel', b"Johhny Blaze", partition=partition)
                    producer.produce('marvel', b"\xc2BoomShakalaka", partition=partition)
                    producer.produce('dc', b"Diana Prince", partition=partition)
                    producer.produce('dc', b"Bruce Wayne", partition=partition)
                    producer.produce('dc', b"Clark Kent", partition=partition)
                    producer.produce('dc', b"Arthur Curry", partition=partition)
                    producer.produce('dc', b"\xc2ShakalakaBoom", partition=partition)
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
        consumer = KafkaConsumer(
            {'bootstrap.servers': self.kafka_connect_str, 'group.id': 'my_consumer', 'auto.offset.reset': 'earliest'}
        )
        consumer.subscribe(self.topics)

        iteration = 0
        while not self._shutdown_event.is_set():
            consumer.poll(timeout=500)
            iteration += 1
