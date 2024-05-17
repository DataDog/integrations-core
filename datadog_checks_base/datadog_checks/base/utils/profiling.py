# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from threading import Lock


class Profiling(object):
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Profiling, cls).__new__(cls)
            cls._instance._running = False
            cls._instance._profiler = None
            cls._instance._mutex = Lock()
            cls._instance._profiling_imported = False

        return cls._instance

    def start(self):
        with self._mutex:
            if not self._running and self._profiler is None:
                if not self._profiling_imported:
                    from ddtrace.profiling import Profiler

                    self._profiling_imported = True

                self._profiler = Profiler(service="datadog-agent-integrations")
                self._profiler.start()
                self._running = True
            if not self._running and self._profiler is not None:
                # This branch is exercise if we have previously stopped the profiler
                if self._profiler.status != "running":
                    self._profiler.start()
                    self._running = True

    def stop(self):
        with self._mutex:
            if self._running:
                self._profiler.stop()
                self._running = False
