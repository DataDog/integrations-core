# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy
import json
import os
import re

from six import iteritems

from datadog_checks.base import AgentCheck, ensure_unicode, is_affirmative
from datadog_checks.base.errors import CheckException

from .common import ALLOWED_METRICS, COUNT_METRICS, GAUGE_METRICS, HISTOGRAM_METRICS, MONOTONIC_COUNTER_METRICS
from .utils import get_fqdn, get_stream_id_for_topic

try:
    # This is not the regular `confluent_kafka` but rather the custom version made by MapR
    # that you can install with "pip install mapr-streams-python"
    import confluent_kafka as ck

    ck_import_error = None
except ImportError as e:
    ck = None
    ck_import_error = e


DEFAULT_STREAM_PATH = "/var/mapr/mapr.monitoring/metricstreams"
METRICS_SUBMITTED_METRIC_NAME = "mapr.metrics.submitted"
SERVICE_CHECK = "mapr.can_connect"
TICKET_LOCATION_ENV_VAR = 'MAPR_TICKETFILE_LOCATION'

"""
All mapr metrics go through a Stream topic (similar to a Kafka topic) and are consumed by OpenTSDB, a timeseries
database.
All the metrics are distributed over multiple topics, one for each host. This way, the check instance can subscribe
to the topic relevant to the current host and consume everything.

Note: The MapR documentation https://mapr.com/docs/61/AdministratorGuide/spyglass-on-streams.html states that
there is one topic per host per metric name. This is no longer true starting with 6.1+, there is only one topic per
host now. To support older versions of MapR, the check should be updated to subscribe those multiple topics.
"""


class MaprCheck(AgentCheck):
    def __init__(self, name, init_config, instances):
        super(MaprCheck, self).__init__(name, init_config, instances)
        self._conn = None
        self.hostname = self.instance.get('hostname', get_fqdn())
        self.streams_count = self.instance.get('streams_count', 1)
        self.topic_path = "{stream_path}/{stream_id}:{topic_name}".format(
            stream_path=self.instance.get('stream_path', DEFAULT_STREAM_PATH),
            stream_id=get_stream_id_for_topic(self.hostname, rng=self.streams_count),
            topic_name=self.hostname,
        )
        self.allowed_metrics = [re.compile(w) for w in self.instance.get('metric_whitelist', [])]
        self.custom_tags = self.instance.get('tags', [])
        self.has_ever_submitted_metrics = False
        self._disable_legacy_cluster_tag = is_affirmative(self.instance.get('disable_legacy_cluster_tag', False))
        self.auth_ticket = self.instance.get('ticket_location', os.environ.get(TICKET_LOCATION_ENV_VAR))

        if not self.auth_ticket:
            self.log.warning(
                "Neither `ticket_location` (in the config.yaml) or the %s environment variable is set. This will"
                "cause authentication issues if your cluster requires authenticated requests.",
                TICKET_LOCATION_ENV_VAR,
            )
        elif not os.access(self.auth_ticket, os.R_OK):
            raise CheckException(
                "MapR authentication ticket located at %s is not readable by the dd-agent "
                "user. Please update the file permissions.",
                self.auth_ticket,
            )
        else:
            os.environ[TICKET_LOCATION_ENV_VAR] = self.auth_ticket

    def check(self, _):
        if ck is None:
            raise CheckException(
                "confluent_kafka was not imported correctly, make sure the library is installed and that you've "
                "set LD_LIBRARY_PATH correctly. Please refer to datadog documentation for more details. Error is %s"
                % ck_import_error
            )

        try:
            conn = self.get_connection()
        except Exception:
            self.service_check(
                SERVICE_CHECK, AgentCheck.CRITICAL, self.custom_tags + ['topic:{}'.format(self.topic_path)]
            )
            raise
        else:
            self.service_check(SERVICE_CHECK, AgentCheck.OK, self.custom_tags + ['topic:{}'.format(self.topic_path)])

        submitted_metrics_count = 0

        while True:
            # Collecting one message at a time has no impact on performance because the library
            # batches data. Most calls to `poll` won't initiate a I/O connection.
            msg = conn.poll(timeout=0.5)
            if msg is None:
                # Timed out, no more messages
                break

            if msg.error() is None:
                # Metric received
                submitted_metrics_count += self._process_metric(msg)
            else:
                self._process_error(msg.error())

        if not self.has_ever_submitted_metrics:
            # The integration has never found any metric so far
            if submitted_metrics_count:
                self.has_ever_submitted_metrics = True
                self.log.info("The integration collected metrics for the first time in topic %s", self.topic_path)
            else:
                self.log.error(
                    "The integration was not yet able to collect any MapR metric in topic %s. If this error continues "
                    "after a few check runs, double-check the existence of the stream and the topic using "
                    "maprcli as well as the permissions on this topic.",
                    self.topic_path,
                )

        if submitted_metrics_count:
            self.gauge(METRICS_SUBMITTED_METRIC_NAME, submitted_metrics_count, self.custom_tags)

    def _process_metric(self, msg):
        try:
            metric = json.loads(ensure_unicode(msg.value()))[0]
            metric_name = metric['metric']
            if self.should_collect_metric(metric_name):
                # Will sometimes submit the same metric multiple time, but because it's only
                # gauges and monotonic_counter that's fine.
                self.submit_metric(metric)
                return 1
            return 0
        except Exception as e:
            self.log.warning("Received unexpected message %s, won't be processed", msg.value())
            self.log.exception(e)

    def _process_error(self, error_msg):
        if error_msg.code() == ck.KafkaError.TOPIC_AUTHORIZATION_FAILED:
            if self.auth_ticket:
                raise CheckException(
                    "The user impersonated using the ticket %s does not have the 'consume' permission on topic %s. "
                    "Please update the stream permissions." % (self.auth_ticket, self.topic_path)
                )
            else:
                raise CheckException(
                    "dd-agent user could not consume topic '%s'. Please ensure that:\n"
                    "\t* This is a non-secure cluster, otherwise a user ticket is required.\n"
                    "\t* The dd-agent user has the 'consume' permission on topic %s or "
                    "impersonation is correctly configured." % (self.topic_path, self.topic_path)
                )
        elif error_msg.code() != ck.KafkaError._PARTITION_EOF:
            # Partition EOF is expected anytime we reach the end of one partition in the topic.
            # This is expected at least once per partition per check run.
            raise CheckException(error_msg)

    def get_connection(self):
        if self._conn:
            # confluent_kafka takes care of recreating the connection if anything goes wrong.
            return self._conn

        self._conn = ck.Consumer(
            {
                "group.id": "dd-agent",  # uniquely identify this consumer
                "enable.auto.commit": False,  # important, do not store the offset for this consumer,
                # if we do it just once the mapr library has a bug/feature which prevents resetting it to the head
            }
        )
        self._conn.subscribe([self.topic_path])
        return self._conn

    def should_collect_metric(self, metric_name):
        if metric_name not in ALLOWED_METRICS:
            # Metric is not part of datadog allowed list
            return False
        if not self.allowed_metrics:
            # No filter specified, allow everything
            return True

        for reg in self.allowed_metrics:
            if re.match(reg, metric_name):
                # Metric matched one pattern
                return True

        self.log.debug("Ignoring non whitelisted metric: %s", metric_name)
        return False

    def submit_metric(self, metric):
        metric_name = metric['metric']
        tags = copy.deepcopy(self.custom_tags)
        for k, v in iteritems(metric['tags']):
            if k == 'clustername':
                tags.append("{}:{}".format('mapr_cluster', v))
                if not self._disable_legacy_cluster_tag:
                    self._log_deprecation(k, 'mapr_cluster')
                    tags.append("{}:{}".format(k, v))
            elif k == 'clusterid':
                tags.append("{}:{}".format('mapr_cluster_id', v))
                if not self._disable_legacy_cluster_tag:
                    self._log_deprecation(k, 'mapr_cluster_id')
                    tags.append("{}:{}".format(k, v))
            else:
                tags.append("{}:{}".format(k, v))

        if 'buckets' in metric and metric_name in HISTOGRAM_METRICS:
            for bounds, value in metric['buckets'].items():
                lower, upper = bounds.split(',')
                self.submit_histogram_bucket(
                    metric_name, value, int(lower), int(upper), monotonic=False, hostname=self.hostname, tags=tags
                )
        else:
            if metric_name in GAUGE_METRICS:
                self.gauge(metric_name, metric['value'], tags=tags)
            elif metric_name in MONOTONIC_COUNTER_METRICS:
                self.monotonic_count(metric_name, metric['value'], tags=tags)
            elif metric_name in COUNT_METRICS:
                self.count(metric_name, metric['value'], tags=tags)
