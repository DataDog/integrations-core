# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import subprocess
from datetime import timedelta

from datadog_checks.base import AgentCheck, is_affirmative
from datadog_checks.base.utils.time import get_timestamp

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
    SINFO_STATE_CODE,
    SQUEUE_MAP,
    SQUEUE_PARAMS,
    SSHARE_MAP,
    SSHARE_PARAMS,
)


def get_subprocess_output(cmd):
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.stdout, result.stderr, result.returncode
    except Exception as e:
        return None, f"Error running {cmd}: {e}", 1


def parse_duration(time_str):
    try:
        hours, minutes, seconds = map(int, time_str.split(':'))
        duration = timedelta(hours=hours, minutes=minutes, seconds=seconds)
        return duration.total_seconds()
    except Exception:
        return None


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

        # Additional configurations
        self.gpu_stats = is_affirmative(self.instance.get('collect_gpu_stats', False))
        self.sinfo_collection_level = self.instance.get('sinfo_collection_level', 1)

        # Binary paths
        self.slurm_binaries_dir = self.init_config.get('slurm_binaries_dir', '/usr/bin/')

        # CMD compilation
        if self.collect_sinfo_stats:
            self.sinfo_partition_cmd = self.get_slurm_command('sinfo', SINFO_PARTITION_PARAMS)
            self.sinfo_collection_level = self.instance.get('sinfo_collection_level', 1)
            if self.sinfo_collection_level > 1:
                self.sinfo_node_cmd = self.get_slurm_command('sinfo', SINFO_NODE_PARAMS)
                if self.sinfo_collection_level > 2:
                    self.sinfo_node_cmd[-1] += SINFO_ADDITIONAL_NODE_PARAMS
                if self.gpu_stats:
                    self.sinfo_node_cmd[-1] += GPU_PARAMS
            if self.gpu_stats:
                self.sinfo_partition_cmd[-1] += GPU_PARAMS

        if self.collect_squeue_stats:
            self.squeue_cmd = self.get_slurm_command('squeue', SQUEUE_PARAMS)

        if self.collect_sacct_stats:
            self.sacct_cmd = self.get_slurm_command('sacct', SACCT_PARAMS)

        if self.collect_sdiag_stats:
            self.sdiag_cmd = self.get_slurm_command('sdiag', [])

        if self.collect_sshare_stats:
            self.sshare_cmd = self.get_slurm_command('sshare', SSHARE_PARAMS)

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

    def check(self, _):
        self.collect_metadata()

        commands = []

        if self.collect_sinfo_stats:
            commands.append(('sinfo', self.sinfo_partition_cmd, self.process_sinfo_partition))
            if self.sinfo_collection_level > 1:
                commands.append(('snode', self.sinfo_node_cmd, self.process_sinfo_node))

        if self.collect_squeue_stats:
            commands.append(('squeue', self.squeue_cmd, self.process_squeue))

        if self.collect_sdiag_stats:
            commands.append(('sdiag', self.sdiag_cmd, self.process_sdiag))

        if self.collect_sshare_stats:
            commands.append(('sshare', self.sshare_cmd, self.process_sshare))

        if self.collect_sacct_stats and self.last_run_time is not None:
            self._update_sacct_params()
            commands.append(('sacct', self.sacct_cmd, self.process_sacct))
        elif self.last_run_time is None:
            # Set timestamp here so we can use it for the next run and collect sacct stats only
            # between the 2 runs.
            self.last_run_time = get_timestamp()

        for name, cmd, process_func in commands:
            self.log.debug("Running %s command: %s", name, cmd)
            out, err, ret = get_subprocess_output(cmd)
            if ret != 0:
                self.log.error("Error running %s: %s", name, err)
            elif out:
                self.log.debug("Processing %s output", name)
                process_func(out)
            else:
                self.log.debug("No output from %s", name)

    def process_sinfo_partition(self, output):
        # normal*|c1|1|up|1000|N/A|1/0/0/1|allocated|1
        lines = output.strip().split('\n')

        if self.debug_sinfo_stats:
            self.log.debug("Processing sinfo partition line: %s", lines)

        for line in lines:
            partition_data = line.split('|')

            tags = []
            tags.extend(self.tags)

            tags = self._process_tags(partition_data, PARTITION_MAP["tags"], tags)

            if self.gpu_stats:
                gpu_tags = self._process_sinfo_gpu(partition_data[-2], partition_data[-1], "partition", tags)
                tags.extend(gpu_tags)

            self._process_metrics(partition_data, PARTITION_MAP, tags)

            self._process_sinfo_cpu_state(partition_data[6], "partition", tags)
            self.gauge('partition.info', 1, tags)

        self.gauge('sinfo.partition.enabled', 1)

    def process_sinfo_node(self, output):
        # PARTITION |AVAIL |NODELIST |NODES(A/I/O/T) |MEMORY |CLUSTER |CPU_LOAD |FREE_MEM |TMP_DISK |STATE |REASON |ACTIVE_FEATURES |THREADS |GRES      |GRES_USED  # noqa: E501
        # normal    |up    |c1       |0/1/0/1        |  1000 |N/A     |    1.84 |    5440 |       0 |idle  |none   |(null)          |      1 |(null)    |(null)     # noqa: E501
        lines = output.strip().split('\n')

        if self.debug_sinfo_stats:
            self.log.trace("Processing sinfo node payload: %s", lines)

        for line in lines:
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

        self.gauge('sinfo.node.enabled', 1)

    def process_squeue(self, output):
        # JOBID |      USER |      NAME |   STATE |            NODELIST |      CPUS |   NODELIST(REASON) | MIN_MEMORY # noqa: E501
        #    31 |      root |      wrap | PENDING |                     |         1 |        (Resources) |       500M # noqa: E501
        lines = output.strip().split('\n')

        if self.debug_squeue_stats:
            self.log.debug("Processing squeue output: %s", lines)

        for line in lines:
            job_data = line.split('|')

            tags = []
            tags.extend(self.tags)

            tags = self._process_tags(job_data, SQUEUE_MAP["tags"], tags)

            self.gauge('squeue.job.info', 1, tags=tags)

        self.gauge('squeue.enabled', 1)

    def process_sacct(self, output):
        # JobID    |JobName |Partition|Account|AllocCPUS|AllocTRES                       |Elapsed  |CPUTimeRAW|MaxRSS|MaxVMSize|AveCPU|AveRSS |State   |ExitCode|Start               |End     |NodeList    # noqa: E501
        # 36       |test.py |normal   |root   |1        |billing=1,cpu=1,mem=500M,node=1 |00:00:03 |3         |      |         |      |       |RUNNING |0:0     |2024-09-24T12:00:01 |Unknown |c1          # noqa: E501
        # 36.batch |batch   |         |root   |1        |cpu=1,mem=500M,node=1           |00:00:03 |3         |      |         |      |       |RUNNING |0:0     |2024-09-24T12:00:01 |Unknown |c1          # noqa: E501
        lines = output.strip().split('\n')

        if self.debug_sacct_stats:
            self.log.debug("Processing sacct output: %s", lines)

        for line in lines:
            job_data = line.split('|')
            tags = []
            tags.extend(self.tags)

            # Process the JobID
            job_id_full = job_data[0].strip()
            if '.' in job_id_full:
                job_id, job_id_suffix = job_id_full.split('.', 1)
                tags.append(f"slurm_job_id:{job_id}")
                tags.append(f"slurm_job_id_suffix:{job_id_suffix}")
            else:
                job_id = job_id_full
                tags.append(f"slurm_job_id:{job_id}")

            tags = self._process_tags(job_data, SACCT_MAP["tags"], tags)

            # Process job metrics
            self._process_metrics(job_data, SACCT_MAP, tags)

            duration = parse_duration(job_data[6])
            if not duration:
                self.log.debug("Invalid duration for job '%s'. Skipping. Assigning duration as 0.", job_id)
                duration = 0

            self.gauge('sacct.job.duration', duration, tags=tags)
            self.gauge('sacct.job.info', 1, tags=tags)

        self.gauge('sacct.enabled', 1)

    def process_sshare(self, output):
        # Account |User |RawShares |NormShares |RawUsage |NormUsage |EffectvUsage |FairShare |LevelFS  |GrpTRESMins |TRESRunMins                                                     # noqa: E501
        # root    |root |        1 |           |       0 |          |    0.000000 | 0.000000 |0.000000 |            |cpu=0,mem=0,energy=0,node=0,billing=0,fs/disk=0,vmem=0,pages=0  # noqa: E501
        lines = output.strip().split('\n')

        if self.debug_sshare_stats:
            self.log.debug("Processing sshare output: %s", lines)

        for line in lines:
            sshare_data = line.split('|')

            tags = []
            tags.extend(self.tags)

            tags = self._process_tags(sshare_data, SSHARE_MAP["tags"], tags)

            self._process_metrics(sshare_data, SSHARE_MAP, tags)

        self.gauge('sshare.enabled', 1, tags=tags)

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

        self.gauge('sdiag.enabled', 1)

    def _update_sacct_params(self):
        sacct_params = SACCT_PARAMS.copy()
        if self.last_run_time is not None:
            now = get_timestamp()
            delta = now - self.last_run_time
            start_time_param = f"--starttime=now-{int(delta)}seconds"

            sacct_params = [param for param in sacct_params if not param.startswith('--starttime')]
            sacct_params.append(start_time_param)
            self.log.debug("Updating sacct command with new timestamp: %s", start_time_param)

        self.last_run_time = get_timestamp()

        # Update the sacct command with the dynamic SACCT_PARAMS
        self.sacct_cmd = self.get_slurm_command('sacct', sacct_params)

    def _process_sinfo_cpu_state(self, cpus_state, namespace, tags):
        # "0/2/0/2"
        try:
            allocated, idle, other, total = cpus_state.split('/')
        except ValueError as e:
            self.log.debug("Invalid CPU state '%s'. Skipping. Error: %s", cpus_state, e)
            return

        self.gauge(f'{namespace}.cpu.allocated', allocated, tags)
        self.gauge(f'{namespace}.cpu.idle', idle, tags)
        self.gauge(f'{namespace}.cpu.other', other, tags)
        self.gauge(f'{namespace}.cpu.total', total, tags)

    def _process_sinfo_gpu(self, gres, gres_used, namespace, tags):
        used_gpu_used_idx = "null"
        gpu_type = "null"
        total_gpu = None
        used_gpu_count = None

        try:
            # gpu:tesla:4(IDX:0-3) -> ["gpu","tesla","4(IDX","0-3)"]
            gres_used_parts = gres_used.split(':')
            # gpu:tesla:4 -> ["gpu","tesla","4"]
            gres_total_parts = gres.split(':')

            # Ensure gres_used_parts has the correct format for GPU usage
            if len(gres_used_parts) == 4 and gres_used_parts[0] == "gpu":
                _, gpu_type, used_gpu_count_part, used_gpu_used_idx_part = gres_used_parts
                used_gpu_count = int(used_gpu_count_part.split('(')[0])
                used_gpu_used_idx = used_gpu_used_idx_part.rstrip(')')

            # Ensure gres_total_parts has the correct format for total GPUs
            if len(gres_total_parts) == 3 and gres_total_parts[0] == "gpu":
                _, _, total_gpu_part = gres_total_parts
                total_gpu = int(total_gpu_part)
        except (ValueError, IndexError) as e:
            self.log.debug(
                "Invalid GPU data: gres:'%s', gres_used:'%s'. Skipping GPU metric submission. Error: %s",
                gres,
                gres_used,
                e,
            )

        gpu_tags = [f"slurm_partition_gpu_type:{gpu_type}", f"slurm_partition_gpu_used_idx:{used_gpu_used_idx}"]

        _tags = tags + gpu_tags
        if total_gpu is not None:
            self.gauge(f'{namespace}.gpu_total', total_gpu, _tags)
        if used_gpu_count is not None:
            self.gauge(f'{namespace}.gpu_used', used_gpu_count, _tags)

        return gpu_tags

    def _process_tags(self, data, map, tags):
        for tag_info in map:
            value = data[tag_info["index"]]

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
                        value = value.replace(key, '').strip()
                        tags.append(f'sinfo_state_code:{mapped_value}')
                        break

            tags.append(f'{tag_info["name"]}:{value}')

        return tags

    def _process_metrics(self, data, metrics_map, tags):
        for metric_info in metrics_map["metrics"]:
            metric_value_str = data[metric_info["index"]]

            if metric_value_str.strip() == '':
                self.log.debug("Empty metric value for '%s'. Skipping.", metric_info["name"])
                continue

            try:
                metric_value = float(metric_value_str)
            except ValueError:
                self.log.debug("Invalid metric value '%s' for '%s'. Skipping.", metric_value_str, metric_info["name"])
                continue

            self.gauge(metric_info["name"], metric_value, tags)

    @AgentCheck.metadata_entrypoint
    def collect_metadata(self):
        # Leaving this one as a try because the metadata version collection isn't all that important
        # even if it fails and thus should not stop the check from running.
        try:
            # slurm 21.08.6\n
            out, err, ret = get_subprocess_output([self.sinfo_partition_cmd[0], '--version'])
            if ret != 0:
                self.log.error("Error running sinfo --version: %s", err)
            elif out:
                self.log.debug("Processing sinfo --version output: %s", out)
                version_out = out.split(' ')[1].strip()
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
