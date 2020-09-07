# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import List, TypedDict

EdgeHubConfig = TypedDict('EdgeHubConfig', {'prometheus_url': str})
EdgeAgentConfig = TypedDict('EdgeAgentConfig', {'prometheus_url': str})

Instance = TypedDict(
    'Instance',
    {
        'edge_hub': EdgeHubConfig,
        'edge_agent': EdgeAgentConfig,
        'security_daemon_management_api_url': str,
        'tags': List[str],
    },
    total=False,
)
