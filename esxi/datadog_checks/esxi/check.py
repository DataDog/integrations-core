# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any  # noqa: F401

from pyVim import connect

from datadog_checks.base import AgentCheck  # noqa: F401


class EsxiCheck(AgentCheck):
    __NAMESPACE__ = 'esxi'

    def __init__(self, name, init_config, instances):
        super(EsxiCheck, self).__init__(name, init_config, instances)
        self.esxi_url = self.instance.get("esxi_url")
        self.port = self.instance.get("port")
        self.username = self.instance.get("username")
        self.password = self.instance.get("password")
        self.tags = ["esxi_url:{}".format(self.esxi_url)]
        if self.port:
            self.tags.append("port:{}".format(self.port))

    def check(self, _):
        try:
            connection = connect.SmartConnect(host=self.esxi_url, user=self.username, pwd=self.password, port=self.port)
            self.conn = connection
            self.count("host.can_connect", 1, tags=self.tags)
        except Exception as e:
            self.log.warning("Cannot connect to ESXi host %s:%s- %s", self.esxi_url, self.port, e)
            self.count("host.can_connect", 0, tags=self.tags)
