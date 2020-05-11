# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any, Dict

from datadog_checks.base import AgentCheck, ConfigurationError
from datadog_checks.base.utils.http import RequestsWrapper


class MarkLogicApi(object):
    def __init__(self, http, api_url):
        # type: (RequestsWrapper, str) -> None
        self._http = http
        self._base_url = api_url + '/manage/v2'

    def get_status_data(self, resource=None, name=None, group=None):
        """
        Example url:
            - http://localhost:8002/manage/v2/hosts?view=status
            - http://localhost:8002/manage/v2/hosts?view=status&format=json (cluster level)
            - http://localhost:8002/manage/v2/forests/Security?view=status&format=json
            - http://localhost:8002/manage/v2/databases/Extensions?view=status&format=json
            - http://localhost:8002/manage/v2/hosts/2871b05b4bdc?view=status&format=json
            - http://localhost:8002/manage/v2/transactions?format=json (already in http://localhost:8002/manage/v2/hosts?view=status)
            - http://localhost:8002/manage/v2/servers?view=status&format=json (already in http://localhost:8002/manage/v2/hosts?view=status)
        """
        params = {
            'view': 'status',
            'format': 'json',
        }
        url = self._base_url

        if resource:
            url = "{}/{}".format(url, resource)
        resp = self._http.get(url, params=params)
        resp.raise_for_status()
        return resp.json()

    def get_requests_data(self, resource=None, name=None, group=None):
        """
        Example url:
            - http://localhost:8002/manage/v2/requests?format=json (cluster level)
            - http://localhost:8002/manage/v2/requests?format=json&server-id=Admin&group-id=Default
            - http://localhost:8002/manage/v2/requests?format=json&group-id=Default
            - http://localhost:8002/manage/v2/requests?format=json&host-id=2871b05b4bdc
        """
        params = {
            'format': 'json',
        }
        url = "{}/requests".format(self._base_url)
        if resource:
            params['{}-id'.format(resource)] = name
        resp = self._http.get(url, params=params)
        resp.raise_for_status()
        return resp.json()

    def get_forest_storage_data(self, name=None, group=None):
        """
        Example url:
            - http://localhost:8002/manage/v2/forests?format=json&view=storage
            - http://localhost:8002/manage/v2/forests?format=json&view=storage&database-id=Last-Login
            - http://localhost:8002/manage/v2/forests?format=json&view=storage&forest-id=Last-Login
            - http://localhost:8002/manage/v2/forests?format=json&view=storage&database-id=Security
        """
        params = {
            'format': 'json',
            'view': 'storage',
        }
        url = "{}/forests".format(self._base_url)
        if name:
            url = "{}/{}".format(url, name)
        resp = self._http.get(url, params=params)
        resp.raise_for_status()
        return resp.json()

    def get_resources(self):
        data = self._get_raw_resources()
        from pprint import pprint
        pprint(data)
        resources = {}
        for group in data['cluster-query']['relations']['relation-group']:
            resource_type = group['typeref']
            resources[resource_type] = []
            for rel in group['relation']:
                resources[resource_type].append({
                    'id': rel['idref'],
                    'name': rel['nameref'],
                })
        return resources

    def _get_raw_resources(self):
        # http://localhost:8002/manage/v2?view=query&format=json
        params = {
            'view': 'query',
            'format': 'json',
        }
        url = self._base_url
        resp = self._http.get(url, params=params)
        resp.raise_for_status()
        return resp.json()
