import re


class ComputeRest:
    def __init__(self, log, http, endpoint):
        self.log = log
        self.http = http
        self.endpoint = endpoint

    def get_response_time(self):
        response = self.http.get('{}'.format(self.endpoint))
        response.raise_for_status()
        self.log.debug("response: %s", response.json())
        return response.elapsed.total_seconds() * 1000

    def get_limits(self, project_id):
        response = self.http.get('{}/limits?project_id={}'.format(self.endpoint, project_id))
        response.raise_for_status()
        self.log.debug("response: %s", response.json())
        return {
            re.sub('((?<=[a-z0-9])[A-Z]|(?!^)[A-Z](?=[a-z]))', r'_\1', key).lower(): value
            for key, value in response.json()['limits']['absolute'].items()
            if isinstance(value, (int, float)) and not isinstance(value, bool)
        }

    def get_quota_set(self, project_id):
        response = self.http.get('{}/os-quota-sets/{}'.format(self.endpoint, project_id))
        response.raise_for_status()
        self.log.debug("response: %s", response.json())
        return {
            re.sub('((?<=[a-z0-9])[A-Z]|(?!^)[A-Z](?=[a-z]))', r'_\1', key).lower(): value
            for key, value in response.json()['quota_set'].items()
            if isinstance(value, (int, float)) and not isinstance(value, bool)
        }

    def get_servers(self, project_id):
        response = self.http.get('{}/servers/detail?project_id={}'.format(self.endpoint, project_id))
        response.raise_for_status()
        self.log.debug("response: %s", response.json())
        server_metrics = {}
        for server in response.json()['servers']:
            try:
                response = self.http.get('{}/servers/{}/diagnostics'.format(self.endpoint, server['id']))
                response.raise_for_status()
                self.log.debug("response: %s", response.json())
                server_metrics[server['id']] = {
                    'name': server['name'],
                    'metrics': {
                        re.sub('((?<=[a-z0-9])[A-Z]|(?!^)[A-Z](?=[a-z]))', r'_\1', key).lower(): value
                        for key, value in response.json().items()
                        if isinstance(value, (int, float)) and not isinstance(value, bool)
                    },
                }
            except Exception as e:
                self.log.error("Exception: %s", e)
        return server_metrics

    def get_flavors(self):
        response = self.http.get('{}/flavors/detail'.format(self.endpoint))
        response.raise_for_status()
        self.log.debug("response: %s", response.json())
        flavor_metrics = {}
        for flavor in response.json()['flavors']:
            flavor_metrics[flavor['id']] = {
                'name': flavor['name'],
                'metrics': {
                    re.sub('((?<=[a-z0-9])[A-Z]|(?!^)[A-Z](?=[a-z]))', r'_\1', key).lower(): value
                    for key, value in flavor.items()
                    if isinstance(value, (int, float)) and not isinstance(value, bool)
                },
            }
        return flavor_metrics
