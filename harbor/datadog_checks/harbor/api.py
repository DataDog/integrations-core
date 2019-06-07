from .common import (
    CHARTREPO_HEALTH_URL,
    HEALTH_URL,
    LOGIN_PRE_1_7_URL,
    LOGIN_URL,
    PING_URL,
    PROJECTS_URL,
    REGISTRIES_PING_PRE_1_8_URL,
    REGISTRIES_PING_URL,
    REGISTRIES_PRE_1_8_URL,
    REGISTRIES_URL,
    SYSTEM_INFO_URL,
    VERSION_1_7,
    VERSION_1_8,
    VOLUME_INFO_URL,
)


class HarborAPI(object):
    def __init__(self, harbor_url, http):
        self.base_url = harbor_url
        self.http = http
        self._fetch_and_set_harbor_version()

    def authenticate(self, username, password):
        auth_form_data = {'principal': username, 'password': password}
        if self.harbor_version >= VERSION_1_7:
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

    def _make_get_request(self, url):
        resp = self.http.get(self._resolve_url(url))
        resp.raise_for_status()
        try:
            return resp.json()
        except ValueError:
            # Cannot decode json. Some api calls (i.e. "PING") return plain text data.
            return resp.text

    def _make_post_request(self, url, data=None, json=None):
        resp = self.http.post(self._resolve_url(url), data=data, json=json)
        resp.raise_for_status()
        try:
            return resp.json()
        except ValueError:
            # Cannot decode json. Some api calls (i.e. "PING") return plain text data.
            return resp.text

    def _resolve_url(self, url, **kwargs):
        return url.format(base_url=self.base_url, **kwargs)
