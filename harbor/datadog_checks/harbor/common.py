# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from requests.exceptions import InvalidURL, HTTPError, Timeout

SYSTEMINFO_URL = "{base_url}/api/systeminfo/"
LOGIN_URL = "{base_url}/c/login/"
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
    def __init__(self, harbor_url, requests_session, version=None):
        self.base_url = harbor_url
        self.session = requests_session
        self.harbor_version = version
        self._fetch_and_set_harbor_version()

    def authenticate(self, username, password):
        auth_form_data = {
            'principal': username,
            'password': password
        }
        url = self._resolve_url(LOGIN_URL)
        resp = self.session.post(url, data=auth_form_data)
        resp.raise_for_status()

    def health(self):
        return self._make_request(HEALTH_URL)

    def ping(self):
        return self._make_request(PING_URL)

    def chartrepo_health(self):
        return self._make_request(CHARTREPO_HEALTH_URL)

    def projects(self):
        return self._make_paginated_request(PROJECTS_URL)

    def registries(self):
        if self.harbor_version >= [1, 8, 0]:
            return self._make_paginated_request(REGISTRIES_URL)
        else:
            return self._make_paginated_request(REGISTRIES_PRE_1_8_URL)

    def volume_info(self):
        return self._make_request(VOLUME_INFO_URL)

    def _fetch_and_set_harbor_version(self):
        systeminfo = self._make_request(SYSTEMINFO_URL)
        version_str = systeminfo['harbor_version'].split('-')[0].lstrip('v').split('.')[:3]
        self.harbor_version = [0, 0, 0]
        for i in range(len(version_str)):
            self.harbor_version[i] = int(version_str[i])

        self.with_chartrepo = systeminfo['with_chartmuseum']

    def _make_paginated_request(self, url):
        resp = self.session.get(self._resolve_url(url), params={'page_size': 1})
        resp.raise_for_status()
        results = resp.json()
        while "next" in resp.links:
            next_url = '{}/{}'.format(self.base_url, resp.links['next']['url'])
            resp = self.session.get(next_url, params={'page_size': 1})
            resp.raise_for_status()
            results.extend(resp.json())
        return results or []

    def _make_request(self, url):
        resp = self.session.get(self._resolve_url(url))
        try:
            return resp.json()
        except ValueError:
            # Cannot decode json. This is expected with some Harbor api calls
            return resp.text

    def _resolve_url(self, url, **kwargs):
        return url.format(base_url=self.base_url, **kwargs)
