# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging

from six import iteritems

from datadog_checks.base import ensure_bytes, ensure_unicode
from datadog_checks.checks import AgentCheck
from datadog_checks.ibm_mq.connection import Connection

from . import constants, errors
from .config import Config

try:
    import pymqi
except ImportError as pymqi_exception:
    pymqiException = pymqi_exception
    pymqi = None

log = logging.getLogger(__file__)


class IbmMqCheck(AgentCheck):
    def check(self, instance):
        if not pymqi:
            log.error("You need to install pymqi: {}".format(pymqiException))
            raise errors.PymqiException("You need to install pymqi: {}".format(pymqiException))

        config = Config(instance)
        config.check_properly_configured()
        connection = Connection(config)

        try:
            queue_manager = connection.get_queue_manager_pcf_connection()
            pcf_conn = pymqi.PCFExecute(queue_manager)
        except Exception as e:
            self.warning("cannot connect to queue manager: {}".format(e))
            self.service_check(constants.SYSTEM_CAN_CONNECT_SERVICE_CHECK, AgentCheck.CRITICAL, config.tags)
        else:
            self.service_check(constants.SYSTEM_CAN_CONNECT_SERVICE_CHECK, AgentCheck.OK, config.tags)
            self._submit_metrics(config, pcf_conn)
            queue_manager.disconnect()

    def _submit_metrics(self, config, pcf_conn):
        self._submit_queue_manager_stats(pcf_conn, config.tags)
        self._submit_channel_stats(config, pcf_conn, config.tags_no_channel)
        self._submit_queue_stats(config, pcf_conn)

    # ##################################################################################################################
    # QUEUE MANAGER STATS
    # ##################################################################################################################

    def _submit_queue_manager_stats(self, pcf_conn, tags):
        try:
            response = pcf_conn.MQCMD_INQUIRE_Q_MGR()
            for properties in response:
                self._submit_metrics_from_properties(
                    properties, metric_cat='queue_manager', metrics_map=constants.QUEUE_MANAGER_METRICS, tags=tags
                )

            response = pcf_conn.MQCMD_INQUIRE_Q_MGR_STATUS()
            for properties in response:
                self._submit_metrics_from_properties(
                    properties,
                    metric_cat='queue_manager',
                    metrics_map=constants.QUEUE_MANAGER_STATUS_METRICS,
                    tags=tags,
                )

            self.service_check(constants.QUEUE_MANAGER_SERVICE_CHECK, AgentCheck.OK, tags)
        except pymqi.MQMIError as e:
            self.warning("Error getting queue manager stats: {}".format(e))
            self.service_check(constants.QUEUE_MANAGER_SERVICE_CHECK, AgentCheck.CRITICAL, tags)

    # ##################################################################################################################
    # CHANNEL STATS
    # ##################################################################################################################

    def _submit_channel_stats(self, config, pcf_conn, tags):
        """ Submit channel stats (metrics and service checks)

        Note on service check: the service check is tagged with the channel search name.
        This mean that for channel search using `*`, the service check is tagged with `channel:*`.
        """
        discoverable = '*'
        for channel_search_name in [discoverable] + config.channels:
            service_check_tags = tags + ['channel:{}'.format(channel_search_name)]
            try:
                request_args = {pymqi.CMQCFC.MQCACH_CHANNEL_NAME: ensure_bytes(channel_search_name)}

                response = pcf_conn.MQCMD_INQUIRE_CHANNEL(request_args)
                for properties in response:
                    channel_tags = tags + self._build_extra_channel_tags(properties)
                    self._submit_metrics_from_properties(
                        properties, metric_cat='channel', metrics_map=constants.CHANNEL_METRICS, tags=channel_tags
                    )

                response = pcf_conn.MQCMD_INQUIRE_CHANNEL_STATUS(request_args)
                for properties in response:
                    channel_status_tags = tags + self._build_extra_channel_tags(properties)
                    self._submit_metrics_from_properties(
                        properties,
                        metric_cat='channel',
                        metrics_map=constants.CHANNEL_STATUS_METRICS,
                        tags=channel_status_tags,
                    )
                    self._submit_channel_status_metrics(properties, channel_status_tags)

                self.gauge('{}.channel.channels'.format(constants.METRIC_PREFIX), len(response), tags=tags)

                self.service_check(constants.CHANNEL_SERVICE_CHECK, AgentCheck.OK, service_check_tags)
            except pymqi.MQMIError as e:
                self.warning("Error getting channel stats: {}".format(e))
                self.service_check(constants.CHANNEL_SERVICE_CHECK, AgentCheck.CRITICAL, service_check_tags)

    def _submit_channel_status_metrics(self, properties, tags):
        channel_name = ensure_unicode(properties[pymqi.CMQCFC.MQCACH_CHANNEL_NAME]).strip()
        channel_status = properties[pymqi.CMQCFC.MQIACH_CHANNEL_STATUS]

        self._submit_channel_count(channel_name, channel_status, tags)
        self._submit_channel_status_check(channel_name, channel_status, tags)

    def _submit_channel_count(self, channel_name, channel_status, channel_tags):
        if channel_status not in constants.CHANNEL_STATUS_MAP:
            self.log.warning("Status `{}` not found for channel `{}`".format(channel_status, channel_name))
            channel_status = constants.STATUS_MQCHS_UNKNOWN

        for status, status_label in iteritems(constants.CHANNEL_STATUS_MAP):
            status_active = int(status == channel_status)
            self.gauge('ibm_mq.channel.count', status_active, tags=channel_tags + ["status:" + status_label])

    def _submit_channel_status_check(self, channel_name, channel_status, channel_tags):
        if channel_status in constants.SERVICE_CHECK_MAP:
            service_check_status = constants.SERVICE_CHECK_MAP[channel_status]
        else:
            self.log.warning("Status `{}` not found for channel `{}`".format(channel_status, channel_name))
            service_check_status = AgentCheck.UNKNOWN
        self.service_check(constants.CHANNEL_STATUS_SERVICE_CHECK, service_check_status, channel_tags)

    @staticmethod
    def _build_extra_channel_tags(properties):
        channel_tag = ensure_unicode(properties[pymqi.CMQCFC.MQCACH_CHANNEL_NAME]).strip()
        return ['channel:{}'.format(channel_tag)]

    # ##################################################################################################################
    # QUEUE STATS
    # ##################################################################################################################

    def _submit_queue_stats(self, config, pcf_conn):
        for queue_name in self._get_queues(config, pcf_conn):
            tags = self._get_queue_tags(config, queue_name)
            request_args = {pymqi.CMQC.MQCA_Q_NAME: ensure_bytes(queue_name)}

            try:
                response = pcf_conn.MQCMD_INQUIRE_Q(request_args)
                for properties in response:
                    self._submit_metrics_from_properties(
                        properties, metric_cat='queue', metrics_map=constants.QUEUE_METRICS, tags=tags
                    )

                response = pcf_conn.MQCMD_INQUIRE_Q_STATUS(request_args)
                for properties in response:
                    self._submit_metrics_from_properties(
                        properties, metric_cat='queue', metrics_map=constants.QUEUE_STATUS_METRICS, tags=tags
                    )

                response = pcf_conn.MQCMD_RESET_Q_STATS(request_args)
                for properties in response:
                    self._submit_metrics_from_properties(
                        properties, metric_cat='queue', metrics_map=constants.QUEUE_RESET_METRICS, tags=tags
                    )

                self.service_check(constants.QUEUE_SERVICE_CHECK, AgentCheck.OK, tags)
            except pymqi.MQMIError as e:
                self.warning("Error getting channel stats: {}".format(e))
                self.service_check(constants.QUEUE_SERVICE_CHECK, AgentCheck.CRITICAL, tags)

    def _get_queues(self, config, pcf_conn):
        return list(set(config.queues + self._discover_queues(config, pcf_conn)))

    def _discover_queues(self, config, pcf_conn):
        queues = []
        if config.auto_discover_queues:
            queues.extend(self._discover_queues_from_mq_pattern(pcf_conn, '*'))

        if config.queue_patterns:
            for pattern in config.queue_patterns:
                queues.extend(self._discover_queues_from_mq_pattern(pcf_conn, pattern))

        if config.queue_regex:
            if not queues:
                queues = self._discover_queues_from_mq_pattern(pcf_conn, '*')
            keep_queues = []
            for queue_pattern in config.queue_regex:
                for queue in queues:
                    if queue_pattern.match(queue):
                        keep_queues.append(queue)
            queues = keep_queues

        return queues

    def _discover_queues_from_mq_pattern(self, pcf_conn, mq_pattern):
        queues = []

        for queue_type in constants.SUPPORTED_QUEUE_TYPES:
            args = {pymqi.CMQC.MQCA_Q_NAME: ensure_bytes(mq_pattern), pymqi.CMQC.MQIA_Q_TYPE: queue_type}
            try:
                response = pcf_conn.MQCMD_INQUIRE_Q(args)
            except pymqi.MQMIError as e:
                self.warning("Error discovering queue: {}".format(e))
            else:
                for queue_info in response:
                    queue = queue_info[pymqi.CMQC.MQCA_Q_NAME]
                    if queue_info[pymqi.CMQC.MQIA_DEFINITION_TYPE] == pymqi.CMQC.MQQDT_PREDEFINED:
                        queues.append(ensure_unicode(queue).strip())

        return queues

    @staticmethod
    def _get_queue_tags(config, queue_name):
        queue_tags = config.tags + ["queue:{}".format(queue_name)]
        for regex, q_tags in config.queue_tag_re:
            if regex.match(queue_name):
                queue_tags.extend(q_tags)
        return queue_tags

    # ##################################################################################################################
    # SUBMIT METRICS FROM PCF RESPONSE PROPERTIES
    # ##################################################################################################################

    def _submit_metrics_from_properties(self, properties, metric_cat, metrics_map, tags):
        for metric_suffix, values in iteritems(metrics_map):
            mq_attr, metric_type = values
            metric_name = '{}.{}.{}'.format(constants.METRIC_PREFIX, metric_cat, metric_suffix)
            if callable(mq_attr):
                metric_value = mq_attr(properties)
                if metric_value is not None:
                    self._submit_metric_by_type(metric_type, metric_name, metric_value, tags)
            else:
                if mq_attr in properties:
                    metric_value = properties[mq_attr]
                    self._submit_metric_by_type(metric_type, metric_name, metric_value, tags)

    def _submit_metric_by_type(self, metric_type, metric_name, metric_value, tags):
        if metric_type == constants.GAUGE:
            self.gauge(metric_name, metric_value, tags=tags)
        elif metric_type == constants.RATE:
            self.rate(metric_name, metric_value, tags=tags)
        else:
            self.log.error("Invalid metric type (%s) for metric (%s):", metric_type, metric_name)

    # ##################################################################################################################
    # END
    # ##################################################################################################################@s
