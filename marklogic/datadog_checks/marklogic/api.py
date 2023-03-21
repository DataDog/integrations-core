# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any, Dict  # noqa: F401

from datadog_checks.base.utils.http import RequestsWrapper  # noqa: F401

from .constants import BASE_ENDPOINT


class MarkLogicApi(object):
    def __init__(self, http, api_url):
        # type: (RequestsWrapper, str) -> None
        self._http = http

        # Remove a possible trailing '/', added by BASE_ENDPOINT
        if api_url[-1] == '/':
            api_url = api_url[:-1]
        self._base_url = api_url + BASE_ENDPOINT

    def http_get(self, route="", params=None):
        # type: (str, Dict[str, str]) -> Dict[str, Any]
        if params is None:
            params = {}
        params['format'] = 'json'  # Always in json

        url = self._base_url + route
        resp = self._http.get(url, params=params)
        resp.raise_for_status()
        return resp.json()

    def get_status_data(self, resource=None):
        # type: (str) -> Dict[str, Any]
        """
        Example url:
            - http://localhost:8002/manage/v2/hosts?view=status
            - http://localhost:8002/manage/v2/forests?view=status&format=json
        """
        params = {'view': 'status'}
        route = ""
        if resource:
            route = "/" + resource

        return self.http_get(route, params)

    def get_requests_data(self, resource=None, name=None, group=None):
        # type: (str, str, str) -> Dict[str, Any]
        """
        https://docs.marklogic.com/REST/GET/manage/v2/requests
        Example url:
            - http://localhost:8002/manage/v2/requests?format=json (cluster level)
            - http://localhost:8002/manage/v2/requests?format=json&server-id=Admin&group-id=Default
            - http://localhost:8002/manage/v2/requests?format=json&group-id=Default
            - http://localhost:8002/manage/v2/requests?format=json&host-id=2871b05b4bdc
        """
        params = {}
        route = "/requests"
        if resource and name:
            params['{}-id'.format(resource)] = name
        if group:
            params['group-id'] = group

        return self.http_get(route, params)

    def get_storage_data(self, resource=None, name=None, group=None):
        # type: (str, str, str) -> Dict[str, Any]
        """
        https://docs.marklogic.com/REST/GET/manage/v2/forests
        Example url:
            - http://localhost:8002/manage/v2/forests?format=json&view=storage
            - http://localhost:8002/manage/v2/forests?format=json&view=storage&database-id=Last-Login
            - http://localhost:8002/manage/v2/forests?format=json&view=storage&forest-id=Last-Login
            - http://localhost:8002/manage/v2/forests?format=json&view=storage&database-id=Security
        """
        params = {
            'view': 'storage',
        }
        route = "/forests"
        if resource and name:
            params['{}-id'.format(resource)] = name
        if group:
            params['group-id'] = group

        return self.http_get(route, params)

    def get_resources(self):
        # type: () -> Dict[str, Any]
        # This resource address returns the summary of all of the resources in the local cluster,
        # or resources in the local cluster that match a query.
        # http://localhost:8002/manage/v2?view=query&format=json
        params = {
            'view': 'query',
        }

        return self.http_get(params=params)

    def get_health(self):
        # type: () -> Dict[str, Any]
        """
        Return the cluster health querying http://localhost:8002/manage/v2?view=health&format=json.
        See https://docs.marklogic.com/REST/GET/manage/v2.
        """
        params = {'view': 'health'}

        return self.http_get(params=params)
