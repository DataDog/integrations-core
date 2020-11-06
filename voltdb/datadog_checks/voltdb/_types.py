# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import List, TypedDict

Instance = TypedDict(
    'Instance',
    {
        'host': str,
        'port': int,
        'username': str,
        'password': str,
        'password_hashed': bool,
        'tags': List[str],
    },
    total=False,
)
