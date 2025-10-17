# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import subprocess


class LSFClient:
    def __init__(self):
        pass

    def _run_command(self, command):
        try:
            result = subprocess.run(command, timeout=5, capture_output=True, text=True)
            return result.stdout, result.stderr, result.returncode
        except Exception as e:
            return None, e, 1

    def start_monitoring(self, sample_period):
        return self._run_command(['badmin', 'perfmon', 'start', sample_period])

    def lsid(self):
        return self._run_command(['lsid'])

    def lsclusters(self):
        return self._run_command(['lsclusters', '-w'])

    def bhosts(self):
        return self._run_command(['bhosts', '-w'])

    def lshosts(self):
        return self._run_command(
            [
                'lshosts',
                '-o',
                '"HOST_NAME:50 type:30  model:30  cpuf: ncpus: maxmem: maxswp: server: RESOURCES: rexpri: nprocs: ncores: nthreads: maxtmp:"',  # noqa: E501
            ]
        )
