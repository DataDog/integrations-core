# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Callable, Dict, List  # noqa: F401

from six import iteritems

from datadog_checks.base import AgentCheck, to_string
from datadog_checks.base.log import CheckLoggingAdapter  # noqa: F401

from .. import metrics
from ..config import IBMMQConfig  # noqa: F401

try:
    import pymqi
except ImportError as e:
    pymqiException = e
    pymqi = None
else:
    # Since pymqi is not be available/installed on win/macOS when running e2e,
    # we load the following constants only pymqi import succeed
    STATUS_MQCHS_UNKNOWN = -1
    CHANNEL_STATUS_NAME_MAPPING = {
        pymqi.CMQCFC.MQCHS_INACTIVE: "inactive",
        pymqi.CMQCFC.MQCHS_BINDING: "binding",
        pymqi.CMQCFC.MQCHS_STARTING: "starting",
        pymqi.CMQCFC.MQCHS_RUNNING: "running",
        pymqi.CMQCFC.MQCHS_STOPPING: "stopping",
        pymqi.CMQCFC.MQCHS_RETRYING: "retrying",
        pymqi.CMQCFC.MQCHS_STOPPED: "stopped",
        pymqi.CMQCFC.MQCHS_REQUESTING: "requesting",
        pymqi.CMQCFC.MQCHS_PAUSED: "paused",
        pymqi.CMQCFC.MQCHS_INITIALIZING: "initializing",
        STATUS_MQCHS_UNKNOWN: "unknown",
    }


class ChannelMetricCollector(object):
    CHANNEL_SERVICE_CHECK = 'ibm_mq.channel'
    CHANNEL_STATUS_SERVICE_CHECK = 'ibm_mq.channel.status'

    CHANNEL_COUNT_CHECK = 'ibm_mq.channel.count'

    def __init__(
        self,
        config,  # type: IBMMQConfig
        service_check,  # type: Callable
        gauge,  # type: Callable
        log,  # type: CheckLoggingAdapter
    ):
        self.config = config
        self.log = log
        self.service_check = service_check
        self.gauge = gauge

    def get_pcf_channel_metrics(self, queue_manager):
        discovered_channels = self._discover_channels(queue_manager)
        if discovered_channels:
            num_channels = len(discovered_channels)
            mname = '{}.channel.channels'.format(metrics.METRIC_PREFIX)
            self.gauge(mname, num_channels, tags=self.config.tags_no_channel, hostname=self.config.hostname)

            for channel_info in discovered_channels:
                channel_name = to_string(channel_info[pymqi.CMQCFC.MQCACH_CHANNEL_NAME]).strip()
                channel_tags = self.config.tags_no_channel + ["channel:{}".format(channel_name)]
                self._submit_metrics_from_properties(
                    channel_info, channel_name, metrics.channel_metrics(), channel_tags
                )

        # Check specific channels
        # If a channel is not discoverable, a user may want to check it specifically.
        # Specific channels are checked first to send channel metrics and `ibm_mq.channel` service checks
        # at the same time, but the end result is the same in any order.
        for channel in self.config.channels:
            self._submit_channel_status(queue_manager, channel, self.config.tags_no_channel)

        # Grab all the discoverable channels
        if self.config.auto_discover_channels:
            self._submit_channel_status(queue_manager, '*', self.config.tags_no_channel, self.config.channels)

    def _discover_channels(self, queue_manager):
        """Discover all channels"""
        args = {pymqi.CMQCFC.MQCACH_CHANNEL_NAME: pymqi.ensure_bytes('*')}
        pcf = None
        response = None
        try:
            pcf = pymqi.PCFExecute(
                queue_manager, response_wait_interval=self.config.timeout, convert=self.config.convert_endianness
            )
            response = pcf.MQCMD_INQUIRE_CHANNEL(args)
        except pymqi.MQMIError as e:
            # Don't warn if no messages, see:
            # https://github.com/dsuch/pymqi/blob/v1.12.0/docs/examples.rst#how-to-wait-for-multiple-messages
            if e.comp == pymqi.CMQC.MQCC_FAILED and e.reason == pymqi.CMQC.MQRC_NO_MSG_AVAILABLE:
                self.log.debug("There are no messages available for PCF channel")
            else:
                self.log.warning("Error getting CHANNEL stats %s", e)
        finally:
            if pcf is not None:
                pcf.disconnect()
        return response

    def _submit_channel_status(self, queue_manager, search_channel_name, tags, channels_to_skip=None):
        """Submit channel status

        Note: Error 3065 (MQRCCF_CHL_STATUS_NOT_FOUND) might indicate that the channel has not been used.
        More info: https://www.ibm.com/support/knowledgecenter/SSFKSJ_7.1.0/com.ibm.mq.doc/fm16690_.htm

        :param search_channel_name might contain wildcard characters
        """
        channels_to_skip = channels_to_skip or []
        search_channel_tags = tags + ["channel:{}".format(search_channel_name)]
        pcf = None
        try:
            args = {pymqi.CMQCFC.MQCACH_CHANNEL_NAME: pymqi.ensure_bytes(search_channel_name)}
            pcf = pymqi.PCFExecute(
                queue_manager, response_wait_interval=self.config.timeout, convert=self.config.convert_endianness
            )
            response = pcf.MQCMD_INQUIRE_CHANNEL_STATUS(args)
            self.service_check(
                self.CHANNEL_SERVICE_CHECK, AgentCheck.OK, search_channel_tags, hostname=self.config.hostname
            )
        except pymqi.MQMIError as e:
            if e.comp == pymqi.CMQC.MQCC_FAILED and e.reason == pymqi.CMQCFC.MQRCCF_CHL_STATUS_NOT_FOUND:
                self.service_check(
                    self.CHANNEL_SERVICE_CHECK,
                    AgentCheck.CRITICAL,
                    search_channel_tags,
                    message=str(e),
                    hostname=self.config.hostname,
                )
                self.log.debug("Channel status not found for channel %s: %s", search_channel_name, e)
            elif e.comp == pymqi.CMQC.MQCC_FAILED and e.reason == pymqi.CMQC.MQRC_NO_MSG_AVAILABLE:
                self.service_check(
                    self.CHANNEL_SERVICE_CHECK,
                    AgentCheck.UNKNOWN,
                    search_channel_tags,
                    message=str(e),
                    hostname=self.config.hostname,
                )
                self.log.debug("There are no messages available for channel %s", search_channel_name)
            else:
                self.service_check(
                    self.CHANNEL_SERVICE_CHECK,
                    AgentCheck.CRITICAL,
                    search_channel_tags,
                    message=str(e),
                    hostname=self.config.hostname,
                )
                self.log.warning("Error getting CHANNEL status for channel %s: %s", search_channel_name, e)
        else:
            for channel_info in response:
                channel_name = to_string(channel_info[pymqi.CMQCFC.MQCACH_CHANNEL_NAME]).strip()
                if channel_name in channels_to_skip:
                    continue
                channel_tags = tags + ["channel:{}".format(channel_name)]

                self._submit_metrics_from_properties(
                    channel_info, channel_name, metrics.channel_status_metrics(), channel_tags
                )

                channel_status = channel_info[pymqi.CMQCFC.MQIACH_CHANNEL_STATUS]
                self._submit_channel_count(channel_name, channel_status, channel_tags)
                self._submit_status_check(channel_name, channel_status, channel_tags)
        finally:
            if pcf is not None:
                pcf.disconnect()

    def _submit_metrics_from_properties(self, channel_info, channel_name, metrics_map, tags):
        # type: (Dict, str, Dict[str, int], List[str] ) -> None
        for metric_name, pymqi_type in iteritems(metrics_map):
            metric_full_name = '{}.channel.{}'.format(metrics.METRIC_PREFIX, metric_name)
            if pymqi_type not in channel_info:
                self.log.debug("metric '%s' not found in channel: %s", metric_name, channel_name)
                continue
            metric_value = int(channel_info[pymqi_type])
            self.gauge(metric_full_name, metric_value, tags=tags, hostname=self.config.hostname)

    def _submit_channel_count(self, channel_name, channel_status, channel_tags):
        if channel_status not in CHANNEL_STATUS_NAME_MAPPING:
            self.log.warning("Status `%s` not found for channel `%s`", channel_status, channel_name)
            channel_status = STATUS_MQCHS_UNKNOWN

        for status, status_label in iteritems(CHANNEL_STATUS_NAME_MAPPING):
            status_active = int(status == channel_status)
            self.gauge(
                self.CHANNEL_COUNT_CHECK,
                status_active,
                tags=channel_tags + ["status:" + status_label],
                hostname=self.config.hostname,
            )

    def _submit_status_check(self, channel_name, channel_status, channel_tags):
        if channel_status in self.config.channel_status_mapping:
            service_check_status = self.config.channel_status_mapping[channel_status]
        else:
            self.log.warning("Status `%s` not found for channel `%s`", channel_status, channel_name)
            service_check_status = AgentCheck.UNKNOWN
        self.service_check(
            self.CHANNEL_STATUS_SERVICE_CHECK, service_check_status, channel_tags, hostname=self.config.hostname
        )
