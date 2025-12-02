# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.base import AgentCheck

from .client import LSFClient
from .config_models import ConfigMixin
from .processors import (
    BadminPerfmonProcessor,
    BHostsProcessor,
    BJobsProcessor,
    BQueuesProcessor,
    BSlotsProcessor,
    GPUHostsProcessor,
    GPULoadProcessor,
    LsClustersProcessor,
    LSFMetricsProcessor,
    LSHostsProcessor,
    LsLoadProcessor,
)


class IbmSpectrumLsfCheck(AgentCheck, ConfigMixin):
    __NAMESPACE__ = 'ibm_spectrum_lsf'

    def __init__(self, name, init_config, instances):
        super(IbmSpectrumLsfCheck, self).__init__(name, init_config, instances)
        self.client: LSFClient = LSFClient(self.log)
        self.processors: list[LSFMetricsProcessor] = []
        self.tags: list[str] = []
        self.check_initializations.append(self.parse_config)
        self.check_initializations.append(self.initialize_processors)

    def parse_config(self):
        self.tags = list[str](self.config.tags or []) + [f"lsf_cluster_name:{self.config.cluster_name}"]

    def initialize_processors(self) -> None:
        self.processors = [
            LsClustersProcessor(self.client, self.config, self.log, self.tags),
            LSHostsProcessor(self.client, self.config, self.log, self.tags),
            LsLoadProcessor(self.client, self.config, self.log, self.tags),
            BHostsProcessor(self.client, self.config, self.log, self.tags),
            BJobsProcessor(self.client, self.config, self.log, self.tags),
            BQueuesProcessor(self.client, self.config, self.log, self.tags),
            BSlotsProcessor(self.client, self.config, self.log, self.tags),
            GPULoadProcessor(self.client, self.config, self.log, self.tags),
            GPUHostsProcessor(self.client, self.config, self.log, self.tags),
            BadminPerfmonProcessor(self.client, self.config, self.log, self.tags),
        ]

    def check(self, instance):
        _, err, exit_code = self.client.lsid()
        if exit_code == 0:
            self.gauge("can_connect", 1, self.tags)
        else:
            self.gauge("can_connect", 0, self.tags)
            self.log.error("Failed to get lsid output: %s. Skipping check", err)
            return

        for processor in self.processors:
            if processor.should_run():
                metrics = processor.process_metrics()
                for metric in metrics:
                    self.gauge(metric.name, metric.value, tags=metric.tags)
            else:
                self.log.trace("Skipping %s metrics; excluded in configuration.", processor.name)

    def cancel(self):
        if self.config.metric_sources and 'badmin_perfmon' in self.config.metric_sources:
            self.client.badmin_perfmon_stop()
