# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import os
import re

import mock
import pytest

from datadog_checks.dev.utils import read_file

from .common import FIXTURES_PATH, USING_LATEST


def mocked_perform_request(*args, **kwargs):
    """
    A mocked version of _perform_request
    """
    response = mock.MagicMock()
    url = args[0]

    if re.search('/[234567]/nginx', url):
        file_contents = read_file(os.path.join(FIXTURES_PATH, 'v1', 'plus_api_nginx.json'))
        response.json.return_value = json.loads(file_contents)
    elif re.search('/[234567]/processes', url):
        file_contents = read_file(os.path.join(FIXTURES_PATH, 'v1', 'plus_api_processes.json'))
        response.json.return_value = json.loads(file_contents)
    elif re.search('/[234567]/connections', url):
        file_contents = read_file(os.path.join(FIXTURES_PATH, 'v1', 'plus_api_connections.json'))
        response.json.return_value = json.loads(file_contents)
    elif re.search('/[234567]/ssl', url):
        file_contents = read_file(os.path.join(FIXTURES_PATH, 'v1', 'plus_api_ssl.json'))
        response.json.return_value = json.loads(file_contents)
    elif re.search('/[234567]/slabs', url):
        file_contents = read_file(os.path.join(FIXTURES_PATH, 'v1', 'plus_api_slabs.json'))
        response.json.return_value = json.loads(file_contents)
    elif re.search('/[234567]/http/requests', url):
        file_contents = read_file(os.path.join(FIXTURES_PATH, 'v1', 'plus_api_http_requests.json'))
        response.json.return_value = json.loads(file_contents)
    elif re.search('/[23456]/http/server_zones', url):
        file_contents = read_file(os.path.join(FIXTURES_PATH, 'v1/', 'plus_api_http_server_zones.json'))
        response.json.return_value = json.loads(file_contents)
    elif re.search('/[234567]/http/caches', url):
        file_contents = read_file(os.path.join(FIXTURES_PATH, 'v1', 'plus_api_http_caches.json'))
        response.json.return_value = json.loads(file_contents)
    elif re.search('/[23456]/http/upstreams', url):
        file_contents = read_file(os.path.join(FIXTURES_PATH, 'v1', 'plus_api_http_upstreams.json'))
        response.json.return_value = json.loads(file_contents)
    elif re.search('/[234567]/stream/upstreams', url):
        file_contents = read_file(os.path.join(FIXTURES_PATH, 'v1', 'plus_api_stream_upstreams.json'))
        response.json.return_value = json.loads(file_contents)
    elif re.search('/[234567]/stream/server_zones', url):
        file_contents = read_file(os.path.join(FIXTURES_PATH, 'v1', 'plus_api_stream_server_zones.json'))
        response.json.return_value = json.loads(file_contents)
    elif re.search('/[34567]/stream/zone_sync', url):
        file_contents = read_file(os.path.join(FIXTURES_PATH, 'v3', 'plus_api_stream_zone_sync.json'))
        response.json.return_value = json.loads(file_contents)
    elif re.search('/[56]/http/location_zones', url):
        file_contents = read_file(os.path.join(FIXTURES_PATH, 'v5', 'plus_api_http_location_zones.json'))
        response.json.return_value = json.loads(file_contents)
    elif re.search('/[567]/resolvers', url):
        file_contents = read_file(os.path.join(FIXTURES_PATH, 'v5', 'plus_api_resolvers.json'))
        response.json.return_value = json.loads(file_contents)
    elif re.search('/[67]/http/limit_reqs', url):
        file_contents = read_file(os.path.join(FIXTURES_PATH, 'v6', 'plus_api_http_limit_reqs.json'))
        response.json.return_value = json.loads(file_contents)
    elif re.search('/[67]/http/limit_conns', url):
        file_contents = read_file(os.path.join(FIXTURES_PATH, 'v6', 'plus_api_http_limit_conns.json'))
        response.json.return_value = json.loads(file_contents)
    elif re.search('/[67]/stream/limit_conns', url):
        file_contents = read_file(os.path.join(FIXTURES_PATH, 'v6', 'plus_api_stream_limit_conns.json'))
        response.json.return_value = json.loads(file_contents)
    elif re.search('/[7]/http/upstreams', url):
        file_contents = read_file(os.path.join(FIXTURES_PATH, 'v7', 'plus_api_http_upstreams.json'))
        response.json.return_value = json.loads(file_contents)
    elif re.search('/[7]/http/server_zones', url):
        file_contents = read_file(os.path.join(FIXTURES_PATH, 'v7', 'plus_api_http_server_zones.json'))
        response.json.return_value = json.loads(file_contents)
    elif re.search('/[7]/http/location_zones', url):
        file_contents = read_file(os.path.join(FIXTURES_PATH, 'v7', 'plus_api_http_location_zones.json'))
        response.json.return_value = json.loads(file_contents)
    elif re.match(".*/[23456]/http/?", url):
        file_contents = read_file(os.path.join(FIXTURES_PATH, 'v1', 'plus_api_http.json'))
        response.json.return_value = json.loads(file_contents)
    elif re.match(".*/[23456]/stream/?", url):
        file_contents = read_file(os.path.join(FIXTURES_PATH, 'v1', 'plus_api_stream.json'))
        response.json.return_value = json.loads(file_contents)
    elif re.match(".*/[23456]/?", url):
        file_contents = read_file(os.path.join(FIXTURES_PATH, 'v1', 'plus_api.json'))
        response.json.return_value = json.loads(file_contents)
    elif re.match(".*/[7]/http/?", url):
        file_contents = read_file(os.path.join(FIXTURES_PATH, 'v7', 'plus_api_http.json'))
        response.json.return_value = json.loads(file_contents)
    elif re.match(".*/[7]/stream/?", url):
        file_contents = read_file(os.path.join(FIXTURES_PATH, 'v7', 'plus_api_stream.json'))
        response.json.return_value = json.loads(file_contents)
    elif re.match(".*/[7]/?", url):
        file_contents = read_file(os.path.join(FIXTURES_PATH, 'v7', 'plus_api.json'))
        response.json.return_value = json.loads(file_contents)
    else:
        response.json.return_value = ''

    return response


requires_static_version = pytest.mark.skipif(USING_LATEST, reason='Version `latest` is ever-changing, skipping')
