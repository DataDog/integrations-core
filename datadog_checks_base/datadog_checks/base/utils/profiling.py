# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from threading import Lock


class Profiling(object):
    def __init__(self):
        self._profiler = None
        self._running = False
        self._mutex = Lock()

    def start(self):
        with self._mutex:
            if not self._running and self._profiler is None:
                from ddtrace.profiling import Profiler

                self._profiler = Profiler(service="datadog-agent-integrations")
                self._profiler.start()
                self._running = True
            if not self._running and self._profiler is not None:
                # This branch is exercise if we have previously stopped the profiler
                if self._profiler.status != "running":
                    self._profiler.start()
                    self._running = True

    def stop(self):
        if not self._running:
            return

        with self._mutex:
            if self._running:
                self._profiler.stop()
                self._running = False


PROFILING = Profiling()
