# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import random
import time
from collections.abc import Callable
from functools import wraps
from typing import Any

from requests import Response


def get_nested(obj: dict, path: str, default: Any = None) -> Any:
    """Walk a slash-separated path through nested dicts, returning default if any level is absent or not a dict."""
    current: Any = obj
    for key in path.split("/"):
        if not isinstance(current, dict):
            return default
        current = current.get(key)
    return current


def retry_on_rate_limit(method: Callable[..., Response]) -> Callable[..., Response]:
    """Retry on HTTP 429 with exponential backoff and jitter."""

    @wraps(method)
    def wrapper(self, *args, **kwargs) -> Response:
        max_retries: int = self.instance.get('pc_max_retries', 3)
        base_backoff: int = self.instance.get('pc_base_backoff_seconds', 1)
        max_backoff: int = self.instance.get('pc_max_backoff_seconds', 30)
        attempts = max(1, max_retries)

        for attempt in range(attempts):
            response = method(self, *args, **kwargs)

            if response.status_code != 429:
                return response

            self.count("api.rate_limited", 1, tags=self.base_tags)

            if attempt >= attempts - 1:
                self.log.error("Max retries exceeded for Nutanix API rate limiting")
                response.raise_for_status()

            backoff = min(base_backoff * (2**attempt) + random.random(), max_backoff)
            self.log.warning(
                "Rate limited by Nutanix API (attempt %d/%d), backing off for %.2f seconds",
                attempt + 1,
                max_retries,
                backoff,
            )
            time.sleep(backoff)

        return response

    return wrapper
