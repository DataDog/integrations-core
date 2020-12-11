# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import List, TypedDict

Instance = TypedDict(
    'Instance',
    {
        'url': str,
        'username': str,
        'password': str,
        'password_hashed': bool,
        'tls_verify': bool,
        'tls_ca_cert': str,
        'tags': List[str],
        'custom_queries': List[dict],
    },
    total=False,
)
