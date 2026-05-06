# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from collections.abc import Callable

import requests


def http_probe(
    host: str,
    port: int,
    path: str,
    *,
    verifier: Callable[[requests.Response], bool],
    timeout: float = 0.5,
) -> bool:
    """Perform a single GET probe and apply the verifier.

    Returns True iff the request completed and the verifier accepted the
    response. All network exceptions yield False (probes are best-effort).

    The ``host`` is used verbatim in the URL — IPv6 hosts must already be
    bracketed by the caller (the Agent-side bridge handles this).
    """
    url = f"http://{host}:{port}{path}"
    try:
        response = requests.get(url, timeout=timeout)
    except requests.RequestException:
        return False
    try:
        return bool(verifier(response))
    finally:
        response.close()
