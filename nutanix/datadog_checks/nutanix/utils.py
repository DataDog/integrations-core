# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import random
import time
from functools import wraps


def retry_on_rate_limit(method):
    """Retry on HTTP 429 with exponential backoff and jitter."""

    @wraps(method)
    def wrapper(self, *args, **kwargs):
        max_retries = self.instance.get('pc_max_retries', 3)
        base_backoff = self.instance.get('pc_base_backoff_seconds', 1)
        max_backoff = self.instance.get('pc_max_backoff_seconds', 30)

        for attempt in range(max(1, max_retries)):
            response = method(self, *args, **kwargs)

            if response.status_code != 429:
                return response

            self.count("api.rate_limited", 1, tags=self.base_tags)

            if max_retries == 0 or attempt >= max_retries - 1:
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

    return wrapper
