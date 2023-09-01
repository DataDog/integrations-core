# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os
from collections import OrderedDict

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
