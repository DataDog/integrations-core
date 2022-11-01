# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging
import threading
import time
from collections import defaultdict

import pywintypes
import win32pdh

try:
    import datadog_agent
except ImportError:
    datadog_agent = None

from ....utils.time import get_precise_time


class WindowsPerformanceObjectRefresher(threading.Thread):
    def __init__(self):
        name = self.__class__.__name__
        super(WindowsPerformanceObjectRefresher, self).__init__(name=name)

        # If not specified in configuration, "interval's" default value is 0, which effectively
        # disables a call to PdhEnumObjects() API. Microsoft requires to call this function
        # before number calling an API like PdhEnumObjectItems(). However there are a few
        # problems with PdhEnumObjects() API call and it should be avoided if possible:
        #   a) It is extremely slow (may take seconds and allocate/free memory 300,000 times).
        #   b) Will generate warnings and errors in Windows Event logs is Agent service has
        #      no Administrator rights.
        # One cannot use PdhEnumObjectItems() to discover up-to-date counters and instances names
        # without calling PdhEnumObjects(refresh=True) first. But on the other hand performance
        # Objects and their Counters are already known and specified in the Agent configuration.
        # There is also a matter of up-to-date instance names. But we do not have to get them
        # from PdhEnumObjectItems() and instead can get them from PdhGetFormattedCounterArray().
        #
        # But here is a caveat. If some performance Objects and Counters are not installed yet
        # and installed after Agent started, they still will not be "visible" for PDH API calls
        # unless Agent is restarted or calls PdhEnumObjects(refresh=True). This is not common
        # scenario though, since Performance Counters Providers are not frequently installed or
        # uninstalled. However if this rare case is needed to be supported a customer will need
        # to set global "windows_counter_refresh_interval" configuration to a number of second
        # how often the counters should be refreshed. The only additional recommendation in this
        # case would running Agent as Local System or Local Administrator user because
        # otherwise these call will generate handful of errors and warning in Windows Event
        # Logs every time PdhEnumObjects() API is called.
        #
        # It worth to point that other parts of Agent code or 3rd party libraries may invoke
        # PdhEnumObjects(refresh=True), however it does not change above mentioned assertions.

        self.interval = 0
        if datadog_agent and datadog_agent.get_config('windows_counter_refresh_interval') is not None:
            self.interval = datadog_agent.get_config('windows_counter_refresh_interval')

        self.logger = logging.getLogger(name)
        self.logger.info('Windows Counters refresh interval set to %d seconds', self.interval)
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
                if server in self.last_refresh and now - self.last_refresh[server] < self.interval:
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

            time.sleep(1)

    def add_server(self, server):
        self.servers[server] += 1
        self.log_server_count(server)

    def remove_server(self, server):
        self.servers[server] -= 1
        self.log_server_count(server)

    def log_server_count(self, server):
        self.logger.info('Refresh counter set to %d for server: %s', self.servers[server], server)

    def get_last_refresh(self, server):
        if server in self.last_refresh:
            return self.last_refresh[server]

        return 0
