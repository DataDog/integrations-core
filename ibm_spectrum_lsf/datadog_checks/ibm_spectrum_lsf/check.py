# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.base import AgentCheck

from .client import LSFClient
from .common import BHOSTS, BJOBS, BQUEUES, BSLOTS, LSCLUSTERS, LSHOSTS, LSLOAD
from .config_models import ConfigMixin


class IbmSpectrumLsfCheck(AgentCheck, ConfigMixin):
    __NAMESPACE__ = 'ibm_spectrum_lsf'

    def __init__(self, name, init_config, instances):
        super(IbmSpectrumLsfCheck, self).__init__(name, init_config, instances)
        self.client = LSFClient(self.log)
        self.check_initializations.append(self.parse_config)

    def parse_config(self):
        self.tags = self.config.tags if self.config.tags else []
        self.tags.append(f"lsf_cluster_name:{self.config.cluster_name}")

    def process_tags(self, tag_mapping, line_data):
        tags = []
        for tag in tag_mapping:
            val = line_data[tag['id']]
            key = tag['name']
            tags.append(f"{key}:{val}")

        return tags

    def submit_metrics(self, prefix, metric_mapping, line_data, tags):
        for metric in metric_mapping:
            val = line_data[metric['id']]
            transformer = metric['transform']
            val = transformer(val)

            name = metric['name']
            self.gauge(f"{prefix}.{name}", val, tags=self.tags + tags)

    def collect_metrics_from_command(self, client_func, mapping):
        output, err, exit_code = client_func()
        cmd_name = mapping['name']
        if exit_code != 0:
            self.log.error("Failed to get %s output: %s", cmd_name, err)
            return

        output_lines = output.strip().split('\n')
        headers = output_lines.pop(0)
        delimiter = '|' if '|' in output else None
        if len(headers.split(delimiter)) != mapping.get('expected_columns'):
            (
                self.log.warning(
                    "Skipping %s metrics; unexpected return value: %s columns", cmd_name, len(headers.split(delimiter))
                ),
            )
            return

        self.log.debug("Processing %s metrics", cmd_name)
        for line in output_lines:
            line_data = [line.strip() for line in line.split(delimiter)]
            tags = self.process_tags(mapping.get('tags', []), line_data)
            self.submit_metrics(mapping.get('prefix'), mapping.get('metrics'), line_data, tags)

    def collect_clusters(self):
        """
        CLUSTER_NAME   STATUS   MASTER_HOST                          ADMIN    HOSTS  SERVERS
        cluster1       ok       ip-11-21-111-198.ec2.internal     ec2-user        1        1
        """
        self.collect_metrics_from_command(self.client.lsclusters, LSCLUSTERS)

    def collect_bhosts(self):
        """
        HOST_NAME          STATUS          JL/U    MAX  NJOBS    RUN  SSUSP  USUSP    RSV
        ip-10-11-220-188.ec2.internal ok              -      4      0      0      0      0      0
        """
        self.collect_metrics_from_command(self.client.bhosts, BHOSTS)

    def collect_lshosts(self):
        """
        HOST_NAME                     type    model     cpuf     ncpus    maxmem     maxswp     server  nprocs   ncores   nthreads maxtmp
        ip-11-21-111-198.ec2.internal X86_64  Intel_E5  12.50    4        16030M         -      Yes     1        4        1        81886M
        """  # noqa: E501
        self.collect_metrics_from_command(self.client.lshosts, LSHOSTS)

    def collect_lsload(self):
        """
        HOST_NAME               status  r15s   r1m  r15m   ut    pg    io  ls    it   tmp   swp   mem
        ip-11-21-111-198.ec2.internal     ok   0.1   0.0   0.0   0%   0.0     1   1     4   71G    0M
        """
        self.collect_metrics_from_command(self.client.lsload, LSLOAD)

    def collect_bslots(self):
        """
        SLOTS          RUNTIME
        2              UNLIMITED
        """
        self.collect_metrics_from_command(self.client.bslots, BSLOTS)

    def collect_bqueues(self):
        """
        QUEUE_NAME      PRIO STATUS          MAX JL/U JL/P JL/H NJOBS  PEND   RUN  SUSP
        admin            50  Open:Active       -    -    -    -     0     0     0     0
        owners           43  Open:Active       -    -    -    -     0     0     0     0
        priority         43  Open:Active       -    -    -    -     0     0     0     0
        night            40  Open:Active       -    -    -    -     0     0     0     0
        short            35  Open:Active       -    -    -    -     0     0     0     0
        normal           30  Open:Active       -    -    -    -     0     0     0     0
        interactive      30  Open:Active       -    -    -    -     0     0     0     0
        idle             20  Open:Active       -    -    -    -     0     0     0     0
        """
        self.collect_metrics_from_command(self.client.bqueues, BQUEUES)

    def collect_bjobs(self):
        """
        JOBID|STAT|QUEUE|FROM_HOST|EXEC_HOST |RUN_TIME|CPU_USED|MEM|TIME_LEFT|SWAP|IDLE_FACTOR|%COMPLETE
        65|PEND|normal|ip-10-11-220-188.ec2.internal | -|0 second(s)|-|-|-|-|-|-
        """
        self.collect_metrics_from_command(self.client.bjobs, BJOBS)

    def check(self, _):
        _, err, exit_code = self.client.lsid()
        if exit_code == 0:
            self.gauge("can_connect", 1, self.tags)
        else:
            self.gauge("can_connect", 0, self.tags)
            self.log.error("Failed to get lsid output: %s. Skipping check", err)
            return

        self.client.start_monitoring(self.config.min_collection_interval)
        self.collect_clusters()
        self.collect_bhosts()
        self.collect_lshosts()
        self.collect_lsload()
        self.collect_bslots()
        self.collect_bqueues()
        self.collect_bjobs()
