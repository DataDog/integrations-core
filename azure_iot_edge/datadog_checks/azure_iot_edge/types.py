# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import List, TypedDict

Instance = TypedDict(
    'Instance',
    {
        'edge_hub_prometheus_url': str,
        'edge_agent_prometheus_url': str,
        'tags': List[str],
    },
    total=False,
)
