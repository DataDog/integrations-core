# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import threading
import time

from confluent_kafka import Consumer as KafkaConsumer
from confluent_kafka import Producer as KafkaProducer

from .common import PARTITIONS, get_authentication_configuration

DEFAULT_SLEEP = 5
DEFAULT_TIMEOUT = 5


class StoppableThread(threading.Thread):
    def __init__(self, instance, sleep=DEFAULT_SLEEP, timeout=DEFAULT_TIMEOUT):
        super(StoppableThread, self).__init__()
        self.instance = instance
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
        producer = self.__get_producer_client()

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

                    # This topic is not consumed by `my_consumer`, and shouldn't show up in consumer.offset
                    producer.produce('unconsumed_topic', b"extra message 1", partition=partition)
                    producer.produce('unconsumed_topic', b"extra message 2", partition=partition)
                    producer.produce('unconsumed_topic', b"extra message 3", partition=partition)
                    producer.produce('unconsumed_topic', b"extra message 4", partition=partition)
                    producer.produce('unconsumed_topic', b"extra message 5", partition=partition)
                except Exception:
                    pass

            time.sleep(1)

    def __get_producer_client(self):
        config = {
            "bootstrap.servers": self.instance['kafka_connect_str'],
            "socket.timeout.ms": 1000,
        }
        config.update(get_authentication_configuration(self.instance))

        return KafkaProducer(config)


class Consumer(StoppableThread):
    def __init__(self, instance, topics, sleep=DEFAULT_SLEEP, timeout=DEFAULT_TIMEOUT):
        super(Consumer, self).__init__(instance, sleep=sleep, timeout=timeout)
        self.topics = topics

    def run(self):
        consumer = self.__get_consumer_client()
        consumer.subscribe(self.topics)

        while not self._shutdown_event.is_set():
            consumer.poll(timeout=1)

    def __get_consumer_client(self):
        config = {
            "bootstrap.servers": self.instance['kafka_connect_str'],
            "socket.timeout.ms": 1000,
            'group.id': 'my_consumer',
            'auto.offset.reset': 'earliest',
        }
        config.update(get_authentication_configuration(self.instance))
        return KafkaConsumer(config)
