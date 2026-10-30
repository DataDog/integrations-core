# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Standard-library HTTP calls for preparing and loading the CouchDB test environment."""

import base64
import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def request(method, url, *, auth=None, json_body=None, headers=None, timeout=10, raise_for_status=True):
    """Send a request and return its status code and decoded JSON body.

    Error statuses raise `urllib.error.HTTPError` unless `raise_for_status` is false, in which case they are returned.
    Timeouts while connecting or reading raise `TimeoutError`.
    """
    request_headers = dict(headers or {})
    data = None
    if json_body is not None:
        data = json.dumps(json_body).encode('utf-8')
        request_headers.setdefault('Content-Type', 'application/json')
    if auth is not None:
        # Sent preemptively, like requests does, because urllib's auth handler waits for a 401 challenge
        credentials = base64.b64encode('{}:{}'.format(*auth).encode('utf-8')).decode('ascii')
        request_headers['Authorization'] = f'Basic {credentials}'

    try:
        with urlopen(Request(url, data=data, headers=request_headers, method=method), timeout=timeout) as response:
            status, body = response.status, response.read()
    except HTTPError as e:
        if raise_for_status:
            raise
        status, body = e.code, e.read()
    except URLError as e:
        # urlopen wraps connect timeouts, but not read timeouts
        if isinstance(e.reason, TimeoutError):
            raise e.reason from e
        raise

    return status, json.loads(body) if body else None
