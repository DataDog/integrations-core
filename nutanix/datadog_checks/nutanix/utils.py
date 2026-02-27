# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import random
import time
from functools import wraps

from requests.exceptions import HTTPError


def retry_on_rate_limit(method):
    """Decorator to retry API requests when rate limited with exponential backoff."""

    @wraps(method)
    def wrapper(self, *args, **kwargs):
        max_retries = self.instance.get('pc_max_retries', 3)
        base_backoff = self.instance.get('pc_base_backoff_seconds', 1)
        max_backoff = self.instance.get('pc_max_backoff_seconds', 30)

        last_exception = None
        # Use max(1, max_retries) to ensure at least one attempt even when max_retries is 0
        for attempt in range(max(1, max_retries)):
            try:
                response = method(self, *args, **kwargs)

                # Check if it's an HTTP response with status code
                if hasattr(response, 'status_code'):
                    if response.status_code == 429:
                        if max_retries > 0 and attempt < max_retries - 1:
                            # Calculate backoff with exponential increase and jitter
                            backoff = min(base_backoff * (2**attempt) + random.random(), max_backoff)
                            self.log.warning(
                                "Rate limited by Nutanix API (attempt %d/%d), backing off for %.2f seconds",
                                attempt + 1,
                                max_retries,
                                backoff,
                            )
                            # Report retry metrics
                            self.gauge("api.retry.count", 1, tags=self.base_tags)
                            self.gauge("api.retry.backoff_seconds", backoff, tags=self.base_tags)
                            time.sleep(backoff)
                            continue
                        else:
                            self.log.error("Max retries exceeded for Nutanix API request after rate limiting")
                            self.gauge("api.retry.exhausted", 1, tags=self.base_tags)
                            response.raise_for_status()  # This will raise HTTPError for 429

                    # For successful responses or non-429 errors, return/raise immediately
                    response.raise_for_status()

                # Reset retry count metric on success
                if attempt > 0:
                    self.gauge("api.retry.count", 0, tags=self.base_tags)

                return response

            except HTTPError as e:
                last_exception = e
                # Only retry on 429, re-raise other HTTP errors immediately
                if hasattr(e, 'response') and e.response is not None and e.response.status_code == 429:
                    if max_retries > 0 and attempt < max_retries - 1:
                        # Calculate backoff with exponential increase and jitter
                        backoff = min(base_backoff * (2**attempt) + random.random(), max_backoff)
                        self.log.warning(
                            "Rate limited by Nutanix API (attempt %d/%d), backing off for %.2f seconds",
                            attempt + 1,
                            max_retries,
                            backoff,
                        )
                        # Report retry metrics
                        self.gauge("api.retry.count", 1, tags=self.base_tags)
                        self.gauge("api.retry.backoff_seconds", backoff, tags=self.base_tags)
                        time.sleep(backoff)
                        continue
                    else:
                        self.log.error("Max retries exceeded for Nutanix API request after rate limiting")
                        self.gauge("api.retry.exhausted", 1, tags=self.base_tags)
                raise
            except Exception:
                # For non-HTTP errors, raise immediately without retry
                raise

        # This should not be reached, but just in case
        if last_exception:
            raise last_exception
        raise Exception(f"Failed to complete request after {max_retries} retries")

    return wrapper
