# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any  # noqa: F401
import os

from datadog_checks.base import AgentCheck  # noqa: F401
import subprocess
from .config_models import ConfigMixin


SINFO_FLAGS = ["-ho", "%R|%n|%t|%c|%m|%e|%a"]
SQUEUE_FLAGS = ["-ho", "%A|%u|%j|%T|%N|%C|%R|%M"]
SSHARE_FLAGS = ["-hp"]
SACCT_FLAGS = ["-ho", "JobID|JobName%100|Partition|Account|AllocCPUs|AllocTRES%100|Elapsed|CPUTimeRAW|MaxRSS|MaxVMSize|AveCPU|AveRSS|State|ExitCode|Start|End|NodeList", "--parsable2", "--units=M", f"--starttime=now-{time_diff}seconds"]
SDIAG_FLAGS = ["--parsable2"]

def get_subprocess_out(cmd):
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout, result.stderr, result.returncode

class SlurmCheck(AgentCheck, ConfigMixin):

    # This will be the prefix of every metric and service check the integration sends
    __NAMESPACE__ = 'slurm'

    def __init__(self, name, init_config, instances):
        super(SlurmCheck, self).__init__(name, init_config, instances)
        slurm_binaries_path = self.init_config.get('slurm_binaries_path', '/usr/bin/')
        
        sinfo_cmd = self.instance.get('sinfo_path', os.path.join(slurm_binaries_path, 'sinfo'))
        squeue_cmd = self.instance.get('squeue_path', os.path.join(slurm_binaries_path, 'squeue'))
        sshare_cmd = self.instance.get('sshare_path', os.path.join(slurm_binaries_path, 'sshare'))
        sacct_cmd = self.instance.get('sacct_path', os.path.join(slurm_binaries_path, 'sacct'))
        sdiag_cmd = self.instance.get('sdiag_path', os.path.join(slurm_binaries_path, 'sdiag'))

        self.sinfo_cmd = [sinfo_cmd] + SINFO_FLAGS
        self.squeue_cmd = [squeue_cmd] + SQUEUE_FLAGS
        self.sshare_cmd = [sshare_cmd] + SSHARE_FLAGS
        self.sacct_cmd = [sacct_cmd] + SACCT_FLAGS
        self.sdiag_cmd = [sdiag_cmd] + SDIAG_FLAGS

        gpu_stats = self.instance.get('gpu_stats', False)
        cluster_stats = self.instance.get('cluster_stats', False)

        if gpu_stats:
            self.sinfo_cmd[-1] += '|%G'
        
        if cluster_stats:
            self.sinfo_cmd[-1].replace("%n", "%N")


    def check(self, _):
        instance_config.get('sinfo_path', os.path.join(slurm_binaries_path, 'sinfo'))