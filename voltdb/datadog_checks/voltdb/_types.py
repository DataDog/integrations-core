# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import TypedDict, List

Instance = TypedDict(
    'Instance',
    {
        'hostname': str,
        'port': int,
        'username': str,
        'password': str,
        'tags': List[str],
    },
    total=False,
)
