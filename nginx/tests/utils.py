# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import os

import mock

from datadog_checks.dev.utils import read_file

from .common import FIXTURES_PATH


def mocked_perform_request(*args, **kwargs):
    """
    A mocked version of _perform_request
    """
    response = mock.MagicMock()
    url = args[1]

    if '/2/nginx' in url:
        file_contents = read_file(os.path.join(FIXTURES_PATH, 'plus_api_nginx.json'))
        response.json.return_value = json.loads(file_contents)
    elif '/2/processes' in url:
        file_contents = read_file(os.path.join(FIXTURES_PATH, 'plus_api_processes.json'))
        response.json.return_value = json.loads(file_contents)
    elif '/2/connections' in url:
        file_contents = read_file(os.path.join(FIXTURES_PATH, 'plus_api_connections.json'))
        response.json.return_value = json.loads(file_contents)
    elif '/2/ssl' in url:
        file_contents = read_file(os.path.join(FIXTURES_PATH, 'plus_api_ssl.json'))
        response.json.return_value = json.loads(file_contents)
    elif '/2/slabs' in url:
        file_contents = read_file(os.path.join(FIXTURES_PATH, 'plus_api_slabs.json'))
        response.json.return_value = json.loads(file_contents)
    elif '/2/http/requests' in url:
        file_contents = read_file(os.path.join(FIXTURES_PATH, 'plus_api_http_requests.json'))
        response.json.return_value = json.loads(file_contents)
    elif '/2/http/server_zones' in url:
        file_contents = read_file(os.path.join(FIXTURES_PATH, 'plus_api_http_server_zones.json'))
        response.json.return_value = json.loads(file_contents)
    elif '/2/http/caches' in url:
        file_contents = read_file(os.path.join(FIXTURES_PATH, 'plus_api_http_caches.json'))
        response.json.return_value = json.loads(file_contents)
    elif '/2/http/upstreams' in url:
        file_contents = read_file(os.path.join(FIXTURES_PATH, 'plus_api_http_upstreams.json'))
        response.json.return_value = json.loads(file_contents)
    elif '/2/stream/upstreams' in url:
        file_contents = read_file(os.path.join(FIXTURES_PATH, 'plus_api_stream_upstreams.json'))
        response.json.return_value = json.loads(file_contents)
    elif '/2/stream/server_zones' in url:
        file_contents = read_file(os.path.join(FIXTURES_PATH, 'plus_api_stream_server_zones.json'))
        response.json.return_value = json.loads(file_contents)
    else:
        response.json.return_value = ''

    return response
