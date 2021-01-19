# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import os
import re

import mock

from datadog_checks.dev.utils import read_file

from .common import FIXTURES_PATH


def mocked_perform_request(*args, **kwargs):
    """
    A mocked version of _perform_request
    """
    response = mock.MagicMock()
    url = args[0]

    if re.search('/[23]/nginx', url):
        file_contents = read_file(os.path.join(FIXTURES_PATH, 'plus_api_nginx.json'))
        response.json.return_value = json.loads(file_contents)
    elif re.search('/[23]/processes', url):
        file_contents = read_file(os.path.join(FIXTURES_PATH, 'plus_api_processes.json'))
        response.json.return_value = json.loads(file_contents)
    elif re.search('/[23]/connections', url):
        file_contents = read_file(os.path.join(FIXTURES_PATH, 'plus_api_connections.json'))
        response.json.return_value = json.loads(file_contents)
    elif re.search('/[23]/ssl', url):
        file_contents = read_file(os.path.join(FIXTURES_PATH, 'plus_api_ssl.json'))
        response.json.return_value = json.loads(file_contents)
    elif re.search('/[23]/slabs', url):
        file_contents = read_file(os.path.join(FIXTURES_PATH, 'plus_api_slabs.json'))
        response.json.return_value = json.loads(file_contents)
    elif re.search('/[23]/http/requests', url):
        file_contents = read_file(os.path.join(FIXTURES_PATH, 'plus_api_http_requests.json'))
        response.json.return_value = json.loads(file_contents)
    elif re.search('/[23]/http/server_zones', url):
        file_contents = read_file(os.path.join(FIXTURES_PATH, 'plus_api_http_server_zones.json'))
        response.json.return_value = json.loads(file_contents)
    elif re.search('/[23]/http/caches', url):
        file_contents = read_file(os.path.join(FIXTURES_PATH, 'plus_api_http_caches.json'))
        response.json.return_value = json.loads(file_contents)
    elif re.search('/[23]/http/upstreams', url):
        file_contents = read_file(os.path.join(FIXTURES_PATH, 'plus_api_http_upstreams.json'))
        response.json.return_value = json.loads(file_contents)
    elif re.search('/[23]/stream/upstreams', url):
        file_contents = read_file(os.path.join(FIXTURES_PATH, 'plus_api_stream_upstreams.json'))
        response.json.return_value = json.loads(file_contents)
    elif re.search('/[23]/stream/server_zones', url):
        file_contents = read_file(os.path.join(FIXTURES_PATH, 'plus_api_stream_server_zones.json'))
        response.json.return_value = json.loads(file_contents)
    elif re.search('/[3]/stream/zone_sync', url):
        file_contents = read_file(os.path.join(FIXTURES_PATH, 'plus_api_stream_zone_sync.json'))
        response.json.return_value = json.loads(file_contents)
    else:
        response.json.return_value = ''

    return response
