# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os
from collections import OrderedDict

import mock

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


def get_wire_headers(http, url='http://example.com/hello', **options):
    """Return headers from the prepared outgoing request."""
    with mock.patch('requests.adapters.HTTPAdapter.send') as send:
        send.return_value = mock.MagicMock(status_code=200, headers={}, is_redirect=False, history=[])
        http.get(url, **options)

    return send.call_args.args[0].headers
