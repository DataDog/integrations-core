# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import List, TypedDict

Instance = TypedDict(
    'Instance',
    {'host': str, 'port': int, 'username': str, 'password': str, 'tls_ca_cert': str, 'tags': List[str]},
    total=False,
)
