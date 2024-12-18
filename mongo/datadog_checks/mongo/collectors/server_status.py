# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.mongo.collectors.base import MongoCollector


class ServerStatusCollector(MongoCollector):
    """The main collector, performs the 'serverStatus' command and forwards metrics to Datadog."""

    op_map = {
        'reads': {'query', 'getmore'},
        'writes': {'insert', 'update', 'delete'},
        'commands': {'command'},
    }

    def __init__(self, check, db_name, tags, tcmalloc=False):
        super(ServerStatusCollector, self).__init__(check, tags)
        self.collect_tcmalloc_metrics = tcmalloc
        self.db_name = db_name

    def compatible_with(self, deployment):
        # Can be run on any node.
        return True

    def __calculate_oplatency_avg(self, oplatencies, opcounters):
        """Calculate the average operation latency."""
        for op, latency in oplatencies.items():
            if op in self.op_map:
                mapped_ops = self.op_map[op]
                opcounts = sum(opcounters.get(mapped_op, 0) for mapped_op in mapped_ops)
                if opcounts > 0:
                    latency['latency_avg'] = round(latency.get('latency', 0) / opcounts, 1)
        return oplatencies

    def collect(self, api):
        db = api[self.db_name]
        # No need to check for `result['ok']`, already handled by pymongo
        payload = db.command('serverStatus', tcmalloc=self.collect_tcmalloc_metrics)

        # If these keys exist, remove them for now as they cannot be serialized.
        payload.get('backgroundFlushing', {}).pop('last_finished', None)
        payload.pop('localTime', None)

        # Calculate average oplatency
        if payload.get('opLatencies') and payload.get('opcounters'):
            oplatencies = self.__calculate_oplatency_avg(payload.get('opLatencies'), payload.get('opcounters'))
            payload['opLatencies'] = oplatencies

        self._submit_payload(payload)
