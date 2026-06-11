# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

"""Shared cache helpers for deduplicating config-fetch and event-emit cycles."""

import hashlib
import json
import random
import time

EVENT_CACHE_TTL = 3600  # 1 hour in seconds


class EventCacheMixin:
    """Cache helpers shared by ClusterMetadataCollector and KafkaConnectCollector.

    Subclasses must expose: self.check, self.log, self.config,
    self._configs_refresh_interval, self._configs_refresh_jitter.
    """

    def _get_items_to_fetch(self, cache_key: str, item_keys: list[str]) -> list[str]:
        """Return items that need fetching, sorted oldest-expiry-first."""
        current_time = time.time()
        items_to_fetch = []

        try:
            cached_str = self.check.read_persistent_cache(cache_key)
            cache_dict = json.loads(cached_str) if cached_str else {}
        except Exception as e:
            self.log.debug("Could not read cache %s: %s", cache_key, e)
            cache_dict = {}

        for item_key in item_keys:
            expire_at = cache_dict.get(item_key, 0)
            if current_time >= expire_at:
                items_to_fetch.append((expire_at, item_key))

        items_to_fetch.sort()
        return [item_key for _, item_key in items_to_fetch]

    def _mark_items_fetched(
        self,
        cache_key: str,
        item_keys: list[str],
        ttl_base: float | None = None,
        ttl_jitter: float | None = None,
        max_cache_size: int | None = None,
    ) -> None:
        """Mark items as fetched in cache with jittered TTL."""
        if ttl_base is None:
            ttl_base = self._configs_refresh_interval
        if ttl_jitter is None:
            ttl_jitter = self._configs_refresh_jitter

        current_time = time.time()

        try:
            cached_str = self.check.read_persistent_cache(cache_key)
            cache_dict = json.loads(cached_str) if cached_str else {}
        except Exception as e:
            self.log.debug("Could not read cache %s for update: %s", cache_key, e)
            cache_dict = {}

        for item_key in item_keys:
            ttl = ttl_base + random.uniform(0, ttl_jitter)
            cache_dict[item_key] = current_time + ttl

        if max_cache_size and len(cache_dict) > max_cache_size:
            sorted_keys = sorted(cache_dict, key=lambda k: cache_dict[k])
            for key in sorted_keys[: len(cache_dict) - max_cache_size]:
                del cache_dict[key]

        try:
            self.check.write_persistent_cache(cache_key, json.dumps(cache_dict))
        except Exception as e:
            self.log.debug("Could not write cache %s: %s", cache_key, e)

    def _get_events_to_send(
        self, cache_key: str, items: dict[str, str], max_cache_size: int | None = None
    ) -> list[str]:
        """Return item keys whose events should be emitted (new, changed, or expired).

        Writes the updated hash/expiry cache back to persistent storage.
        If max_cache_size is set, evicts the oldest entries when the cache exceeds it.
        """
        if not items:
            return []

        current_time = time.time()
        events_to_send = []

        try:
            cached_str = self.check.read_persistent_cache(cache_key)
            cache_dict = json.loads(cached_str) if cached_str else {}
        except Exception as e:
            self.log.debug("Could not read cache %s: %s", cache_key, e)
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
                self.check.write_persistent_cache(cache_key, json.dumps(cache_dict))
            except Exception as e:
                self.log.debug("Could not write cache %s: %s", cache_key, e)

        return events_to_send

    def _get_tags(self, cluster_id: str | None = None) -> list[str]:
        """Build metric tags, appending cluster ID tags when provided."""
        tags = list(self.config._custom_tags)
        if cluster_id:
            tags.append(f'kafka_cluster_id:{cluster_id}')
            if self.config._kafka_cluster_id_override:
                tags.append(f'original_kafka_cluster_id:{self.config._auto_detected_cluster_id}')
        return tags

    def _original_cluster_id_field(self) -> dict[str, str]:
        """Return the original cluster ID event field when a cluster ID override is active."""
        if self.config._kafka_cluster_id_override:
            return {'original_kafka_cluster_id': self.config._auto_detected_cluster_id}
        return {}
