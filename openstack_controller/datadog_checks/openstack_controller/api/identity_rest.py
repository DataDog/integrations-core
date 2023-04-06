# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
class IdentityRest:
    def __init__(self, log, http, endpoint):
        self.log = log
        self.http = http
        self.endpoint = endpoint

    def get_response_time(self):
        response = self.http.get('{}'.format(self.endpoint))
        response.raise_for_status()
        self.log.debug("response: %s", response.json())
        return response.elapsed.total_seconds() * 1000

    def get_domains(self):
        response = self.http.get('{}/domains'.format(self.endpoint))
        response.raise_for_status()
        self.log.debug("response: %s", response.json())
        return response.json()['domains']

    def get_projects(self):
        response = self.http.get('{}/projects'.format(self.endpoint))
        response.raise_for_status()
        self.log.debug("response: %s", response.json())
        return response.json()['projects']

    def get_users(self):
        response = self.http.get('{}/users'.format(self.endpoint))
        response.raise_for_status()
        self.log.debug("response: %s", response.json())
        return response.json()['users']
