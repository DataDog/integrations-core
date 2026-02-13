# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os
from collections import OrderedDict
from unittest import mock

from datadog_checks.dev.http import HTTPResponseMock

DEFAULT_OPTIONS = {
    'auth': None,
    'cert': None,
    'headers': OrderedDict(
        [
            ('User-Agent', 'Datadog Agent/0.0.0'),
            ('Accept', '*/*'),
            ('Accept-Encoding', 'gzip, deflate'),
        ]
    ),
    'proxies': None,
    'timeout': (10.0, 10.0),
    'verify': True,
    'allow_redirects': True,
}

FIXTURE_PATH = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'fixtures')


def make_mock_session():
    """Create a mock session whose get/post/head/put/patch/delete/options return HTTPResponseMock(200)."""
    session = mock.MagicMock()
    default_response = HTTPResponseMock(200, content=b'')
    for method in ('get', 'post', 'head', 'put', 'patch', 'delete', 'options'):
        getattr(session, method).return_value = default_response
    return session
