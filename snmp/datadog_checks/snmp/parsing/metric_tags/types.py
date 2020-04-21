# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from typing import List, TypedDict

MetricTag = TypedDict(
    'MetricTag',
    {
        'symbol': str,
        'MIB': str,
        'OID': str,
        # Simple tag.
        'tag': str,
        # Regex matching.
        'match': str,
        'tags': List[str],
    },
    total=False,
)
