# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import re
import subprocess
import time
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import timedelta

from datadog_checks.base import AgentCheck, is_affirmative
from datadog_checks.base.utils.tagging import tagger
from datadog_checks.base.utils.time import get_timestamp

from .config_models import ConfigMixin
from .constants import (
    GPU_PARAMS,
    GPU_TOTAL,
    NODE_MAP,
    PARTITION_MAP,
    SACCT_MAP,
    SACCT_PARAMS,
    SCONTROL_PARAMS,
    SCONTROL_TAG_MAPPING,
    SDIAG_MAP,
    SINFO_ADDITIONAL_NODE_PARAMS,
    SINFO_NODE_PARAMS,
    SINFO_PARTITION_INFO_PARAMS,
    SINFO_PARTITION_PARAMS,
    SINFO_STATE_CODE,
    SQUEUE_MAP,
    SQUEUE_PARAMS,
    SSHARE_MAP,
    SSHARE_PARAMS,
)

# Upper bound (seconds) on any Slurm CLI call so a hung binary can't wedge the check.
SUBPROCESS_TIMEOUT = 120


def get_subprocess_output(cmd):
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=SUBPROCESS_TIMEOUT)
        return result.stdout, result.stderr, result.returncode
    except Exception as e:
        return None, f"Error running {cmd}: {e}", 1


def parse_duration(time_str):
    # Slurm renders durations as '[DD-]HH:MM:SS'; the day prefix appears once a job runs >= 24h.
    try:
        days = 0
        if '-' in time_str:
            days_str, time_str = time_str.split('-', 1)
            days = int(days_str)
        hours, minutes, seconds = map(int, time_str.split(':'))
        return timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds).total_seconds()
    except Exception:
        return None


# Matches a sinfo GRES/GRES_USED gpu entry: legacy 'gpu:tesla:4', modern
# 'gpu:<type>:8(S:0-1)' (socket affinity) and 'gpu:<type>:3(IDX:0,4-5)' (used indices),
# and typeless 'gpu:8'. The trailing '(...)' is optional; '(null)' simply won't match.
GPU_GRES_RE = re.compile(r'gpu:(?:(?P<type>[^:(]+):)?(?P<count>\d+)(?:\((?P<detail>[^)]*)\))?')

# seff prints memory in whichever unit fits; normalize everything to MB for the metric.
MEMORY_UNIT_TO_MB = {"B": 1 / 1024 / 1024, "KB": 1 / 1024, "MB": 1, "GB": 1024, "TB": 1024 * 1024}


@dataclass
class ProcessPidMatch:
    host_pid: str
    namespace_pids: list[str]


class SlurmCheck(AgentCheck, ConfigMixin):
    # This will be the prefix of every metric and service check the integration sends
    __NAMESPACE__ = 'slurm'

    def get_slurm_command(self, cmd_name, params):
        cmd_path = self.instance.get(f'{cmd_name}_path', os.path.join(self.slurm_binaries_dir, cmd_name))
        return [cmd_path] + params

    def __init__(self, name, init_config, instances):
        super(SlurmCheck, self).__init__(name, init_config, instances)

        # What should be collected
        self.collect_sinfo_stats = is_affirmative(self.instance.get('collect_sinfo_stats', True))
        self.collect_squeue_stats = is_affirmative(self.instance.get('collect_squeue_stats', True))
        self.collect_sdiag_stats = is_affirmative(self.instance.get('collect_sdiag_stats', True))
        self.collect_sshare_stats = is_affirmative(self.instance.get('collect_sshare_stats', True))
        self.collect_sacct_stats = is_affirmative(self.instance.get('collect_sacct_stats', True))
        self.collect_scontrol_stats = is_affirmative(self.instance.get('collect_scontrol_stats', False))
        self.collect_seff_stats = is_affirmative(self.instance.get('collect_seff_stats', False))
        self.resolve_scontrol_host_pids = is_affirmative(self.instance.get('resolve_scontrol_host_pids', False))

        # Additional configurations
        self.gpu_stats = is_affirmative(self.instance.get('collect_gpu_stats', False))
        self.sinfo_collection_level = self.instance.get('sinfo_collection_level', 1)

        # Binary paths
        self.slurm_binaries_dir = self.init_config.get('slurm_binaries_dir', '/usr/bin/')

        # CMD compilation
        if self.collect_sinfo_stats:
            self.sinfo_partition_cmd = self.get_slurm_command('sinfo', SINFO_PARTITION_PARAMS)
            self.sinfo_partition_info_cmd = self.get_slurm_command('sinfo', SINFO_PARTITION_INFO_PARAMS)
            if self.sinfo_collection_level > 1:
                self.sinfo_node_cmd = self.get_slurm_command('sinfo', SINFO_NODE_PARAMS)
                if self.sinfo_collection_level > 2:
                    self.sinfo_node_cmd[-1] += SINFO_ADDITIONAL_NODE_PARAMS
                if self.gpu_stats:
                    self.sinfo_node_cmd[-1] += GPU_PARAMS
            if self.gpu_stats:
                self.sinfo_partition_cmd[-1] += GPU_TOTAL
                self.sinfo_partition_info_cmd[-1] += GPU_PARAMS

        if self.collect_squeue_stats:
            self.squeue_cmd = self.get_slurm_command('squeue', SQUEUE_PARAMS)

        if self.collect_sacct_stats:
            self.sacct_cmd = self.get_slurm_command('sacct', SACCT_PARAMS)

        if self.collect_sdiag_stats:
            self.sdiag_cmd = self.get_slurm_command('sdiag', [])

        if self.collect_seff_stats:
            self.seff_cmd = self.get_slurm_command('seff', [])

        if self.collect_sshare_stats:
            self.sshare_cmd = self.get_slurm_command('sshare', SSHARE_PARAMS)

        if self.collect_scontrol_stats:
            self.scontrol_cmd = self.get_slurm_command('scontrol', SCONTROL_PARAMS)
            self.squeue_enrich_cmd = self.get_slurm_command('squeue', ["-j"])

        # Metric and Tag configuration
        self.last_run_time = None
        self.tags = self.instance.get('tags', [])

        # Debug only. QOL feature for troubleshooting in the future. Allows me to dump specific
        # debugging logs depending on what the issue is.
        self.debug_sinfo_stats = is_affirmative(self.instance.get('debug_sinfo_stats', False))
        self.debug_squeue_stats = is_affirmative(self.instance.get('debug_squeue_stats', False))
        self.debug_sdiag_stats = is_affirmative(self.instance.get('debug_sdiag_stats', False))
        self.debug_sshare_stats = is_affirmative(self.instance.get('debug_sshare_stats', False))
        self.debug_sacct_stats = is_affirmative(self.instance.get('debug_sacct_stats', False))
        self.debug_scontrol_stats = is_affirmative(self.instance.get('debug_scontrol_stats', False))

    def check(self, _):
        self.collect_metadata()

        commands = []

        if self.collect_sinfo_stats:
            commands.append(('sinfo', self.sinfo_partition_cmd, self.process_sinfo_partition))
            commands.append(('sinfo', self.sinfo_partition_info_cmd, self.process_sinfo_partition_info))
            if self.sinfo_collection_level > 1:
                commands.append(('snode', self.sinfo_node_cmd, self.process_sinfo_node))

        if self.collect_squeue_stats:
            commands.append(('squeue', self.squeue_cmd, self.process_squeue))

        if self.collect_sdiag_stats:
            commands.append(('sdiag', self.sdiag_cmd, self.process_sdiag))

        if self.collect_sshare_stats:
            commands.append(('sshare', self.sshare_cmd, self.process_sshare))

        sacct_window_end = None
        if self.collect_sacct_stats and self.last_run_time is not None:
            sacct_window_end = self._update_sacct_params()
            commands.append(('sacct', self.sacct_cmd, self.process_sacct))
        elif self.last_run_time is None:
            # Set timestamp here so we can use it for the next run and collect sacct stats only
            # between the 2 runs.
            self.last_run_time = get_timestamp()

        if self.collect_scontrol_stats:
            commands.append(('scontrol', self.scontrol_cmd, self.process_scontrol))

        for name, cmd, process_func in commands:
            self.log.debug("Running %s command: %s", name, cmd)
            out, err, ret = get_subprocess_output(cmd)
            processed = False
            if ret != 0:
                self.log.error("Error running %s: %s", name, err)
            elif out:
                self.log.debug("Processing %s output", name)
                try:
                    process_func(out)
                    processed = True
                except Exception:
                    self.log.exception("Error processing %s output", name)
            else:
                # A successful command with no output (e.g. no completed jobs in the window) is not a failure.
                self.log.debug("No output from %s", name)
                processed = True

            # Advance the sacct window only after a fully successful sacct call (ran AND parsed), so
            # neither a command failure nor a parse error silently drops that window's jobs.
            if name == 'sacct' and processed and sacct_window_end is not None:
                self.last_run_time = sacct_window_end

    def process_sinfo_partition(self, output):
        # test-queue*|N/A|1/2/0/3
        for partition_data, tags in self._iter_rows(output, self.debug_sinfo_stats, 'sinfo partition'):
            tags = self._process_tags(partition_data, PARTITION_MAP["tags"], tags)

            if self.gpu_stats:
                gpu_tag, _ = self._process_sinfo_gpu(partition_data[-1], None, "partition", tags)
                tags.extend(gpu_tag)

            self._process_sinfo_aiot_state(partition_data[2], "partition", tags)

    def process_sinfo_partition_info(self, output):
        # test-queue*|N/A|c[1-2]|up|1|972|allocated|10
        for partition_data, tags in self._iter_rows(output, self.debug_sinfo_stats, 'sinfo partition info'):
            tags = self._process_tags(partition_data, PARTITION_MAP["tags"], tags)

            if self.gpu_stats:
                gpu_tags, gpu_info_tags = self._process_sinfo_gpu(
                    partition_data[-2], partition_data[-1], "partition", tags
                )
                tags.extend(gpu_tags)

            tags = self._process_tags(partition_data, PARTITION_MAP["info_tags"], tags)
            if self.gpu_stats:
                tags.extend(gpu_info_tags)

            self._process_metrics(partition_data, PARTITION_MAP["metrics"], tags)
            self.gauge('partition.info', 1, tags)

        self.gauge('sinfo.partition.enabled', 1)

    def process_sinfo_node(self, output):
        # PARTITION |AVAIL |NODELIST |NODES(A/I/O/T) |MEMORY |CLUSTER |CPU_LOAD |FREE_MEM |TMP_DISK |STATE |REASON |ACTIVE_FEATURES |THREADS |GRES      |GRES_USED  # noqa: E501
        # normal    |up    |c1       |0/1/0/1        |  1000 |N/A     |    1.84 |    5440 |       0 |idle  |none   |(null)          |      1 |(null)    |(null)     # noqa: E501
        for node_data, tags in self._iter_rows(output, self.debug_sinfo_stats, 'sinfo node'):
            tags = self._process_tags(node_data, NODE_MAP["tags"], tags)

            if self.gpu_stats:
                gpu_tags, gpu_info_tags = self._process_sinfo_gpu(node_data[-2], node_data[-1], "node", tags)
                tags.extend(gpu_tags)

            self._process_metrics(node_data, NODE_MAP["metrics"], tags)
            if self.sinfo_collection_level > 2:
                self._process_metrics(node_data, NODE_MAP["extended_metrics"], tags)

            self._process_sinfo_aiot_state(node_data[3], 'node', tags)

            tags = self._process_tags(node_data, NODE_MAP["info_tags"], tags)
            if self.sinfo_collection_level > 2:
                tags = self._process_tags(node_data, NODE_MAP["extended_tags"], tags)

            # Submit metrics
            if self.gpu_stats:
                tags.extend(gpu_info_tags)
            self.gauge('node.info', 1, tags=tags)

        self.gauge('sinfo.node.enabled', 1)

    def process_squeue(self, output):
        # JOBID |      USER |      NAME |   STATE |            NODELIST |      CPUS |   NODELIST(REASON) | MIN_MEMORY | Partition # noqa: E501
        #    31 |      root |      wrap | PENDING |                     |         1 |        (Resources) |       500M | foo       # noqa: E501
        for job_data, tags in self._iter_rows(output, self.debug_squeue_stats, 'squeue'):
            tags = self._process_tags(job_data, SQUEUE_MAP["tags"], tags)

            self.gauge('squeue.job.info', 1, tags=tags)

        self.gauge('squeue.enabled', 1)

    def process_sacct(self, output):
        # JobID    |JobName |Partition|Account|AllocCPUS|AllocTRES                       |Elapsed  |CPUTimeRAW|MaxRSS|MaxVMSize|AveCPU|AveRSS |State   |ExitCode|Start               |End     |NodeList   | AveDiskRead | MaxDiskRead # noqa: E501
        # 36       |test.py |normal   |root   |1        |billing=1,cpu=1,mem=500M,node=1 |00:00:03 |3         |      |         |      |       |RUNNING |0:0     |2024-09-24T12:00:01 |Unknown |c1         | 0.000000    | 0.000000     # noqa: E501
        # 36.batch |batch   |         |root   |1        |cpu=1,mem=500M,node=1           |00:00:03 |3         |      |         |      |       |RUNNING |0:0     |2024-09-24T12:00:01 |Unknown |c1         | 0.000000    | 0.000000     # noqa: E501
        for job_data, tags in self._iter_rows(output, self.debug_sacct_stats, 'sacct'):
            if len(job_data) <= 12:
                self.log.debug("Skipping malformed sacct line (%d fields): %s", len(job_data), job_data)
                continue

            # Process the JobID
            job_id_full = job_data[0].strip()
            has_suffix = '.' in job_id_full
            if has_suffix:
                job_id, job_id_suffix = job_id_full.split('.', 1)
                tags.append(f"slurm_job_id:{job_id}")
                tags.append(f"slurm_job_id_suffix:{job_id_suffix}")
            else:
                job_id = job_id_full
                tags.append(f"slurm_job_id:{job_id}")

            tags = self._process_tags(job_data, SACCT_MAP["tags"], tags)

            # Process job metrics
            self._process_metrics(job_data, SACCT_MAP["metrics"], tags)

            duration = parse_duration(job_data[6])
            ave_cpu = parse_duration(job_data[10])

            if duration is not None:
                self.gauge('sacct.job.duration', duration, tags=tags)
            else:
                self.log.debug("Invalid duration '%s' for job '%s'. Skipping.", job_data[6], job_id)
            if ave_cpu is not None:
                self.gauge('sacct.slurm_job_avgcpu', ave_cpu, tags=tags)
            self.gauge('sacct.job.info', 1, tags=tags)
            if self.collect_seff_stats:
                job_state = job_data[12].strip().upper()
                # Run on Completed Jobs only https://wiki.rcs.huji.ac.il/hurcs/guides/resource-utilization
                if not has_suffix and job_state == 'COMPLETED':
                    self.log.debug("Processing seff for job %s", job_id)
                    self.process_seff(job_id, tags)

        self.gauge('sacct.enabled', 1)

    def process_seff(self, job_id, tags):
        cmd = self.seff_cmd + [str(job_id)]
        self.log.debug("Running seff command: %s", cmd)
        out, err, ret = get_subprocess_output(cmd)
        if ret != 0 or not out:
            self.log.debug("seff command failed for job %s: %s", job_id, err)
            return

        cpu_utilized = None
        cpu_eff = None
        mem_utilized = None
        mem_eff = None

        for line in out.splitlines():
            line = line.strip()

            # CPU Utilized: 00:00:01
            if line.startswith('CPU Utilized:'):
                cpu_utilized = parse_duration(line.split(':', 1)[1].strip())
                continue

            # CPU Efficiency: 20.00% of 00:00:05 core-walltime
            match = re.match(r'CPU Efficiency: ([\d.]+)%', line)
            if match:
                cpu_eff = float(match.group(1))
                continue

            # Memory Utilized: 0.00 MB / 776.00 KB / 1.50 GB — normalize whatever unit to MB.
            match = re.match(r'Memory Utilized: ([\d.]+)\s*([KMGT]?B)', line)
            if match:
                mem_utilized = float(match.group(1)) * MEMORY_UNIT_TO_MB.get(match.group(2), 1)
                continue

            # Memory Efficiency: 0.00% of 16.00 B (16.00 B/node)
            match = re.match(r'Memory Efficiency: ([\d.]+)%', line)
            if match:
                mem_eff = float(match.group(1))
                continue

        if cpu_utilized is not None:
            self.gauge('seff.cpu_utilized', cpu_utilized, tags)
        if cpu_eff is not None:
            self.gauge('seff.cpu_efficiency', cpu_eff, tags)
        if mem_utilized is not None:
            self.gauge('seff.memory_utilized_mb', mem_utilized, tags)
        if mem_eff is not None:
            self.gauge('seff.memory_efficiency', mem_eff, tags)

    def process_sshare(self, output):
        # Account |User |RawShares |NormShares |RawUsage |NormUsage |EffectvUsage |FairShare |LevelFS  |GrpTRESMins |TRESRunMins                                                     # noqa: E501
        # root    |root |        1 |           |       0 |          |    0.000000 | 0.000000 |0.000000 |            |cpu=0,mem=0,energy=0,node=0,billing=0,fs/disk=0,vmem=0,pages=0  # noqa: E501
        for sshare_data, tags in self._iter_rows(output, self.debug_sshare_stats, 'sshare'):
            tags = self._process_tags(sshare_data, SSHARE_MAP["tags"], tags)

            self._process_metrics(sshare_data, SSHARE_MAP["metrics"], tags)

        self.gauge('sshare.enabled', 1, tags=self.tags)

    def process_sdiag(self, output):
        metrics = {}
        backfill_section = False

        lines = output.split('\n')

        if self.debug_sdiag_stats:
            self.log.debug("Processing sdiag output: %s", lines)

        for line in lines:
            line = line.strip()

            if 'Backfilling stats' in line:
                backfill_section = True
                self.log.debug("Switching to backfilling stats section")

            # Some patterns overlap so we need such as Total Cycles. We need to switch between the two maps once
            # we see the 'Backfilling stats' line.
            current_map = SDIAG_MAP['backfill_stats'] if backfill_section else SDIAG_MAP['main_stats']

            # Try to match known metrics
            for metric, pattern in current_map.items():
                if pattern in line:
                    try:
                        metric_value_str = line.split(':')[1].strip()
                        metric_value = float(metric_value_str) if '.' in metric_value_str else int(metric_value_str)
                        metrics[metric] = metric_value
                    except (ValueError, IndexError):
                        continue
                    break

            if 'Last cycle when' in line:
                try:
                    match = re.search(r'\((\d+)\)', line)
                    if match:
                        last_cycle_epoch = int(match.group(1))
                        now = int(time.time())
                        diff = now - last_cycle_epoch
                        self.gauge('sdiag.backfill.last_cycle_seconds_ago', diff, tags=self.tags)
                except Exception as e:
                    self.log.debug("Failed to parse last cycle epoch from line '%s': %s", line, e)

        for name, value in metrics.items():
            self.gauge(f'sdiag.{name}', value, tags=self.tags)

        self.gauge('sdiag.enabled', 1)

    def _update_sacct_params(self):
        # Build the windowed sacct command and return the window-end timestamp. The caller advances
        # last_run_time only after sacct succeeds, so a failed call doesn't permanently drop that window.
        sacct_params = SACCT_PARAMS.copy()
        now = get_timestamp()
        if self.last_run_time is not None:
            # Guard against a backward clock correction (NTP) producing a negative, malformed window.
            delta = max(0, now - self.last_run_time)
            start_time_param = f"--starttime=now-{int(delta)}seconds"

            sacct_params = [param for param in sacct_params if not param.startswith('--starttime')]
            sacct_params.append(start_time_param)
            self.log.debug("Updating sacct command with new timestamp: %s", start_time_param)

        # Update the sacct command with the dynamic SACCT_PARAMS
        self.sacct_cmd = self.get_slurm_command('sacct', sacct_params)
        return now

    def _process_sinfo_aiot_state(self, aiot_state, namespace, tags):
        # "0/2/0/2"
        try:
            allocated, idle, other, total = map(int, aiot_state.split('/'))
        except ValueError as e:
            self.log.debug("Invalid CPU state '%s'. Skipping. Error: %s", aiot_state, e)
            return
        if namespace == "partition":
            self.gauge(f'{namespace}.node.allocated', allocated, tags)
            self.gauge(f'{namespace}.node.idle', idle, tags)
            self.gauge(f'{namespace}.node.other', other, tags)
            self.gauge(f'{namespace}.node.total', total, tags)
        elif namespace == "node":
            self.gauge(f'{namespace}.cpu.allocated', allocated, tags)
            self.gauge(f'{namespace}.cpu.idle', idle, tags)
            self.gauge(f'{namespace}.cpu.other', other, tags)
            self.gauge(f'{namespace}.cpu.total', total, tags)

    def _parse_gpu_gres(self, gres):
        # Parse a sinfo GRES/GRES_USED gpu field into (gpu_type, count, detail). Tolerates the
        # modern suffixes 'gpu:<type>:8(S:0-1)' / 'gpu:<type>:3(IDX:0,4-5)', the legacy
        # 'gpu:<type>:4', typeless 'gpu:8', and '(null)'. count/detail are None when absent.
        match = GPU_GRES_RE.search(gres) if gres else None
        if not match:
            return "null", None, None
        return match.group('type') or "null", int(match.group('count')), match.group('detail')

    def _process_sinfo_gpu(self, gres, gres_used, namespace, tags):
        gpu_type, total_gpu, _ = self._parse_gpu_gres(gres)
        used_gpu_count = None
        used_gpu_used_idx = "null"
        if gres_used is not None:
            _, used_gpu_count, used_detail = self._parse_gpu_gres(gres_used)
            if used_detail and used_detail.startswith("IDX:"):
                idx = used_detail[len("IDX:") :]
                used_gpu_used_idx = idx if idx and idx != "N/A" else "null"

        gpu_tags = [f"slurm_{namespace}_gpu_type:{gpu_type}"]
        gpu_info_tags = [f"slurm_{namespace}_gpu_used_idx:{used_gpu_used_idx}"]
        _tags = tags + gpu_tags
        if total_gpu is not None:
            self.gauge(f'{namespace}.gpu_total', total_gpu, _tags)
        if used_gpu_count is not None:
            self.gauge(f'{namespace}.gpu_used', used_gpu_count, _tags)

        return gpu_tags, gpu_info_tags

    def _iter_rows(self, output, debug=False, name="") -> Iterator[tuple[list[str], list[str]]]:
        # Yield (fields, base_tags) for each pipe-delimited row of a command's output.
        lines = output.strip().split('\n')
        if debug:
            self.log.debug("Processing %s output: %s", name, lines)
        for line in lines:
            yield line.split('|'), list(self.tags)

    def _process_tags(self, data, tag_map, tags):
        for tag_info in tag_map:
            index = tag_info['index']
            if index >= len(data):
                self.log.debug("Index %d out of range for tag '%s'. Skipping.", index, tag_info['name'])
                continue
            value = data[index]

            # Strip parantheses
            if value.startswith('(') and value.endswith(')'):
                value = value[1:-1].strip()

            # Replace empty values with 'null'. This makes it distinguishable in the UI that the tag is being
            # submitted, but the value is empty.
            if not value:
                self.log.debug("Empty value for tag '%s'. Assigning 'null'.", tag_info["name"])
                value = "null"

            if tag_info["name"] == "slurm_partition_name":
                # Check for asterisk (*) or default partition in the value
                if '*' in value:
                    value = value.replace('*', '')  # Remove the asterisk
                    tags.append('slurm_default_partition:true')

            # https://slurm.schedmd.com/sinfo.html#SECTION_NODE-STATE-CODES
            if tag_info["name"] in ["slurm_partition_state", "slurm_node_state"]:
                for key, mapped_value in SINFO_STATE_CODE.items():
                    if key in value:
                        value = value.replace(key, '')
                        tags.append(f'sinfo_state_code:{mapped_value}')
                value = value.strip()

            tags.append(f'{tag_info["name"]}:{value}')

        return tags

    def _process_metrics(self, data, metrics_map, tags):
        for metric_info in metrics_map:
            index = metric_info['index']
            if index >= len(data):
                self.log.debug("Index %d out of range for metric '%s'. Skipping.", index, metric_info["name"])
                continue
            metric_value_str = data[index]

            if metric_value_str.strip() == '':
                self.log.debug("Empty metric value for '%s'. Skipping.", metric_info["name"])
                continue

            value = metric_value_str.strip().upper()
            multiplier = 1
            if value.endswith('K'):
                multiplier = 1000
                value = value[:-1]
            elif value.endswith('M'):
                multiplier = 1000000
                value = value[:-1]

            try:
                metric_value = float(value) * multiplier
            except ValueError:
                self.log.debug("Invalid metric value '%s' for '%s'. Skipping.", metric_value_str, metric_info["name"])
                continue

            self.gauge(metric_info["name"], metric_value, tags)

    def process_scontrol(self, output):
        # This is for worker nodes only. The local PID of the job isn't available in the slurm controller output.
        # It's only available where the job is running.
        # PID      JOBID    STEPID   LOCALID GLOBALID
        # 3771     14       batch    0       0
        # 3772     14       batch    -       -
        base_cmd = self.scontrol_cmd[:-1]
        hostname = os.uname()[1]
        slurm_node, _, ret = get_subprocess_output(base_cmd + ["show", "hostname", hostname])
        if ret != 0 or not slurm_node:
            self.log.error("Unable to resolve Slurm node name for host '%s'. Skipping scontrol.", hostname)
            return
        slurm_node = slurm_node.strip()
        lines = output.strip().splitlines()
        if not lines:
            self.log.debug("No scontrol listpid output to process")
            return
        headers = lines[0].split()

        # Cache for job details to avoid duplicate calls
        job_details_cache = {}
        host_pid_matches_by_namespace_pid: dict[str, list[ProcessPidMatch]] = (
            self._get_host_pid_matches_by_namespace_pid() if self.resolve_scontrol_host_pids else {}
        )

        for line in lines[1:]:
            tags = [f"slurm_node_name:{slurm_node}"]
            fields = line.split()
            job_id = None

            for header, value in zip(headers, fields):
                new_header = SCONTROL_TAG_MAPPING.get(header, f"slurm_{header.lower()}")

                if new_header == "pid":
                    host_pid_match = self._resolve_scontrol_host_pid(value, host_pid_matches_by_namespace_pid)
                    tags.extend(self._get_process_tags(host_pid_match.host_pid))
                    for namespace_pid in host_pid_match.namespace_pids:
                        if namespace_pid == host_pid_match.host_pid:
                            continue
                        tags.append(f"nspid:{namespace_pid}")
                    value = host_pid_match.host_pid

                tags.append(f"{new_header}:{value}")

                if header == "JOBID" and value.isdigit():
                    job_id = value

            if job_id:
                # Only fetch job details if we haven't seen this job ID before
                if job_id not in job_details_cache:
                    job_details_cache[job_id] = self._enrich_scontrol_tags(job_id)
                tags.extend(job_details_cache[job_id])

            self.gauge("scontrol.jobs.info", 1, tags=tags + self.tags)

    def _resolve_scontrol_host_pid(
        self, namespace_pid: str, host_pid_matches_by_namespace_pid: dict[str, list[ProcessPidMatch]]
    ) -> ProcessPidMatch:
        host_pid_matches = host_pid_matches_by_namespace_pid.get(namespace_pid)
        if not host_pid_matches:
            return ProcessPidMatch(host_pid=namespace_pid, namespace_pids=[])

        if len(host_pid_matches) > 1:
            namespace_match = host_pid_matches[0]
            for host_pid_match in host_pid_matches:
                # Prefer a translated namespace PID, but do not disambiguate by container yet.
                if namespace_pid != host_pid_match.host_pid and namespace_pid in host_pid_match.namespace_pids:
                    namespace_match = host_pid_match
                    break

            matches = [
                {"host_pid": match.host_pid, "namespace_pids": match.namespace_pids} for match in host_pid_matches
            ]
            self.log.debug(
                "Found multiple host PID matches for scontrol namespace PID %s: %s. Using host PID %s.",
                namespace_pid,
                matches,
                namespace_match.host_pid,
            )
            return namespace_match

        return host_pid_matches[0]

    def _get_process_tags(self, pid):
        # Example gpu tags being returned:
        # ['gpu_vendor:nvidia', 'gpu_device:tesla_v100', 'gpu_uuid:gpu_xxxx...']
        pidtags = tagger.tag(f"process://{pid}", tagger.ORCHESTRATOR)
        if pidtags:  # Guard against tagger.tag returning None
            return pidtags

        return []

    def _get_host_pid_matches_by_namespace_pid(self):
        host_proc = os.environ.get("HOST_PROC", "/host/proc")
        host_pid_matches_by_namespace_pid = {}

        try:
            proc_entries = os.scandir(host_proc)
        except OSError as e:
            self.log.debug("Unable to scan host proc path '%s': %s", host_proc, e)
            return host_pid_matches_by_namespace_pid

        with proc_entries:
            for entry in proc_entries:
                if not entry.name.isdigit():
                    continue

                pid_match = ProcessPidMatch(
                    host_pid=entry.name,
                    namespace_pids=self._read_namespace_pids(entry.path, entry.name),
                )
                for namespace_pid in pid_match.namespace_pids:
                    host_pid_matches_by_namespace_pid.setdefault(namespace_pid, []).append(pid_match)

        return host_pid_matches_by_namespace_pid

    def _read_namespace_pids(self, proc_path, host_pid):
        try:
            with open(os.path.join(proc_path, "status")) as status_file:
                for line in status_file:
                    if line.startswith("NSpid:"):
                        return line.split()[1:]
        except OSError as e:
            self.log.debug("Unable to read process status for PID %s: %s", host_pid, e)

        return [host_pid]

    def _enrich_scontrol_tags(self, job_id):
        # Tries to enrich the scontrol job with additional details from squeue.
        try:
            cmd = self.get_slurm_command('squeue', ["-j", job_id, "-ho", "%u %T %j"])
            res, err, code = get_subprocess_output(cmd)

            if code == 0 and res.strip():
                output_line = res.strip()
                parts = output_line.split()

                if len(parts) == 3:
                    user, state, job_name = parts
                    return [f"slurm_job_user:{user}", f"slurm_job_state:{state}", f"slurm_job_name:{job_name}"]
                else:
                    self.log.debug("Unexpected number of parts in squeue output for job %s: %s", job_id, output_line)
            else:
                self.log.debug("Error fetching squeue details for job %s: %s", job_id, err)
        except Exception as e:
            self.log.debug("Error fetching squeue details for job %s: %s", job_id, e)

        return []

    @AgentCheck.metadata_entrypoint
    def collect_metadata(self):
        # Leaving this one as a try because the metadata version collection isn't all that important
        # even if it fails and thus should not stop the check from running.
        try:
            # slurm 21.08.6\n
            out, err, ret = get_subprocess_output(self.get_slurm_command('sinfo', ['--version']))
            if ret != 0:
                self.log.error("Error running sinfo --version: %s", err)
            elif out:
                self.log.debug("Processing sinfo --version output: %s", out)
                parts = out.split(' ')
                version_out = parts[1].strip() if len(parts) > 1 else ''
                if version_out:
                    version_parts = version_out.split('.')
                    version = {
                        "major": version_parts[0],
                        "minor": version_parts[1],
                        "mod": version_parts[2] if len(version_parts) > 2 else "0",
                    }
                    raw_version = f'{version["major"]}.{version["minor"]}.{version["mod"]}'
                    self.set_metadata('version', raw_version, scheme='parts', part_map=version)
                    self.log.debug('Found slurm version: %s', raw_version)
            else:
                self.log.debug("No output from sinfo --version")
        except Exception as e:
            self.log.error("Error collecting metadata: %s", e)
