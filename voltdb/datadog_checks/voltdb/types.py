# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import List, TypedDict

Instance = TypedDict(
    'Instance',
    {
        # Deprecated: use 'host' and 'port' instead. Kept for backwards
        # compatibility with users who still pass the legacy HTTP URL.
        'url': str,
        'host': str,
        'port': int,
        'username': str,
        'password': str,
        'use_ssl': bool,
        'ssl_config_file': str,
        'connect_timeout': float,
        'procedure_timeout': float,
        'statistics_components': List[str],
        'tags': List[str],
        'custom_queries': List[dict],
    },
    total=False,
)
