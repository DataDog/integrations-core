# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import random
import time
from functools import wraps

from requests.exceptions import HTTPError


def retry_on_rate_limit(method):
    """Retry API requests on 429 responses with exponential backoff and jitter."""

    @wraps(method)
    def wrapper(self, *args, **kwargs):
        max_retries = self.instance.get('pc_max_retries', 3)
        base_backoff = self.instance.get('pc_base_backoff_seconds', 1)
        max_backoff = self.instance.get('pc_max_backoff_seconds', 30)

        last_exception = None
        for attempt in range(max(1, max_retries)):
            try:
                response = method(self, *args, **kwargs)

                if hasattr(response, 'status_code'):
                    if response.status_code == 429:
                        self.count("api.rate_limited", 1, tags=self.base_tags)
                        if max_retries > 0 and attempt < max_retries - 1:
                            backoff = min(base_backoff * (2**attempt) + random.random(), max_backoff)
                            self.log.warning(
                                "Rate limited by Nutanix API (attempt %d/%d), backing off for %.2f seconds",
                                attempt + 1,
                                max_retries,
                                backoff,
                            )
                            time.sleep(backoff)
                            continue
                        else:
                            self.log.error("Max retries exceeded for Nutanix API request after rate limiting")
                            response.raise_for_status()

                    response.raise_for_status()
                return response

            except HTTPError as e:
                last_exception = e
                if hasattr(e, 'response') and e.response is not None and e.response.status_code == 429:
                    self.count("api.rate_limited", 1, tags=self.base_tags)
                    if max_retries > 0 and attempt < max_retries - 1:
                        backoff = min(base_backoff * (2**attempt) + random.random(), max_backoff)
                        self.log.warning(
                            "Rate limited by Nutanix API (attempt %d/%d), backing off for %.2f seconds",
                            attempt + 1,
                            max_retries,
                            backoff,
                        )
                        time.sleep(backoff)
                        continue
                    else:
                        self.log.error("Max retries exceeded for Nutanix API request after rate limiting")
                raise
            except Exception:
                raise

        if last_exception:
            raise last_exception
        raise Exception(f"Failed to complete request after {max_retries} retries")

    return wrapper
