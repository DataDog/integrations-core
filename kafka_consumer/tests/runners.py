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
                    # Define protobuf schema for messages
                    # proto_schema = """
                    # syntax = "proto3";
                    #
                    # message Person {
                    #     string name = 1;
                    #     int32 age = 2;
                    #     double transaction_amount = 3;
                    #     string currency = 4;
                    # }
                    # """
                    # print("producing protobuf messages")
                    #
                    # # Import protobuf libraries
                    # from google.protobuf import descriptor_pb2
                    # from google.protobuf.descriptor_pool import DescriptorPool
                    # from google.protobuf.message_factory import MessageFactory
                    # print("import done")
                    #
                    # # Create descriptor and message factory
                    # pool = DescriptorPool()
                    # desc = descriptor_pb2.FileDescriptorProto()
                    # desc.name = "person.proto"
                    # desc.package = "test"
                    # desc.syntax = "proto3"
                    #
                    # message = desc.message_type.add()
                    # message.name = "Person"
                    #
                    # # Add fields
                    # name_field = message.field.add()
                    # name_field.name = "name"
                    # name_field.number = 1
                    # name_field.type = descriptor_pb2.FieldDescriptorProto.TYPE_STRING
                    # name_field.label = descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL
                    #
                    # age_field = message.field.add()
                    # age_field.name = "age"
                    # age_field.number = 2
                    # age_field.type = descriptor_pb2.FieldDescriptorProto.TYPE_INT32
                    # age_field.label = descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL
                    #
                    # amount_field = message.field.add()
                    # amount_field.name = "transaction_amount"
                    # amount_field.number = 3
                    # amount_field.type = descriptor_pb2.FieldDescriptorProto.TYPE_DOUBLE
                    # amount_field.label = descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL
                    #
                    # currency_field = message.field.add()
                    # currency_field.name = "currency"
                    # currency_field.number = 4
                    # currency_field.type = descriptor_pb2.FieldDescriptorProto.TYPE_STRING
                    # currency_field.label = descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL
                    #
                    # pool.Add(desc)
                    # factory = MessageFactory(pool)
                    # Person = factory.GetPrototype(pool.FindMessageTypeByName("Person"))
                    #
                    # # Create and serialize protobuf messages
                    # marvel_messages = [
                    #     {"name": "Peter Parker", "age": 18, "transaction_amount": 123.0, "currency": "dollar"},
                    #     {"name": "Bruce Banner", "age": 45, "transaction_amount": 456.0, "currency": "dollar"},
                    #     {"name": "Tony Stark", "age": 35, "transaction_amount": 789.0, "currency": "dollar"},
                    #     {"name": "Johnny Blaze", "age": 30, "transaction_amount": 321.0, "currency": "dollar"},
                    #     {"name": "BoomShakalaka", "age": 25, "transaction_amount": 654.0, "currency": "dollar"}
                    # ]
                    #
                    # dc_messages = [
                    #     {"name": "Diana Prince", "age": 28, "transaction_amount": 987.0, "currency": "dollar"},
                    #     {"name": "Bruce Wayne", "age": 32, "transaction_amount": 147.0, "currency": "dollar"},
                    #     {"name": "Clark Kent", "age": 29, "transaction_amount": 258.0, "currency": "dollar"},
                    #     {"name": "Arthur Curry", "age": 33, "transaction_amount": 369.0, "currency": "dollar"},
                    #     {"name": "ShakalakaBoom", "age": 27, "transaction_amount": 741.0, "currency": "dollar"}
                    # ]
                    #
                    # # Produce Marvel messages
                    # for msg in marvel_messages:
                    #     person = Person()
                    #     person.name = msg["name"]
                    #     person.age = msg["age"]
                    #     person.transaction_amount = msg["transaction_amount"]
                    #     person.currency = msg["currency"]
                    #     producer.produce('marvel', person.SerializeToString(), partition=partition)
                    #
                    # # Produce DC messages
                    # for msg in dc_messages:
                    #     person = Person()
                    #     person.name = msg["name"]
                    #     person.age = msg["age"]
                    #     person.transaction_amount = msg["transaction_amount"]
                    #     person.currency = msg["currency"]
                    #     producer.produce('dc', person.SerializeToString(), partition=partition)
                    producer.produce('marvel', b'{"name": "Peter Parker", "age": 18, "transaction_amount": 123, "currency": "dollar"}', partition=partition)
                    producer.produce('marvel', b'{"name": "Bruce Banner", "age": 45, "transaction_amount": 456, "currency": "dollar"}', partition=partition)
                    producer.produce('marvel', b'{"name": "Tony Stark", "age": 35, "transaction_amount": 789, "currency": "dollar"}', partition=partition)
                    producer.produce('marvel', b'{"name": "Johnny Blaze", "age": 30, "transaction_amount": 321, "currency": "dollar"}', partition=partition)
                    producer.produce('marvel', b'{"name": "BoomShakalaka", "age": 25, "transaction_amount": 654, "currency": "dollar"}', partition=partition)
                    producer.produce('marvel', b'{"name": "Steve Rogers", "age": 100, "transaction_amount": 555, "currency": "dollar"}', partition=partition)
                    producer.produce('marvel', b'{"name": "Thor Odinson", "age": 1500, "transaction_amount": 888, "currency": "dollar"}', partition=partition)
                    producer.produce('marvel', b'{"name": "Natasha Romanoff", "age": 35, "transaction_amount": 444, "currency": "dollar"}', partition=partition)
                    producer.produce('marvel', b'{"name": "Clint Barton", "age": 40, "transaction_amount": 333, "currency": "dollar"}', partition=partition)
                    producer.produce('marvel', b'{"name": "Doctor Strange", "age": 42, "transaction_amount": 777, "currency": "dollar"}', partition=partition)
                    producer.produce('marvel', b'{"name": "Black Panther", "age": 35, "transaction_amount": 999, "currency": "dollar"}', partition=partition)
                    producer.produce('marvel', b'{"name": "Carol Danvers", "age": 45, "transaction_amount": 666, "currency": "dollar"}', partition=partition)
                    producer.produce('marvel', b'{"name": "Scott Lang", "age": 45, "transaction_amount": 222, "currency": "dollar"}', partition=partition)
                    producer.produce('marvel', b'{"name": "Wanda Maximoff", "age": 30, "transaction_amount": 888, "currency": "dollar"}', partition=partition)
                    producer.produce('marvel', b'{"name": "Vision", "age": 3, "transaction_amount": 111, "currency": "dollar"}', partition=partition)
                    producer.produce('marvel', b'{"name": "\xe6\x98\x9f\xe7\x88\xb5 Peter Quill", "age": 38, "transaction_amount": 444, "currency": "dollar"}', partition=partition)
                    producer.produce('marvel', b'{"name": "Gamora", "age": 29, "transaction_amount": 555, "currency": "dollar"}', partition=partition)
                    producer.produce('marvel', b'{"name": "Drax", "age": 40, "transaction_amount": 333, "currency": "dollar"}', partition=partition)
                    producer.produce('marvel', b'{"name": "Rocket Raccoon", "age": 8, "transaction_amount": 777, "currency": "dollar"}', partition=partition)
                    producer.produce('marvel', b'{"name": "Groot", "age": 5, "transaction_amount": 222, "currency": "dollar"}', partition=partition)
                    producer.produce('marvel', b'{"name": "Nick Fury", "age": 70, "transaction_amount": 888, "currency": "dollar"}', partition=partition)
                    producer.produce('marvel', b'{"name": "Loki", "age": 1054, "transaction_amount": 666, "currency": "dollar"}', partition=partition)
                    producer.produce('marvel', b'{"name": "Deadpool", "age": 35, "transaction_amount": 444, "currency": "dollar"}', partition=partition)
                    producer.produce('marvel', b'{"name": "Professor X", "age": 65, "transaction_amount": 999, "currency": "dollar"}', partition=partition)
                    producer.produce('marvel', b'{"name": "Wolverine", "age": 137, "transaction_amount": 777, "currency": "dollar"}', partition=partition)
                    producer.produce('dc', b'{"name": "Diana Prince", "age": 28, "transaction_amount": 987, "currency": "dollar"}', partition=partition)
                    producer.produce('dc', b'{"name": "Bruce Wayne", "age": 32, "transaction_amount": 147, "currency": "dollar"}', partition=partition)
                    producer.produce('dc', b'{"name": "Clark Kent", "age": 29, "transaction_amount": 258, "currency": "dollar"}', partition=partition)
                    producer.produce('dc', b'{"name": "Arthur Curry", "age": 33, "transaction_amount": 369, "currency": "dollar"}', partition=partition)
                    producer.produce('dc', b'{"name": "ShakalakaBoom", "age": 27, "transaction_amount": 741, "currency": "dollar"}', partition=partition)

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
