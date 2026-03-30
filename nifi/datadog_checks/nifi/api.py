# ABOUTME: REST API client for Apache NiFi.
# ABOUTME: Handles token-based auth, request retries on 401, and endpoint access.

# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from requests.exceptions import HTTPError

from .constants import ABOUT_ENDPOINT, ACCESS_TOKEN_ENDPOINT, CLUSTER_SUMMARY_ENDPOINT


class NiFiApi:
    def __init__(self, api_url, http, log, username=None, password=None):
        self._api_url = api_url.rstrip('/')
        self._http = http
        self._log = log
        self._username = username
        self._password = password
        self._token = None
        self._version = None

    def _authenticate(self):
        """Obtain a bearer token via POST /access/token (expects HTTP 201)."""
        resp = self._http.post(
            f'{self._api_url}{ACCESS_TOKEN_ENDPOINT}',
            data={'username': self._username, 'password': self._password},
            extra_headers={'Content-Type': 'application/x-www-form-urlencoded'},
        )
        if resp.status_code != 201:
            resp.raise_for_status()
            raise HTTPError(f'Expected 201 from token endpoint, got {resp.status_code}')
        self._token = resp.text
        self._log.debug('Obtained NiFi auth token (%d chars)', len(self._token))

    def _ensure_auth(self):
        """Authenticate if we don't have a token yet."""
        if not self._token and self._username and self._password:
            self._authenticate()

    def _request(self, path):
        """GET a JSON endpoint with bearer token auth, retry once on 401."""
        url = f'{self._api_url}{path}'
        extra = {}
        if self._token:
            extra['Authorization'] = f'Bearer {self._token}'

        resp = self._http.get(url, extra_headers=extra)

        if resp.status_code == 401 and self._username and self._password:
            self._log.debug('Got 401, re-authenticating')
            self._authenticate()
            extra['Authorization'] = f'Bearer {self._token}'
            resp = self._http.get(url, extra_headers=extra)

        resp.raise_for_status()
        return resp.json()

    def get_about(self):
        """GET /flow/about — returns version info. Cached after first call."""
        if self._version is None:
            data = self._request(ABOUT_ENDPOINT)
            self._version = data.get('about', {}).get('version', 'unknown')
        return self._version

    def get_cluster_summary(self):
        """GET /flow/cluster/summary — returns cluster health info."""
        return self._request(CLUSTER_SUMMARY_ENDPOINT)
