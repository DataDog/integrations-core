import re


class NetworkRest:
    def __init__(self, log, http, endpoint):
        self.log = log
        self.http = http
        self.endpoint = endpoint

    def get_response_time(self):
        response = self.http.get('{}/'.format(self.endpoint))
        response.raise_for_status()
        self.log.debug("response: %s", response.json())
        return response.elapsed.total_seconds() * 1000

    def get_quotas(self, project_id):
        response = self.http.get('{}/v2.0/quotas/{}'.format(self.endpoint, project_id))
        response.raise_for_status()
        self.log.debug("response: %s", response.json())
        return {
            re.sub('((?<=[a-z0-9])[A-Z]|(?!^)[A-Z](?=[a-z]))', r'_\1', key).lower(): value
            for key, value in response.json()['quota'].items()
            if isinstance(value, (int, float))
        }