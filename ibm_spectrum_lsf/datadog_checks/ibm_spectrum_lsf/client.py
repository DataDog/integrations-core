# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import subprocess

from datadog_checks.base.log import CheckLoggingAdapter


class LSFClient:
    def __init__(self, logger: CheckLoggingAdapter):
        self.log = logger

    def _run_command(self, *command: str) -> tuple[str, str, int]:
        self.log.debug("Running command: %s", command)
        try:
            result = subprocess.run(command, timeout=5, capture_output=True, text=True)
            self.log.trace("Command output: %s", result.stdout)
            return result.stdout, result.stderr, result.returncode
        except Exception as e:
            return "", str(e), 1

    def lsid(self) -> tuple[str, str, int]:
        return self._run_command('lsid')

    def lsclusters(self) -> tuple[str, str, int]:
        return self._run_command('lsclusters', '-w')

    def bhosts(self) -> tuple[str, str, int]:
        return self._run_command('bhosts', '-o', "HOST_NAME STATUS JL_U MAX NJOBS RUN SSUSP USUSP RSV delimiter='|'")

    def lshosts(self) -> tuple[str, str, int]:
        return self._run_command(
            'lshosts',
            '-o',
            "HOST_NAME:80 type:30 model:30 cpuf: ncpus: maxmem: maxswp: server: nprocs: ncores: nthreads: maxtmp: delimiter='|'",  # noqa: E501
        )

    def lsload(self) -> tuple[str, str, int]:
        return self._run_command(
            'lsload', '-o', "HOST_NAME status r15s r1m r15m ut pg io ls it tmp swp mem delimiter='|'"
        )

    def bslots(self) -> tuple[str, str, int]:
        return self._run_command('bslots')

    def bqueues(self) -> tuple[str, str, int]:
        return self._run_command(
            'bqueues', '-o', "QUEUE_NAME PRIO STATUS MAX JL_U JL_P JL_H NJOBS PEND RUN SUSP delimiter='|'"
        )

    def bjobs(self) -> tuple[str, str, int]:
        return self._run_command(
            'bjobs',
            '-o',
            "jobid stat queue user:80 proj:80 from_host:80 exec_host:80 run_time cpu_used mem time_left swap idle_factor %complete delimiter='|'",  # noqa: E501
            "-u",
            "all",
        )

    def gpuload(self) -> tuple[str, str, int]:
        return self._run_command("lsload", "-gpuload", "-w")

    def bhosts_gpu(self) -> tuple[str, str, int]:
        return self._run_command(
            "bhosts",
            "-o",
            "HOST_NAME ngpus ngpus_alloc ngpus_excl_alloc ngpus_shared_alloc ngpus_shared_jexcl_alloc ngpus_excl_avail ngpus_shared_avail delimiter='|'",  # noqa: E501
        )

    def badmin_perfmon(self) -> tuple[str, str, int]:
        return self._run_command(
            "badmin",
            "perfmon",
            "view",
            "-json",
        )

    def badmin_perfmon_start(self, min_collection_interval: float) -> tuple[str, str, int]:
        return self._run_command(
            "badmin",
            "perfmon",
            "start",
            str(min_collection_interval),
        )

    def badmin_perfmon_stop(self) -> tuple[str, str, int]:
        return self._run_command(
            "badmin",
            "perfmon",
            "stop",
        )

    def bhist(self, start_time: str, end_time: str) -> tuple[str, str, int]:
        return self._run_command(
            "bhist",
            "-C",
            f"{start_time},{end_time}",
            "-w",
            "-u",
            "all",
        )
