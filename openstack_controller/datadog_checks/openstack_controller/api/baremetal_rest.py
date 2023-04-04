# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
class BaremetalRest:
    def __init__(self, log, http, endpoint, microversion):
        self.log = log
        self.http = http
        self.endpoint = endpoint
        self.microversion = microversion

    def get_response_time(self):
        url = '{}'.format(self.endpoint)
        self.log.debug("GET %s", url)
        response = self.http.get(url)
        response.raise_for_status()
        self.log.debug("response: %s", response.json())
        return response.elapsed.total_seconds() * 1000

    def get_nodes(self):
        use_legacy_resource = not self.microversion or float(self.microversion) < 1.43
        resource = 'nodes/detail' if use_legacy_resource else '/nodes?detail=True'
        response = self.http.get('{}/{}'.format(self.endpoint, resource))
        response.raise_for_status()
        self.log.debug("Nodes response: %s", response.json())
        node_metrics = []
        for node in response.json()['nodes']:
            node_metrics.append(
                {
                    'node_name': node.get('name'),
                    'node_uuid': node.get('uuid'),
                    'power_state': node.get('power_state'),
                    'conductor_group': node.get('conductor_group'),
                    'maintenance': node.get('maintenance'),
                }
            )
        return node_metrics

    def get_conductors(self):
        response = self.http.get('{}/conductors'.format(self.endpoint))
        response.raise_for_status()
        self.log.debug("Conductors response: %s", response.json())
        conductor_metrics = {}
        for conductor in response.json()['conductors']:
            conductor_metrics[conductor['hostname']] = {
                'hostname': conductor['hostname'],
                'conductor_group': conductor['conductor_group'],
                'alive': conductor['alive'],
            }
        return conductor_metrics
