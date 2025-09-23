# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.mongo.collectors.base import MongoCollector
from datadog_checks.mongo.common import ReplicaSetDeployment


class HostInfoCollector(MongoCollector):
    """
    Collects underlying system metrics that the mongod or mongos runs on using the 'hostInfo' mongo command.
    """

    def compatible_with(self, deployment):
        if isinstance(deployment, ReplicaSetDeployment) and deployment.is_arbiter:
            return False
        return True

    def collect(self, api):
        host_info = api['admin'].command('hostInfo', maxTimeMS=api._timeout)
        return self._submit_payload({'system': host_info.get('system', {})})
