# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.base import AgentCheck

from .client import LSFClient
from .config_models import ConfigMixin
from .processors import (
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
        cluster_name = self.instance.get("cluster_name")
        self.tags: list[str] = self.instance.get("tags", []) + [f"lsf_cluster_name:{cluster_name}"]
        self.check_initializations.append(self.initialize_processors)

    def initialize_processors(self):
        self.processors = [
            LsClustersProcessor(self.client, self.log, self.tags),
            LSHostsProcessor(self.client, self.log, self.tags),
            LsLoadProcessor(self.client, self.log, self.tags),
            BHostsProcessor(self.client, self.log, self.tags),
            BJobsProcessor(self.client, self.log, self.tags),
            BQueuesProcessor(self.client, self.log, self.tags),
            BSlotsProcessor(self.client, self.log, self.tags),
            GPULoadProcessor(self.client, self.log, self.tags),
            GPUHostsProcessor(self.client, self.log, self.tags),
        ]

    def check(self, _):
        _, err, exit_code = self.client.lsid()
        if exit_code == 0:
            self.gauge("can_connect", 1, self.tags)
        else:
            self.gauge("can_connect", 0, self.tags)
            self.log.error("Failed to get lsid output: %s. Skipping check", err)
            return

        for processor in self.processors:
            metrics = processor.process_metrics()
            for metric in metrics:
                self.gauge(metric.name, metric.value, tags=metric.tags)
