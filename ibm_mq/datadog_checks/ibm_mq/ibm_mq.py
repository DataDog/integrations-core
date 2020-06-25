# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any

from datadog_checks.base import AgentCheck
from datadog_checks.base.utils.subprocess_output import get_subprocess_output
from datadog_checks.ibm_mq.metrics import COUNT, GAUGE

from . import connection, errors
from .collectors import ChannelMetricCollector, QueueMetricCollector
from .config import IBMMQConfig

try:
    import pymqi
except ImportError as e:
    pymqiException = e
    pymqi = None


class IbmMqCheck(AgentCheck):
    SERVICE_CHECK = 'ibm_mq.can_connect'

    def __init__(self, *args, **kwargs):
        # type: (*Any, **Any) -> None
        super(IbmMqCheck, self).__init__(*args, **kwargs)
        self.config = IBMMQConfig(self.instance)

        if not pymqi:
            self.log.error("You need to install pymqi: %s", pymqiException)
            raise errors.PymqiException("You need to install pymqi: {}".format(pymqiException))

        self.queue_metric_collector = QueueMetricCollector(
            self.config, self.service_check, self.warning, self.send_metric, self.log
        )
        self.channel_metric_collector = ChannelMetricCollector(self.config, self.service_check, self.gauge, self.log)

    def check(self, _):
        try:
            queue_manager = connection.get_queue_manager_connection(self.config)
            self.service_check(self.SERVICE_CHECK, AgentCheck.OK, self.config.tags)
        except Exception as e:
            self.warning("cannot connect to queue manager: %s", e)
            self.service_check(self.SERVICE_CHECK, AgentCheck.CRITICAL, self.config.tags)
            return

        if self.is_metadata_collection_enabled():
            self._collect_metadata()

        try:
            self.channel_metric_collector.get_pcf_channel_metrics(queue_manager)
            self.queue_metric_collector.collect_queue_metrics(queue_manager)
        finally:
            queue_manager.disconnect()

    def send_metric(self, metric_type, metric_name, metric_value, tags):
        if metric_type in [GAUGE, COUNT]:
            getattr(self, metric_type)(metric_name, metric_value, tags=tags)
        else:
            self.log.warning("Unknown metric type `%s` for metric `%s`", metric_type, metric_name)

    def _collect_metadata(self):
        raw_version = self._get_version()
        if not raw_version:
            self.log.debug("Version not found in stdout")
            return
        self.log.debug('IBM MQ version: %s', raw_version)
        self.set_metadata('version', raw_version)

    def _get_version(self):

        cmd = self.instance.get("custom_version_cmd", "dspmqver")
        try:
            pc_out, pc_err, _ = get_subprocess_output(cmd, self.log, False)
        except OSError as e:
            self.log.debug("Error collecting IBM MQ version: %s", e)
            return None

        if pc_out is None:
            return None
        return self._parse_version(pc_out)

    @staticmethod
    def _parse_version(output):
        for line in output.splitlines():
            line = line.strip()
            if line.startswith("Version:"):
                return line.split()[1]
