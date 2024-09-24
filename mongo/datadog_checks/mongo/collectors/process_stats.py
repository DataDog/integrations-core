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
        self._process = None

    @property
    def is_localhost(self):
        return 'localhost' in self._clean_server_name or '127.0.0.1' in self._clean_server_name

    def compatible_with(self, deployment):
        # Can only be run on self-hosted MongoDB running on the same host as the Agent.
        self.log.debug(
            "Checking compatibility of the ProcessStatsCollector with %s, %s, %s",
            deployment.hosting_type,
            self._clean_server_name,
            self.is_localhost,
        )
        return deployment.hosting_type == HostingType.SELF_HOSTED and self.is_localhost

    def _get_pid_and_process_name(self, api):
        """Fetch PID and process name from MongoDB serverStatus."""
        try:
            server_status = api.server_status()
            pid = server_status.get("pid")
            process_name = server_status.get("process")
            if not pid or not process_name:
                self.log.warning("PID or process name not found in serverStatus.")
            return pid, process_name
        except OperationFailure as e:
            self.log.warning("Failed to retrieve serverStatus: %s", e)
            return None, None

    def _find_process_by_pid(self, pid):
        """Return the process object for a given PID, or None if not found."""
        try:
            return psutil.Process(pid)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            self.log.warning("Process with PID %s not found or access denied.", pid)
            return None

    def _find_process_by_name(self, process_name):
        """Find and return the PID of a process by its name."""
        if not process_name:
            self.log.warning("No process name provided.")
            return None
        for process in psutil.process_iter(["pid", "name"]):
            if process.info["name"] == process_name:
                return process
        self.log.warning("No process found with the name %s.", process_name)
        return None

    def _get_mongo_process(self, api):
        """Retrieve the MongoDB process using either PID or process name."""
        if self._process:
            return self._process

        # Try to get the PID and process name from serverStatus
        pid, process_name = self._get_pid_and_process_name(api)

        # Attempt to get the process by PID
        process = self._find_process_by_pid(pid) if pid else None

        # If process not found by PID, attempt to find it by process name
        if not process or process.name() != process_name:
            process = self._find_process_by_name(process_name)

        if not process:
            self.log.warning("Unable to retrieve MongoDB process.")

        self._process = process
        return self._process

    def collect(self, api):
        process = self._get_mongo_process(api)
        if not process:
            return

        try:
            if (cpu_percent := process.cpu_percent()) != 0:
                # the first call of cpu_percent is 0.0 and should be ignored
                # the cpu_percent can be > 100% if the process has multiple threads
                self._submit_payload({"system": {"cpu_percent": cpu_percent}})
            else:
                self.log.warning("The MongoDB process with PID %s is not consuming CPU", process.pid)
        except Exception as e:
            self.log.error("Failed to collect process stats for MongoDB process with PID %s: %s", process.pid, e)
