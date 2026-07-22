# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import hashlib
import json
import logging
import random
import time

EVENT_CACHE_TTL = 3600  # 1 hour in seconds


class CacheHelper:
    """Encapsulates persistent-cache reads/writes for a single collector.

    Args:
        check: The AgentCheck instance (provides read/write_persistent_cache).
        log: Logger for debug/warning messages.
        configs_refresh_interval: Base TTL in seconds for fetch cadence.
    """

    def __init__(self, check, log: logging.Logger, configs_refresh_interval: int) -> None:
        self._check = check
        self._log = log
        self.refresh_interval = configs_refresh_interval
        self.refresh_jitter = max(15, configs_refresh_interval // 10)

    def get_items_to_fetch(self, cache_key: str, item_keys: list[str]) -> list[str]:
        """Return items whose TTL has expired, sorted oldest-expiry-first."""
        current_time = time.time()
        items_to_fetch = []

        try:
            cached_str = self._check.read_persistent_cache(cache_key)
            cache_dict = json.loads(cached_str) if cached_str else {}
        except Exception as e:
            self._log.debug("Could not read cache %s: %s", cache_key, e)
            cache_dict = {}

        for item_key in item_keys:
            expire_at = cache_dict.get(item_key, 0)
            if current_time >= expire_at:
                items_to_fetch.append((expire_at, item_key))

        items_to_fetch.sort()
        return [item_key for _, item_key in items_to_fetch]

    def mark_items_fetched(
        self,
        cache_key: str,
        item_keys: list[str],
        ttl_base: float | None = None,
        ttl_jitter: float | None = None,
        max_cache_size: int | None = None,
    ) -> None:
        """Mark items as fetched in the cache with a jittered TTL."""
        if ttl_base is None:
            ttl_base = self.refresh_interval
        if ttl_jitter is None:
            ttl_jitter = self.refresh_jitter

        current_time = time.time()

        try:
            cached_str = self._check.read_persistent_cache(cache_key)
            cache_dict = json.loads(cached_str) if cached_str else {}
        except Exception as e:
            self._log.debug("Could not read cache %s for update: %s", cache_key, e)
            cache_dict = {}

        for item_key in item_keys:
            ttl = ttl_base + random.uniform(0, ttl_jitter)
            cache_dict[item_key] = current_time + ttl

        if max_cache_size and len(cache_dict) > max_cache_size:
            sorted_keys = sorted(cache_dict, key=lambda k: cache_dict[k])
            for key in sorted_keys[: len(cache_dict) - max_cache_size]:
                del cache_dict[key]

        try:
            self._check.write_persistent_cache(cache_key, json.dumps(cache_dict))
        except Exception as e:
            self._log.debug("Could not write cache %s: %s", cache_key, e)

    def get_events_to_send(self, cache_key: str, items: dict[str, str], max_cache_size: int | None = None) -> list[str]:
        """Return item keys whose events should be emitted (new, changed, or TTL expired).

        Writes the updated hash/expiry cache back to persistent storage.
        If max_cache_size is set, evicts the oldest entries when the cache exceeds it.
        """
        if not items:
            return []

        current_time = time.time()
        events_to_send = []

        try:
            cached_str = self._check.read_persistent_cache(cache_key)
            cache_dict = json.loads(cached_str) if cached_str else {}
        except Exception as e:
            self._log.debug("Could not read cache %s: %s", cache_key, e)
            cache_dict = {}

        for item_key, event_content in items.items():
            current_hash = hashlib.sha256(event_content.encode('utf-8')).hexdigest()
            cached_entry = cache_dict.get(item_key)

            if (
                not cached_entry
                or cached_entry.get('hash', '') != current_hash
                or current_time >= cached_entry.get('expire_at', 0)
            ):
                events_to_send.append(item_key)
                cache_dict[item_key] = {
                    'hash': current_hash,
                    'expire_at': current_time + EVENT_CACHE_TTL,
                }

        if events_to_send:
            if max_cache_size is not None and len(cache_dict) > max_cache_size:
                sorted_keys = sorted(cache_dict, key=lambda k: cache_dict[k].get('expire_at', 0))
                for key in sorted_keys[: len(cache_dict) - max_cache_size]:
                    del cache_dict[key]
            try:
                self._check.write_persistent_cache(cache_key, json.dumps(cache_dict))
            except Exception as e:
                self._log.debug("Could not write cache %s: %s", cache_key, e)

        return events_to_send
