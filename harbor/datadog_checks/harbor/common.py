# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

SYSTEMINFO_URL = "{base_url}/api/systeminfo/"
LOGIN_URL = "{base_url}/c/login/"
LOGIN_PRE_1_7_URL = "{base_url}/login/"
HEALTH_URL = "{base_url}/api/health/"
PING_URL = "{base_url}/api/ping/"
CHARTREPO_HEALTH_URL = "{base_url}/api/chartrepo/health"
PROJECTS_URL = "{base_url}/api/projects/"
REGISTRIES_URL = "{base_url}/api/registries/"
REGISTRIES_PRE_1_8_URL = "{base_url}/api/targets/"
REGISTRIES_PING_URL = "{base_url}/api/registries/ping/"
REGISTRIES_PING_PRE_1_8_URL = "{base_url}/api/targets/ping/"
VOLUME_INFO_URL = "{base_url}/api/systeminfo/volumes/"


class HarborAPI(object):
    def __init__(self, harbor_url, http):
        self.base_url = harbor_url
        self.http = http
        self._fetch_and_set_harbor_version()

    def authenticate(self, username, password):
        auth_form_data = {'principal': username, 'password': password}
        if self.harbor_version >= [1, 7, 0]:
            url = self._resolve_url(LOGIN_URL)
        else:
            url = self._resolve_url(LOGIN_PRE_1_7_URL)
        self._make_post_request(url, data=auth_form_data)

    def health(self):
        return self._make_get_request(HEALTH_URL)

    def ping(self):
        return self._make_get_request(PING_URL)

    def chartrepo_health(self):
        return self._make_get_request(CHARTREPO_HEALTH_URL)

    def projects(self):
        return self._make_paginated_get_request(PROJECTS_URL)

    def registries(self):
        if self.harbor_version >= [1, 8, 0]:
            return self._make_paginated_get_request(REGISTRIES_URL)
        else:
            return self._make_paginated_get_request(REGISTRIES_PRE_1_8_URL)

    def registry_health(self, registry_id):
        data = {"id": registry_id}
        if self.harbor_version >= [1, 8, 0]:
            return self._make_post_request(REGISTRIES_PING_URL, data=data)
        else:
            return self._make_post_request(REGISTRIES_PING_PRE_1_8_URL, data=data)

    def volume_info(self):
        return self._make_get_request(VOLUME_INFO_URL)

    def _fetch_and_set_harbor_version(self):
        systeminfo = self._make_get_request(SYSTEMINFO_URL)
        version_str = systeminfo['harbor_version'].split('-')[0].lstrip('v').split('.')[:3]
        self.harbor_version = [0, 0, 0]
        for i in range(len(version_str)):
            self.harbor_version[i] = int(version_str[i])

        self.with_chartrepo = systeminfo.get('with_chartmuseum', False)

    def _make_paginated_get_request(self, url):
        resp = self.http.get(self._resolve_url(url), params={'page_size': 100})
        resp.raise_for_status()
        results = resp.json()
        while "next" in resp.links:
            next_url = '{}/{}'.format(self.base_url, resp.links['next']['url'])
            resp = self.http.get(next_url, params={'page_size': 100})
            resp.raise_for_status()
            results.extend(resp.json())
        return results or []

    def _make_get_request(self, url):
        resp = self.http.get(self._resolve_url(url))
        resp.raise_for_status()
        try:
            return resp.json()
        except ValueError:
            # Cannot decode json. This is expected with some Harbor api calls
            return resp.text

    def _make_post_request(self, url, data=None, json=None):
        resp = self.http.post(self._resolve_url(url), data=data, json=json)
        resp.raise_for_status()
        try:
            return resp.json()
        except ValueError:
            # Cannot decode json. This is expected with some Harbor api calls
            return resp.text

    def _resolve_url(self, url, **kwargs):
        return url.format(base_url=self.base_url, **kwargs)
