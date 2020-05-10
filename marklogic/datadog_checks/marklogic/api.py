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

    def get_status(self, resource=None, name=None, group=None):
        # http://localhost:8002/manage/v2/hosts?view=status&format=json
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
