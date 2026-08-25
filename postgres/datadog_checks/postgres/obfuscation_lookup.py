# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import logging
from collections import OrderedDict
from dataclasses import dataclass

from datadog_checks.base.utils.db.sql import compute_sql_signature
from datadog_checks.base.utils.db.utils import obfuscate_sql_with_metadata

from .delta_detector import PgssKey

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ObfuscationResult:
    obfuscated_query: str
    query_signature: str
    tables: list[str] | None
    commands: list[str] | None
    comments: list[str] | None


class ObfuscationLookup:
    """LRU cache mapping pg_stat_statements keys to obfuscated query results.

    A lookup resolves a (queryid, dbid, userid) key to one of three outcomes:

    - hit: the obfuscated result is cached, avoiding both PG text fetch and FFI
      obfuscation. Stored as two tiers, key -> query_signature -> result, so
      multiple keys sharing a query_signature share one result.
    - miss: nothing is cached for the key; the caller must fetch its text and
      pass it to :meth:`populate` to obfuscate, store, and discard the raw text.
    - ignored: the key's text is known to be non-cacheable (e.g. the agent's own
      /* DDIGNORE */ queries). These are neither hit nor miss; lookup skips them
      so they never trigger a repeated text fetch.

    The caller decides what is non-cacheable (via :meth:`mark_ignored`); the
    cache only owns storage and lifecycle. All three tiers are LRU-bounded by
    ``maxsize`` and cleared for a key by :meth:`evict` when it leaves pgss.
    """

    def __init__(self, maxsize: int, obfuscate_options: str, log_unobfuscated_queries: bool = False):
        self._maxsize = maxsize
        self._obfuscate_options = obfuscate_options
        self._log_unobfuscated_queries = log_unobfuscated_queries

        self._key_to_sig: OrderedDict[PgssKey, str] = OrderedDict()
        self._sig_to_result: OrderedDict[str, ObfuscationResult] = OrderedDict()
        # Negative cache: keys we have learned resolve to nothing cacheable.
        self._ignored_keys: OrderedDict[PgssKey, None] = OrderedDict()

        self._hits = 0
        self._misses = 0

    @property
    def queryid_map_size(self) -> int:
        return len(self._key_to_sig)

    @property
    def signature_map_size(self) -> int:
        return len(self._sig_to_result)

    @property
    def ignored_map_size(self) -> int:
        return len(self._ignored_keys)

    @property
    def hits(self) -> int:
        return self._hits

    @property
    def misses(self) -> int:
        return self._misses

    def reset_stats(self):
        self._hits = 0
        self._misses = 0

    def lookup(self, keys: set[PgssKey]) -> tuple[dict[PgssKey, ObfuscationResult], set[PgssKey]]:
        """Return (hits, misses) for the given pg_stat_statements row keys.

        Keys in the negative cache are excluded from both: they are neither a hit
        (no result to return) nor a miss (must not be re-fetched).
        """
        hits: dict[PgssKey, ObfuscationResult] = {}
        misses: set[PgssKey] = set()
        ignored = 0

        for pgss_key in keys:
            if pgss_key in self._ignored_keys:
                self._ignored_keys.move_to_end(pgss_key)
                ignored += 1
                continue
            sig = self._key_to_sig.get(pgss_key)
            if sig is not None:
                self._key_to_sig.move_to_end(pgss_key)
                result = self._sig_to_result.get(sig)
                if result is not None:
                    self._sig_to_result.move_to_end(sig)
                    self._hits += 1
                    hits[pgss_key] = result
                    continue
            self._misses += 1
            misses.add(pgss_key)

        logger.debug(
            "lookup: requested=%d hits=%d misses=%d ignored=%d key_map=%d sig_map=%d ignored_map=%d",
            len(keys),
            len(hits),
            len(misses),
            ignored,
            len(self._key_to_sig),
            len(self._sig_to_result),
            len(self._ignored_keys),
        )
        return hits, misses

    def mark_ignored(self, keys: set[PgssKey]) -> None:
        """Record keys whose text is non-cacheable so future lookups skip them.

        The caller is responsible for deciding what is non-cacheable (e.g. the
        agent's own /* DDIGNORE */ queries). Entries are forgotten via
        :meth:`evict` when their key disappears from pg_stat_statements.
        """
        for pgss_key in keys:
            # Drop any stale positive mapping so an ignored key can never resurface as a
            # hit (e.g. if its signature is later repopulated by another key after this
            # negative entry is LRU-trimmed).
            self._key_to_sig.pop(pgss_key, None)
            self._ignored_keys[pgss_key] = None
            self._ignored_keys.move_to_end(pgss_key)
        if keys:
            self._trim_ignored()
            logger.debug("mark_ignored: added=%d ignored_map=%d", len(keys), len(self._ignored_keys))

    def populate(self, raw_texts: dict[PgssKey, str]) -> dict[PgssKey, ObfuscationResult]:
        """Obfuscate raw texts, store results, and return pgss_key -> ObfuscationResult."""
        results: dict[PgssKey, ObfuscationResult] = {}

        for pgss_key, raw_text in raw_texts.items():
            result = self._obfuscate_single(raw_text)
            if result is None:
                continue

            self._key_to_sig[pgss_key] = result.query_signature
            self._trim_keys()

            if result.query_signature not in self._sig_to_result:
                self._sig_to_result[result.query_signature] = result
                self._trim_sig()
            else:
                self._sig_to_result.move_to_end(result.query_signature)

            results[pgss_key] = result

        logger.debug(
            "populate: input=%d obfuscated=%d key_map=%d sig_map=%d",
            len(raw_texts),
            len(results),
            len(self._key_to_sig),
            len(self._sig_to_result),
        )
        return results

    def evict(self, keys: set[PgssKey]) -> None:
        """Forget all state (positive and negative) for keys evicted from pgss."""
        for pgss_key in keys:
            self._key_to_sig.pop(pgss_key, None)
            self._ignored_keys.pop(pgss_key, None)
        if keys:
            logger.debug(
                "evict: removed=%d key_map=%d ignored_map=%d",
                len(keys),
                len(self._key_to_sig),
                len(self._ignored_keys),
            )

    def _obfuscate_single(self, raw_text: str) -> ObfuscationResult | None:
        try:
            statement = obfuscate_sql_with_metadata(raw_text, self._obfuscate_options)
        except Exception as e:
            if self._log_unobfuscated_queries:
                logger.warning("Failed to obfuscate query=[%s] | err=[%s]", raw_text, e)
            else:
                logger.debug("Failed to obfuscate query | err=[%s]", e)
            return None

        obfuscated_query = statement['query']
        metadata = statement['metadata']
        return ObfuscationResult(
            obfuscated_query=obfuscated_query,
            query_signature=compute_sql_signature(obfuscated_query),
            tables=metadata.get('tables', None),
            commands=metadata.get('commands', None),
            comments=metadata.get('comments', None),
        )

    def _trim_keys(self):
        while len(self._key_to_sig) > self._maxsize:
            self._key_to_sig.popitem(last=False)

    def _trim_sig(self):
        while len(self._sig_to_result) > self._maxsize:
            self._sig_to_result.popitem(last=False)

    def _trim_ignored(self):
        while len(self._ignored_keys) > self._maxsize:
            self._ignored_keys.popitem(last=False)
