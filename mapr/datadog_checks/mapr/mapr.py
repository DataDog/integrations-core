# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import os
import re

from six import iteritems

from datadog_checks.base import AgentCheck

try:
    # This should be `confluent_kafka` but made by mapr!
    from confluent_kafka import Consumer, KafkaError
except ImportError as e:
    print("Unable to import library `confluent_kafka`, make sure it is installed and LD_LIBRARY_PATH is set correctly")
    raise e
    # on our infra you can run
    # export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/opt/mapr/lib:/usr/lib/jvm/java-1.8.0-openjdk-1.8.0.222.b10-0.el7_6.x86_64/jre/lib/amd64/server/  # noqa


class MaprCheck(AgentCheck):
    def __init__(self, name, init_config, agentConfig, instances):
        super(MaprCheck, self).__init__(name, init_config, agentConfig, instances)
        self._conn = None
        self.mapr_host = instances[0]['mapr_host']
        self.topic_path = instances[0]['topic_path']
        self.allowed_metrics = [re.compile('mapr.{}'.format(w)) for w in instances[0]['whitelist']]

        mapr_ticketfile_location = instances[0].get('mapr_ticketfile_location')
        if mapr_ticketfile_location:
            os.environ['MAPR_TICKETFILE_LOCATION'] = mapr_ticketfile_location
        elif not os.environ.get('MAPR_TICKETFILE_LOCATION'):
            self.log.debug(
                "MAPR_TICKETFILE_LOCATION environment variable not set, this may cause authentication issues"
            )

    def check(self, instance):
        tags = instance.get('tags', [])
        while True:
            m = self.conn.poll(timeout=1.0)
            if m is None:
                # Timed out, no more messages
                break
            if m.error() is None:
                # Metric received
                try:
                    kafka_metric = json.loads(m.value().decode('utf-8'))[0]
                    self.submit_metric(kafka_metric, tags)
                except Exception as e:
                    self.log.error("Received unexpected message %s, it wont be processed", m.value())
                    self.log.exception(e)
            elif m.error().code() != KafkaError._PARTITION_EOF:
                # Real error happened
                self.log.error(m.error())
                break
            else:
                self.log.debug(m.error())

    @staticmethod
    def get_stream_id(topic_name, rng=2):
        """To distribute load, all the topics are not in the same stream. Each topic named is hashed
        to obtain an id which is in turn the name of the stream"""
        h = 5381
        for c in topic_name:
            h = ((h << 5) + h) + ord(c)
        return abs(h % rng)

    @property
    def conn(self):
        if self._conn:
            return self._conn

        topic_name = self.mapr_host  # According to docs we should append the metric name.
        stream_id = MaprCheck.get_stream_id(topic_name, rng=2)

        topic_path = "{}:{}".format(os.path.join(self.topic_path, str(stream_id)), topic_name)
        self._conn = Consumer(
            {
                "group.id": "dd-agent",  # uniquely identify this consumer
                "enable.auto.commit": False  # important, we don't need to store the offset for this consumer,
                # and if we do it just once the mapr library has a bug which prevents reading from the head
            }
        )
        self._conn.subscribe([topic_path])
        return self._conn

    def should_collect_metric(self, metric_name):
        for reg in self.allowed_metrics:
            if re.match(reg, metric_name):
                return True
            else:
                self.log.debug("Ignoring non whitelisted metric %s", metric_name)

    def submit_metric(self, metric, additional_tags):
        metric_name = metric['metric']
        if self.should_collect_metric(metric_name):
            tags = ["{}:{}".format(k, v) for k, v in iteritems(metric['tags'])] + additional_tags
            if 'buckets' in metric:
                for bounds, value in metric['buckets'].items():
                    lower, upper = bounds.split(',')
                    self.submit_histogram_bucket(
                        metric_name, value, int(lower), int(upper), monotonic=True, hostname=self.hostname, tags=tags
                    )
            else:
                # No distinction between gauge and count metrics, this should be hardcoded metric by metric
                self.gauge(metric_name, metric['value'], tags=tags)
