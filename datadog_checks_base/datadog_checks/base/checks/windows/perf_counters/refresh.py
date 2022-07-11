# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging
import threading
import time
from collections import defaultdict

import pywintypes
import win32pdh

from ....utils.time import get_precise_time


class WindowsPerformanceObjectRefresher(threading.Thread):
    INTERVAL = 60

    def __init__(self):
        name = self.__class__.__name__
        super(WindowsPerformanceObjectRefresher, self).__init__(name=name)

        self.logger = logging.getLogger(name)
        self.last_refresh = {}
        self.servers = defaultdict(int)

    def run(self):
        # Refresh the list of performance objects for every server, see:
        # https://docs.microsoft.com/en-us/windows/win32/api/pdh/nf-pdh-pdhenumobjectitemsa#remarks
        #
        # We do this in a separate thread to avoid internal lock contention of Windows APIs
        while True:
            # Agent is shutting down
            if not any(self.servers.values()):
                return

            for server, count in self.servers.items():
                if not count:
                    continue

                now = get_precise_time()
                if server in self.last_refresh and now - self.last_refresh[server] < self.INTERVAL:
                    continue

                self.logger.info('Refreshing performance objects for server: %s', server)
                try:
                    # https://docs.microsoft.com/en-us/windows/win32/api/pdh/nf-pdh-pdhenumobjectsa
                    # https://mhammond.github.io/pywin32/win32pdh__EnumObjects_meth.html
                    win32pdh.EnumObjects(None, server, win32pdh.PERF_DETAIL_WIZARD, True)
                except pywintypes.error as error:
                    self.logger.error(
                        'Error refreshing performance objects for server `%s`: %s', server, error.strerror
                    )
                else:
                    self.logger.info('Successfully refreshed performance objects for server: %s', server)

                self.last_refresh[server] = now

            time.sleep(2)

    def add_server(self, server):
        self.servers[server] += 1
        self.log_server_count(server)

    def remove_server(self, server):
        self.servers[server] -= 1
        self.log_server_count(server)

    def log_server_count(self, server):
        self.logger.info('Refresh counter set to %d for server: %s', self.servers[server], server)
