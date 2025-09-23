# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under Simplified BSD License see LICENSE

import os

from requests import Response

from . import common


def mock_send(prepped_request, **kwargs):
    if prepped_request.path_url == '/api/aaaLogin.xml':
        cookie_path = os.path.join(common.FIXTURES_DIR, 'login_cookie.txt')
        response_path = os.path.join(common.FIXTURES_DIR, 'login.txt')
        response = Response()
        with open(cookie_path, 'r') as f:
            response.cookies = {'APIC-cookie': f.read()}
        with open(response_path, 'r') as f:
            response.raw = f.read()

        response.status_code = 200

    return response
