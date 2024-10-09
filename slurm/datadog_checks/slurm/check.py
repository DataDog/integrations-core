# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import subprocess
from typing import Any  # noqa: F401
import time

from datadog_checks.base import AgentCheck  # noqa: F401

from .config_models import ConfigMixin


SINFO_PARTITION_PARAMS = ["-hO", "Partition:|,NodeList:|,CPUs:|,Available:|,Memory:|,Cluster:|,NodeAIOT:|,"]
SINFO_NODE_PARAMS = ["-NO", "PartitionName:|,Available:|,NodeList:|,NodeAIOT:|,Memory:|,Cluster:|,"]
SINFO_ADDITIONAL_NODE_PARAMS = "Cluster:|,CPUsLoad:|,FreeMem:|,Disk:|,StateLong:|,Reason:|,features_act:|,Threads:|,"
GPU_PARAMS = "Gres:|,GresUsed:|,"
SQUEUE_PARAMS = ["-ho", "%A|%u|%j|%T|%N|%C|%R|%m"]
SSHARE_PARAMS = ["-lnpU"]
SACCT_PARAMS = [
    "-npo",
    "JobID,JobName%40,Partition,Account,AllocCPUs,AllocTRES%40,Elapsed,CPUTimeRAW,MaxRSS,MaxVMSize,AveCPU,AveRSS,State,ExitCode,Start,End,NodeList",
    "--units=M",
    f"--starttime=now-15seconds",
]


def get_subprocess_out(cmd):
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout, result.stderr, result.returncode


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
            commands.append(('snode', self.sinfo_node_cmd, self.process_snode))

        for name, cmd, process_func in commands:
            out, err, ret = self.get_subprocess_out(cmd)
            if ret != 0:
                self.log.error(f"Error running {name}: {err}")
            else:
                process_func(out)

    def process_sinfo_partition(self, output: str):
        # normal*|c[1-2]|1|up|1000|N/A|0/2/0/2|(null)|
        lines = output.strip().split('\n')
        for line in lines:
            partition_data = line.split('|')
            partition_name = partition_data[0]
            if partition_name.endswith('*'):
                # normal*
                partition_name = partition_name.rstrip('*')
                default_partition_tag = "slurm_default_partition:true"
            else:
                default_partition_tag = "slurm_default_partition:false"

            tags = [
                f"slurm_partition_name:{partition_name}",
                f"slurm_partition_node_list:{partition_data[1]}",
                f"slurm_partition_cpus_assigned:{partition_data[2]}",
                f"slurm_partition_state:{partition_data[3]}",
                f"slurm_partition_memory_assigned:{partition_data[4]}",
                f"slurm_partition_available:{partition_data[5]}",
                default_partition_tag,
            ]
            if self.gpu_stats:
                gpu_total, gpu_allocated, gpu_tags = self._process_sinfo_gpu(
                    partition_data[6], partition_data[7]
                )
                tags += gpu_tags
                self.gauge('slurm.partition.gpu.total', gpu_total, tags=tags)
                self.gauge('slurm.partition.gpu.allocated', gpu_allocated, tags=tags)

            allocated, idle, other, total = self._process_sinfo_cpu_state(partition_data[6], tags)

            self.gauge('slurm.partition', 1, tags=tags)
            self.gauge('slurm.partition.cpu.allocated', allocated, tags=tags)
            self.gauge('slurm.partition.cpu.idle', idle, tags=tags)
            self.gauge('slurm.partition.cpu.other', other, tags=tags)
            self.gauge('slurm.partition.cpu.total', total, tags=tags)

    def _process_sinfo_cpu_state(self, cpus_state: str):
        # "0/2/0/2"
        allocated, idle, other, total = cpus_state.split('/')
        return int(allocated), int(idle), int(other), int(total)

    def _process_sinfo_gpu(self, gres: str, gres_used: str):
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

        return (
            total_gpu,
            used_gpu_count,
            [f"slurm_partition_gpu_type:{gpu_type},slurm_partition_gpu_used_idx:{used_gpu_used_idx}"],
        )

    def process_sinfo_node(self, output):
        # PARTITION |AVAIL |NODELIST |NODES(A/I/O/T) |MEMORY |CLUSTER |CPU_LOAD |FREE_MEM |TMP_DISK |STATE |REASON |ACTIVE_FEATURES |THREADS |GRES      |GRES_USED |
        # normal    |up    |c1       |0/1/0/1        |  1000 |N/A     |    1.84 |    5440 |       0 |idle  |none   |(null)          |      1 |(null)    |(null)    |
        for line in output.strip().split('\n'):
            node_data = line.split('|')
            tags = self._create_node_tags(node_data)

            # Process GPU data if enabled
            if self.gpu_stats:
                if self.sinfo_collection_level == 2:
                    gpu_total, gpu_allocated, gpu_tags = self._process_sinfo_gpu(
                        node_data[13], node_data[14]
                    )
                else:
                    gpu_total, gpu_allocated, gpu_tags = self._process_sinfo_gpu(
                        node_data[6], node_data[7]
                    )

            tags += gpu_tags
            allocated, idle, other, total = self._process_sinfo_cpu_state(node_data[4], tags)

            # Submit new gauges
            self.gauge('slurm.node.cpu.allocated', allocated, tags=tags)
            self.gauge('slurm.node.cpu.idle', idle, tags=tags)
            self.gauge('slurm.node.cpu.other', other, tags=tags)
            self.gauge('slurm.node.cpu.total', total, tags=tags)
            self.gauge('slurm.node.gpu.total', gpu_total, tags=tags)
            self.gauge('slurm.node.gpu.allocated', gpu_allocated, tags=tags)
            self.gauge('slurm.node.cpu_load', float(node_data[6]), tags=tags)
            self.gauge('slurm.node.free_mem', int(node_data[7]), tags=tags)
            self.gauge('slurm.node.tmp_disk', int(node_data[8]), tags=tags)
            self.gauge('slurm.node.info', 1, tags=tags)

    def _create_node_tags(self, node_data):
        tag_fields = [
            ('slurm_partition', 0),
            ('slurm_node_availability', 1),
            ('slurm_node_name', 2),
            ('slurm_node_memory', 4),
            ('slurm_node_cluster', 5),
        ]
        if self.sinfo_collection_level > 2:
            tag_fields += [
                ('slurm_node_state', 9),
                ('slurm_node_reason', 10),
                ('slurm_node_active_features', 11),
                ('slurm_node_threads', 12)
            ]
        return [f"{field}:{node_data[index].strip()}" for field, index in tag_fields]

    def process_squeue(self, output):
        # JOBID |      USER |      NAME |   STATE |            NODELIST |      CPUS |   NODELIST(REASON) | MIN_MEMORY
        #    31 |      root |      wrap | PENDING |                     |         1 |        (Resources) |       500M  
        for line in output.strip().split('\n'):
            job_data = line.split('|')
            tags = [
                f"slurm_job_id:{job_data[0]}",
                f"slurm_job_user:{job_data[1]}",
                f"slurm_job_name:{job_data[2]}",
                f"slurm_job_state:{job_data[3]}",
                f"slurm_job_node_list:{job_data[4]}",
                f"slurm_job_cpus:{job_data[5]}",
                f"slurm_job_reason:{job_data[6]}",
                f"slurm_job_tres_per_node:{job_data[7]}",
            ]
            self.gauge('slurm.job.info', 1, tags=tags)
    
    def process_sacct(self, output):
        # JobID    |JobName |Partition|Account|AllocCPUS|AllocTRES                       |Elapsed  |CPUTimeRAW|MaxRSS|MaxVMSize|AveCPU|AveRSS |State   |ExitCode|Start               |End     |NodeList   |
        # 36       |test.py |normal   |root   |1        |billing=1,cpu=1,mem=500M,node=1 |00:00:03 |3         |      |         |      |       |RUNNING |0:0     |2024-09-24T12:00:01 |Unknown |c1         |
        # 36.batch |batch   |         |root   |1        |cpu=1,mem=500M,node=1           |00:00:03 |3         |      |         |      |       |RUNNING |0:0     |2024-09-24T12:00:01 |Unknown |c1         |
        for line in output.strip().split('\n'):
            job_data = line.split('|')
            tags = [
                f"slurm_job_id:{job_data[0]}",
                f"slurm_job_name:{job_data[1]}",
                f"slurm_job_partition:{job_data[2]}",
                f"slurm_job_account:{job_data[3]}",
                f"slurm_job_cpus:{job_data[4]}",
                f"slurm_job_tres_per_node:{job_data[5]}",
                f"slurm_job_elapsed:{job_data[6]}",
                f"slurm_job_cputime:{job_data[7]}",
                f"slurm_job_maxrss:{job_data[8]}",
                f"slurm_job_maxvm:{job_data[9]}",
                f"slurm_job_avecpu:{job_data[10]}",
                f"slurm_job_averss:{job_data[11]}",
                f"slurm_job_state:{job_data[12]}",
                f"slurm_job_exitcode:{job_data[13]}",
                f"slurm_job_start:{job_data[14]}",
                f"slurm_job_end:{job_data[15]}",
                f"slurm_job_node_list:{job_data[16]}",
            ]
            self.gauge('slurm.job.info', 1, tags=tags)
    
    def process_sdiag(self, output):
        metrics = {}
        metric_map = {
            'server_thread_count': 'Server thread count:',
            'queue_size': 'Last queue length:',
            'dbd_agent_queue_size': 'DBD Agent queue size:',
            'last_cycle': 'Last cycle:',
            'mean_cycle': 'Mean cycle:',
            'cycles_per_minute': 'Cycles per minute:',
            'backfill_total_jobs_since_start': 'Total backfilled jobs (since last slurm start):',
            'backfill_total_jobs_since_cycle_start': 'Total backfilled jobs (since last stats cycle start):',
            'backfill_total_heterogeneous_components': 'Total backfilled heterogeneous job components:'
        }

        for line in output.split('\n'):
            for metric, pattern in metric_map.items():
                if pattern in line:
                    metrics[metric] = int(line.split(':')[1].strip())
                    break
            
            if 'Backfilling stats' in line:
                backfill_section = True
            elif backfill_section and 'Last cycle:' in line:
                metrics['backfill_last_cycle'] = int(line.split(':')[1].strip())
            elif backfill_section and 'Max cycle:' in line:
                metrics['backfill_max_cycle'] = int(line.split(':')[1].strip())
            elif 'Last depth cycle:' in line:
                metrics['backfill_depth_mean'] = int(line.split(':')[1].strip())

        return metrics
    
    def process_sshare(self, output):
        # Account |User |RawShares |NormShares |RawUsage |NormUsage |EffectvUsage |FairShare |LevelFS  |GrpTRESMins |TRESRunMins                                                    |
        # root    |root |        1 |           |       0 |          |    0.000000 | 0.000000 |0.000000 |            |cpu=0,mem=0,energy=0,node=0,billing=0,fs/disk=0,vmem=0,pages=0 |
        for line in output.strip().split('\n'):
            share_data = line.split('|')
            tags = [
                f"slurm_account:{share_data[0]}",
                f"slurm_user:{share_data[1]}",
                f"slurm_group_tres_mins:{share_data[9]}",
                f"slurm_tres_run_mins:{share_data[10]}",
            ]

            self.gauge('slurm.share.raw_shares', share_data[2], tags=tags)
            self.gauge('slurm.share.norm_shares', share_data[3], tags=tags)
            self.gauge('slurm.share.raw_usage', share_data[4], tags=tags)
            self.gauge('slurm.share.norm_usage', share_data[5], tags=tags)
            self.gauge('slurm.share.effective_usage', share_data[6], tags=tags)
            self.gauge('slurm.share.fair_share', share_data[7], tags=tags)
            self.gauge('slurm.share.level_fs', share_data[8], tags=tags)