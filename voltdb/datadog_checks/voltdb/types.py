# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import List, Tuple, TypedDict, Union

Instance = TypedDict(
    'Instance',
    {
        'url': str,
        'username': str,
        'password': str,
        'password_hashed': bool,
        'tls_verify': bool,
        'tls_cert': Union[str, Tuple[str, str]],  # <path> or (<path>, <password>)
        'tags': List[str],
    },
    total=False,
)
