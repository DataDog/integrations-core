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

    def _use_legacy_nodes_resource(self):
        if not self.microversion:
            return True
        legacy_microversion = False
        try:
            legacy_microversion = float(self.microversion) < 1.43
        except Exception:
            pass

        return legacy_microversion or self.microversion.lower() != 'latest'

    def collect_conductor_metrics(self):
        if not self.microversion:
            return False
        legacy_microversion = False
        try:
            legacy_microversion = float(self.microversion) < 1.49
        except Exception:
            pass

        return not legacy_microversion

    def get_nodes(self):
        resource = 'nodes/detail' if self._use_legacy_nodes_resource() else '/nodes?detail=True'
        response = self.http.get('{}/{}'.format(self.endpoint, resource))
        response.raise_for_status()
        self.log.debug("Nodes response: %s", response.json())
        node_metrics = []
        for node in response.json().get('nodes'):
            is_up = 1 if node.get('maintenance') is False else 0
            node_metrics.append(
                {
                    'node_name': node.get('name'),
                    'node_uuid': node.get('uuid'),
                    'power_state': node.get('power_state'),
                    'conductor_group': node.get('conductor_group'),
                    'is_up': is_up,
                }
            )
        return node_metrics

    def get_conductors(self):
        response = self.http.get('{}/conductors'.format(self.endpoint))
        response.raise_for_status()
        self.log.debug("Conductors response: %s", response.json())
        conductor_metrics = []
        for conductor in response.json().get('conductors'):
            is_alive = 1 if conductor.get('alive') is True else 0
            conductor_metrics.append(
                {
                    'hostname': conductor.get('hostname'),
                    'conductor_group': conductor.get('conductor_group'),
                    'alive': is_alive,
                }
            )
        return conductor_metrics
