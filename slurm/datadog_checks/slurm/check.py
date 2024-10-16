# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import subprocess
from datetime import timedelta
from typing import Any  # noqa: F401

from datadog_checks.base import AgentCheck  # noqa: F401

from .config_models import ConfigMixin
from .constants import (
    GPU_PARAMS,
    NODE_MAP,
    PARTITION_MAP,
    SACCT_MAP,
    SACCT_PARAMS,
    SDIAG_MAP,
    SINFO_ADDITIONAL_NODE_PARAMS,
    SINFO_NODE_PARAMS,
    SINFO_PARTITION_PARAMS,
    SQUEUE_MAP,
    SQUEUE_PARAMS,
    SSHARE_MAP,
    SSHARE_PARAMS,
)


def get_subprocess_out(cmd):
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout, result.stderr, result.returncode


def parse_duration(time_str):
    hours, minutes, seconds = map(int, time_str.split(':'))
    duration = timedelta(hours=hours, minutes=minutes, seconds=seconds)
    total_seconds = duration.total_seconds()

    return total_seconds


class SlurmCheck(AgentCheck, ConfigMixin):

    # This will be the prefix of every metric and service check the integration sends
    __NAMESPACE__ = 'slurm'

    def get_slurm_command(self, cmd_name, default_path, params):
        cmd_path = self.instance.get(f'{cmd_name}_path', os.path.join(self.slurm_binaries_path, default_path))
        return [cmd_path] + params

    def __init__(self, name, init_config, instances):
        super(SlurmCheck, self).__init__(name, init_config, instances)

        # Binary paths
        self.slurm_binaries_path = self.init_config.get('slurm_binaries_path', '/usr/bin/')
        self.sinfo_partition_cmd = self.get_slurm_command('sinfo', 'sinfo', SINFO_PARTITION_PARAMS)
        self.squeue_cmd = self.get_slurm_command('squeue', 'squeue', SQUEUE_PARAMS)
        self.sacct_cmd = self.get_slurm_command('sacct', 'sacct', SACCT_PARAMS)
        self.sdiag_cmd = self.get_slurm_command('sdiag', 'sdiag', [])
        self.sshare_cmd = self.get_slurm_command('sshare', 'sshare', SSHARE_PARAMS)
        self.tags = self.instance.get('tags', [])

        # Metric and Tag configuration
        self.gpu_stats = self.instance.get('gpu_stats', False)
        self.sinfo_collection_level = self.instance.get('sinfo_collection_level', 1)

        if self.gpu_stats:
            self.sinfo_partition_cmd[-1] += GPU_PARAMS

        if self.sinfo_collection_level > 1:
            self.sinfo_node_cmd = self.get_slurm_command('sinfo', 'sinfo', SINFO_NODE_PARAMS)
            if self.sinfo_collection_level > 2:
                self.sinfo_node_cmd[-1] += SINFO_ADDITIONAL_NODE_PARAMS
            if self.gpu_stats:
                self.sinfo_node_cmd[-1] += GPU_PARAMS

    def check(self, _):
        commands = [
            ('sinfo', self.sinfo_partition_cmd, self.process_sinfo_partition),
            ('squeue', self.squeue_cmd, self.process_squeue),
            ('sacct', self.sacct_cmd, self.process_sacct),
            ('sdiag', self.sdiag_cmd, self.process_sdiag),
            ('sshare', self.sshare_cmd, self.process_sshare),
        ]

        if self.sinfo_collection_level > 1:
            commands.append(('snode', self.sinfo_node_cmd, self.process_sinfo_node))

        for name, cmd, process_func in commands:
            out, err, ret = get_subprocess_out(cmd)
            if ret != 0:
                self.log.error("Error running %s: %s", name, err)
            elif out:
                process_func(out)
            else:
                self.log.debug("No output from %s", name)

    def process_sinfo_partition(self, output: str):
        # normal*|c[1-2]|1|up|1000|N/A|0/2/0/2|(null)|
        lines = output.strip().split('\n')
        for line in lines:
            partition_data = line.split('|')

            tags = []
            tags.extend(self.tags)

            tags = self._process_tags(partition_data, PARTITION_MAP["tags"], tags)

            if self.gpu_stats:
                gpu_tags = self._process_sinfo_gpu(partition_data[-2], partition_data[-1], "partition", tags)
                tags.extend(gpu_tags)

            self._process_sinfo_cpu_state(partition_data[6], "partition", tags)
            self.gauge('partition.info', 1, tags)

    def process_sinfo_node(self, output):
        # PARTITION |AVAIL |NODELIST |NODES(A/I/O/T) |MEMORY |CLUSTER |CPU_LOAD |FREE_MEM |TMP_DISK |STATE |REASON |ACTIVE_FEATURES |THREADS |GRES      |GRES_USED | # noqa: E501
        # normal    |up    |c1       |0/1/0/1        |  1000 |N/A     |    1.84 |    5440 |       0 |idle  |none   |(null)          |      1 |(null)    |(null)    | # noqa: E501

        for line in output.strip().split('\n'):
            node_data = line.split('|')

            tags = []
            tags.extend(self.tags)

            tags = self._process_tags(node_data, NODE_MAP["tags"], tags)

            if self.sinfo_collection_level > 2:
                tags = self._process_tags(node_data, NODE_MAP["extended_tags"], tags)

            if self.gpu_stats:
                gpu_tags = self._process_sinfo_gpu(node_data[-2], node_data[-1], "node", tags)
                tags.extend(gpu_tags)

            # Submit metrics
            self._process_metrics(node_data, NODE_MAP, tags)
            self._process_sinfo_cpu_state(node_data[3], 'node', tags)
            self.gauge('node.info', 1, tags=tags)

    def process_squeue(self, output):
        # JOBID |      USER |      NAME |   STATE |            NODELIST |      CPUS |   NODELIST(REASON) | MIN_MEMORY # noqa: E501
        #    31 |      root |      wrap | PENDING |                     |         1 |        (Resources) |       500M # noqa: E501
        for line in output.strip().split('\n'):
            job_data = line.split('|')

            tags = []
            tags.extend(self.tags)

            tags = self._process_tags(job_data, SQUEUE_MAP["tags"], tags)

            self.gauge('squeue.job.info', 1, tags=tags)

    def process_sacct(self, output):
        # JobID    |JobName |Partition|Account|AllocCPUS|AllocTRES                       |Elapsed  |CPUTimeRAW|MaxRSS|MaxVMSize|AveCPU|AveRSS |State   |ExitCode|Start               |End     |NodeList   | # noqa: E501
        # 36       |test.py |normal   |root   |1        |billing=1,cpu=1,mem=500M,node=1 |00:00:03 |3         |      |         |      |       |RUNNING |0:0     |2024-09-24T12:00:01 |Unknown |c1         | # noqa: E501
        # 36.batch |batch   |         |root   |1        |cpu=1,mem=500M,node=1           |00:00:03 |3         |      |         |      |       |RUNNING |0:0     |2024-09-24T12:00:01 |Unknown |c1         | # noqa: E501
        for line in output.strip().split('\n'):
            job_data = line.split('|')
            tags = []
            tags.extend(self.tags)

            tags = self._process_tags(job_data, SACCT_MAP["tags"], tags)

            # Submit job info metric
            self._process_metrics(job_data, SACCT_MAP, tags)
            duration = parse_duration(job_data[6])
            self.gauge('sacct.job.duration', duration, tags=tags)
            self.gauge('sacct.job.info', 1, tags=tags)

    def process_sshare(self, output):
        # Account |User |RawShares |NormShares |RawUsage |NormUsage |EffectvUsage |FairShare |LevelFS  |GrpTRESMins |TRESRunMins                                                    | # noqa: E501
        # root    |root |        1 |           |       0 |          |    0.000000 | 0.000000 |0.000000 |            |cpu=0,mem=0,energy=0,node=0,billing=0,fs/disk=0,vmem=0,pages=0 | # noqa: E501

        for line in output.strip().split('\n'):
            sshare_data = line.split('|')

            tags = []
            tags.extend(self.tags)

            tags = self._process_tags(sshare_data, SSHARE_MAP["tags"], tags)

            self._process_metrics(sshare_data, SSHARE_MAP, tags)

    def process_sdiag(self, output):
        metrics = {}
        backfill_section = False

        for line in output.split('\n'):
            line = line.strip()

            if 'Backfilling stats' in line:
                backfill_section = True

            # Some patterns overlap so we need such as Total Cycles. We need to switch between the two maps once
            # we see the 'Backfilling stats' line.
            current_map = SDIAG_MAP['backfill_stats'] if backfill_section else SDIAG_MAP['main_stats']

            for metric, pattern in current_map.items():
                if pattern in line:
                    try:
                        metric_value_str = line.split(':')[1].strip()
                        metric_value = float(metric_value_str) if '.' in metric_value_str else int(metric_value_str)
                        metrics[metric] = metric_value
                    except (ValueError, IndexError):
                        continue
                    break

        for name, value in metrics.items():
            self.gauge(f'sdiag.{name}', value, tags=self.tags)

    def _process_sinfo_cpu_state(self, cpus_state: str, namespace, tags):
        # "0/2/0/2"
        allocated, idle, other, total = cpus_state.split('/')
        self.gauge(f'{namespace}.cpu.allocated', allocated, tags)
        self.gauge(f'{namespace}.cpu.idle', idle, tags)
        self.gauge(f'{namespace}.cpu.other', other, tags)
        self.gauge(f'{namespace}.cpu.total', total, tags)

    def _process_sinfo_gpu(self, gres, gres_used, namespace, tags):
        used_gpu_used_idx = "N/A"
        gpu_type = "N/A"
        total_gpu = 0
        used_gpu_count = 0
        # gpu:tesla:4(IDX:0-3)
        gres_used_parts = gres_used.split(':')
        # gpu:tesla:4
        gres_total_parts = gres.split(':')

        if len(gres_used_parts) == 3 and "gpu" in gres_used_parts:
            # ["gpu","tesla","4(IDX:0-3)"]
            used_gpu = gres_used_parts[2].split('(')
            used_gpu_count = int(used_gpu[0])
            used_gpu_used_idx = used_gpu[1].rstrip(')').split(':')[1]
            gpu_type = gres_used_parts[1]

        if len(gres_total_parts) == 3 and "gpu" in gres_total_parts:
            # ["gpu","tesla","4"]
            total_gpu = int(gres_total_parts[2])

        tags = [f"slurm_partition_gpu_type:{gpu_type}", f"slurm_partition_gpu_used_idx:{used_gpu_used_idx}"]
        self.gauge(f'{namespace}.gpu_total', total_gpu, tags)
        self.gauge(f'{namespace}.gpu_used', used_gpu_count, tags)

        return tags

    def _process_tags(self, data, map, tags):
        for tag_info in map:
            value = data[tag_info["index"]]
            if not value:
                self.log.debug("Empty value for tag '%s'. Assigning 'N/A'.", tag_info["name"])
                value = "N/A"
            tags.append(f'{tag_info["name"]}:{value}')

        return tags

    def _process_metrics(self, data, metrics_map, tags):
        for metric_info in metrics_map["metrics"]:
            metric_value_str = data[metric_info["index"]]

            if metric_value_str.strip() == '':
                self.log.debug("Empty metric value for '%s'. Skipping.", metric_info["name"])
                continue

            try:
                metric_value = float(metric_value_str) if '.' in metric_value_str else int(metric_value_str)
            except ValueError:
                self.log.debug("Invalid metric value '%s' for '%s'. Skipping.", metric_value_str, metric_info["name"])
                continue

            self.gauge(metric_info["name"], metric_value, tags)
