# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from .common import (
    CHARTREPO_HEALTH_URL,
    HEALTH_URL,
    PING_URL,
    PROJECTS_URL,
    REGISTRIES_PING_PRE_1_8_URL,
    REGISTRIES_PING_URL,
    REGISTRIES_PRE_1_8_URL,
    REGISTRIES_URL,
    SYSTEM_INFO_URL,
    VERSION_1_8,
    VOLUME_INFO_URL,
)


class HarborAPI(object):
    def __init__(self, harbor_url, http):
        self.base_url = harbor_url
        self.http = http
        self._fetch_and_set_harbor_version()

    def chartrepo_health(self):
        """Support added with Harbor 1.6"""
        return self._make_get_request(CHARTREPO_HEALTH_URL)

    def health(self):
        """Support added with Harbor 1.8 This endpoints provide granular health probes on each component of the
        Harbor environment
        """
        return self._make_get_request(HEALTH_URL)

    def ping(self):
        """Support added with Harbor 1.5"""
        return self._make_get_request(PING_URL)

    def projects(self):
        return self._make_paginated_get_request(PROJECTS_URL)

    def registries(self):
        if self.harbor_version >= VERSION_1_8:
            return self._make_paginated_get_request(REGISTRIES_URL)
        else:
            return self._make_paginated_get_request(REGISTRIES_PRE_1_8_URL)

    def registry_health(self, registry_id):
        data = {"id": registry_id}
        if self.harbor_version >= VERSION_1_8:
            return self._make_post_request(REGISTRIES_PING_URL, data=data)
        else:
            return self._make_post_request(REGISTRIES_PING_PRE_1_8_URL, data=data)

    def volume_info(self):
        return self._make_get_request(VOLUME_INFO_URL)

    def _fetch_and_set_harbor_version(self):
        systeminfo = self._make_get_request(SYSTEM_INFO_URL)
        version_str = systeminfo['harbor_version'].split('-')[0].lstrip('v').split('.')[:3]
        self.harbor_version = [int(s) for s in version_str]
        self.with_chartrepo = systeminfo.get('with_chartmuseum', False)

    def read_only_status(self):
        systeminfo = self._make_get_request(SYSTEM_INFO_URL)
        return systeminfo.get('read_only', None)

    def _make_paginated_get_request(self, url):
        http_params = {'page_size': 100}
        resp = self.http.get(self._resolve_url(url), params=http_params)
        resp.raise_for_status()
        results = resp.json()
        while "next" in resp.links:
            next_url = '{}/{}'.format(self.base_url, resp.links['next']['url'])
            resp = self.http.get(next_url, params=http_params)
            resp.raise_for_status()
            results.extend(resp.json())
        return results or []

    def _make_get_request(self, url, **kwargs):
        resp = self.http.get(self._resolve_url(url), **kwargs)
        resp.raise_for_status()
        if resp.content:
            # Do not parse json of an empty response
            return resp.json()

    def _make_post_request(self, url, **kwargs):
        resp = self.http.post(self._resolve_url(url), **kwargs)
        resp.raise_for_status()
        if resp.content:
            # Do not parse json of an empty response
            return resp.json()

    def _resolve_url(self, url):
        return url.format(base_url=self.base_url)
