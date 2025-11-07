# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import subprocess
from typing import Optional

from datadog_checks.base.log import AgentLogger


class LSFClient:
    def __init__(self, logger: AgentLogger):
        self.log = logger

    def _run_command(self, command: list[str]) -> tuple[Optional[str], Optional[str], Optional[int]]:
        self.log.debug("Running command: %s", command)
        try:
            result = subprocess.run(command, timeout=5, capture_output=True, text=True)
            self.log.trace("Command output: %s", result.stdout)
            return result.stdout, result.stderr, result.returncode
        except Exception as e:
            return None, str(e), 1

    def start_monitoring(self, sample_period: int) -> tuple[Optional[str], Optional[str], Optional[int]]:
        return self._run_command(['badmin', 'perfmon', 'start', str(sample_period)])

    def lsid(self) -> tuple[Optional[str], Optional[str], Optional[int]]:
        return self._run_command(['lsid'])

    def lsclusters(self) -> tuple[Optional[str], Optional[str], Optional[int]]:
        return self._run_command(['lsclusters', '-w'])

    def bhosts(self) -> tuple[Optional[str], Optional[str], Optional[int]]:
        return self._run_command(['bhosts', '-o', "HOST_NAME STATUS JL_U MAX NJOBS RUN SSUSP USUSP RSV delimiter='|'"])

    def lshosts(self) -> tuple[Optional[str], Optional[str], Optional[int]]:
        return self._run_command(
            [
                'lshosts',
                '-o',
                "HOST_NAME:80 type:30 model:30 cpuf: ncpus: maxmem: maxswp: server: nprocs: ncores: nthreads: maxtmp: delimiter='|'",  # noqa: E501
            ]
        )

    def lsload(self) -> tuple[Optional[str], Optional[str], Optional[int]]:
        return self._run_command(
            ['lsload', '-o', "HOST_NAME status r15s r1m r15m ut pg io ls it tmp swp mem delimiter='|'"]
        )

    def bslots(self) -> tuple[Optional[str], Optional[str], Optional[int]]:
        return self._run_command(['bslots'])

    def bqueues(self) -> tuple[Optional[str], Optional[str], Optional[int]]:
        return self._run_command(
            ['bqueues', '-o', "QUEUE_NAME PRIO STATUS MAX JL_U JL_P JL_H NJOBS PEND RUN SUSP delimiter='|'"]
        )

    def bjobs(self) -> tuple[Optional[str], Optional[str], Optional[int]]:
        return self._run_command(
            [
                'bjobs',
                '-o',
                "jobid queue from_host:80 exec_host:80 run_time cpu_used mem time_left swap idle_factor %complete delimiter='|'",  # noqa: E501
            ]
        )

    def gpuload(self) -> tuple[Optional[str], Optional[str], Optional[int]]:
        return self._run_command(["lsload", "-gpuload", "-w"])
