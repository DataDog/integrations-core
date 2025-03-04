# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import glob
import os

from typing import Any  # noqa: F401

from datadog_checks.base import AgentCheck # noqa: F401

class InfinibandCheck(AgentCheck):

    # This will be the prefix of every metric and service check the integration sends
    __NAMESPACE__ = 'infiniband'

    def __init__(self, name, init_config, instances):
        super(InfinibandCheck, self).__init__(name, init_config, instances)
        self.tags = self.instance.get('tags', [])
        self.base_path = self.instance.get('infiniband_path', '/sys/class/infiniband')
        # Test to see if the path exist. In containerized environments it's customary to mount it to /host
        if not os.path.exists(self.base_path):
            alternative_path = os.path.join('/host', self.base_path.lstrip('/'))
            if os.path.exists(alternative_path):
                self.base_path = alternative_path
            else:
                raise Exception(f"Path {self.base_path} and {alternative_path} does not exist")


    def check(self, _):
        for device in os.listdir(self.base_path):
            dev_path = os.path.join(self.base_path, device, "ports")
            if not os.path.isdir(dev_path):
                continue

            for port in os.listdir(dev_path):
                port_path = os.path.join(dev_path, port)

                tags = self.tags + ["device:{}".format(device), "port:{}".format(port)]

                counters_path = os.path.join(port_path, "counters")
                if os.path.isdir(counters_path):
                    for file in glob.glob(f"{counters_path}/*"):
                        filename = os.path.basename(file)
                        with open(file, "r") as f:
                            self.gauge(f"infiniband.{filename}", int(f.read()), tags=tags)

                hw_counters_path = os.path.join(port_path, "hw_counters")
                if os.path.isdir(hw_counters_path):
                    for file in glob.glob(f"{hw_counters_path}/*"):
                        filename = os.path.basename(file)
                        with open(file, "r") as f:
                            self.gauge(f"rdma.{filename}", int(f.read()), tags=tags)
