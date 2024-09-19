# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import psutil
from pymongo.errors import OperationFailure

from datadog_checks.mongo.collectors.base import MongoCollector
from datadog_checks.mongo.common import HostingType


class ProcessStatsCollector(MongoCollector):
    """
    Collects process stats for a mongod or mongos node.
    This collector is only compatible with self-hosted MongoDB running on the same host as the Agent.
    """

    def __init__(self, check, tags):
        super(ProcessStatsCollector, self).__init__(check, tags)
        self._clean_server_name = check._config.clean_server_name

    @property
    def is_localhost(self):
        return 'localhost' in self._clean_server_name or '127.0.0.1' in self._clean_server_name

    def compatible_with(self, deployment):
        # Can only be run on self-hosted MongoDB running on the same host as the Agent.
        return deployment.hosting_type == HostingType.SELF_HOSTED and self.is_localhost

    def _get_pid_and_name(self, api):
        server_status = api.server_status()
        return server_status.get("pid"), server_status.get("process")

    def collect(self, api):
        pid = None
        try:
            pid, process_name = self._get_pid_and_name(api)
        except OperationFailure as e:
            self.log.warning("Failed to get the PID of the mongod process: %s", e)
            return

        if pid:
            try:
                process = psutil.Process(pid)
                cpu_percent = process.cpu_percent()
                if cpu_percent != 0:
                    # the first call of cpu_percent is 0.0 and should be ignored
                    self._submit_payload({"system": {"cpu_percent": cpu_percent}})
            except psutil.NoSuchProcess:
                self.log.warning("The %s process with PID %s is not running", process_name, pid)
            except psutil.AccessDenied:
                self.log.warning(
                    "The Agent does not have permission to collect process stats for the %s process with PID %s",
                    process_name,
                    pid,
                )
            except Exception as e:
                self.log.error("Failed to collect process stats for %s process with PID %s: %s", process_name, pid, e)
