# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base import AgentCheck


class DruidCheck(AgentCheck):
    # TODO: Use http.RequestsWrapper

    def check(self, instance):
        pass

# TAGS:
#   - druid service name e.g. druid/broker

# TODO: Handle version
# etcd.server.version,gauge,,item,,Which version is running. 1 for 'server_version' label with current version.,0,etcd,
