# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import logging
from collections import OrderedDict
from collections.abc import Hashable
from dataclasses import dataclass

from datadog_checks.base.utils.db.sql import compute_sql_signature
from datadog_checks.base.utils.db.utils import obfuscate_sql_with_metadata

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ObfuscationResult:
    obfuscated_query: str
    query_signature: str
    tables: list[str] | None
    commands: list[str] | None
    comments: list[str] | None


def obfuscate_statement(
    raw_text: str, obfuscate_options: str, log_unobfuscated_queries: bool = False
) -> ObfuscationResult | None:
    """Obfuscate one statement via the FFI, returning None if it cannot be obfuscated.

    Exposed separately from :class:`ObfuscationLookup` for statement sources whose identity does
    not determine their text, which therefore cannot be cached. MySQL's
    ``prepared_statements_instances`` is one: it is keyed on a reusable memory address, so a
    recycled instance can carry unrelated text and every row has to be obfuscated afresh.
    """
    try:
        statement = obfuscate_sql_with_metadata(raw_text, obfuscate_options)
    except Exception as e:
        if log_unobfuscated_queries:
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


class ObfuscationLookup[K: Hashable]:
    """LRU cache mapping statement identity keys to obfuscated query results.

    ``K`` is whatever identifies a statement in the source table: a
    ``(queryid, dbid, userid)`` triple for ``pg_stat_statements``, a digest string for MySQL's
    ``events_statements_summary_by_digest``, and so on. The cache never interprets the key.

    A lookup resolves a key to one of three outcomes:

    - hit: the obfuscated result is cached, avoiding both the text fetch and FFI obfuscation.
      Stored as two tiers, key -> query_signature -> result, so multiple keys sharing a
      query_signature share one result.
    - miss: nothing is cached for the key; the caller must fetch its text and pass it to
      :meth:`populate` to obfuscate, store, and discard the raw text.
    - ignored: the key is known to resolve to nothing usable, because the caller rejected its
      text. These are neither hit nor miss; lookup skips them so they are never fetched again.

    The caller decides what is non-cacheable (via :meth:`mark_ignored`), since whether a rejection
    is permanent depends on the source table; the cache only owns storage and lifecycle. All three
    tiers are LRU-bounded by ``maxsize``, and :meth:`evict` clears every tier for a key once it
    leaves the source table, which bounds how long any entry (positive or negative) survives.
    """

    def __init__(self, maxsize: int, obfuscate_options: str, log_unobfuscated_queries: bool = False):
        self._maxsize = maxsize
        self._obfuscate_options = obfuscate_options
        self._log_unobfuscated_queries = log_unobfuscated_queries

        self._key_to_sig: OrderedDict[K, str] = OrderedDict()
        self._sig_to_result: OrderedDict[str, ObfuscationResult] = OrderedDict()
        # Negative cache: keys we have learned resolve to nothing cacheable.
        self._ignored_keys: OrderedDict[K, None] = OrderedDict()

        self._hits = 0
        self._misses = 0

    @property
    def maxsize(self) -> int:
        return self._maxsize

    @maxsize.setter
    def maxsize(self, value: int):
        self._maxsize = value
        self._trim()

    @property
    def key_map_size(self) -> int:
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

    def lookup(self, keys: set[K]) -> tuple[dict[K, ObfuscationResult], set[K]]:
        """Return (hits, misses) for the given statement keys.

        Keys in the negative cache are excluded from both: they are neither a hit
        (no result to return) nor a miss (must not be re-fetched).
        """
        hits: dict[K, ObfuscationResult] = {}
        misses: set[K] = set()
        ignored = 0

        for key in keys:
            if key in self._ignored_keys:
                self._ignored_keys.move_to_end(key)
                ignored += 1
                continue
            sig = self._key_to_sig.get(key)
            if sig is not None:
                self._key_to_sig.move_to_end(key)
                result = self._sig_to_result.get(sig)
                if result is not None:
                    self._sig_to_result.move_to_end(sig)
                    self._hits += 1
                    hits[key] = result
                    continue
            self._misses += 1
            misses.add(key)

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

    def mark_ignored(self, keys: set[K]) -> None:
        """Record keys that resolve to nothing usable so future lookups skip them.

        The caller is responsible for deciding what is non-cacheable, since whether a rejection is
        permanent depends on the source table. Entries are forgotten via :meth:`evict` when their
        key disappears from the source table.
        """
        for key in keys:
            # Drop any stale positive mapping so an ignored key can never resurface as a
            # hit (e.g. if its signature is later repopulated by another key after this
            # negative entry is LRU-trimmed).
            self._key_to_sig.pop(key, None)
            self._ignored_keys[key] = None
            self._ignored_keys.move_to_end(key)
        if keys:
            self._trim_ignored()
            logger.debug("mark_ignored: added=%d ignored_map=%d", len(keys), len(self._ignored_keys))

    def populate(self, raw_texts: dict[K, str]) -> tuple[dict[K, ObfuscationResult], set[K]]:
        """Obfuscate raw texts and store the results.

        Returns (results, failures), where failures are the keys whose text could not be
        obfuscated. Obfuscation depends only on the text, so a failure will recur for as long as
        the key keeps resolving to that text; callers that know the text is stable should pass
        these to :meth:`mark_ignored` rather than re-fetching them every collection.
        """
        results: dict[K, ObfuscationResult] = {}
        failures: set[K] = set()

        for key, raw_text in raw_texts.items():
            result = self._obfuscate_single(raw_text)
            if result is None:
                failures.add(key)
                continue

            self._key_to_sig[key] = result.query_signature
            self._trim_keys()

            if result.query_signature not in self._sig_to_result:
                self._sig_to_result[result.query_signature] = result
                self._trim_sig()
            else:
                self._sig_to_result.move_to_end(result.query_signature)

            results[key] = result

        logger.debug(
            "populate: input=%d obfuscated=%d failed=%d key_map=%d sig_map=%d",
            len(raw_texts),
            len(results),
            len(failures),
            len(self._key_to_sig),
            len(self._sig_to_result),
        )
        return results, failures

    def evict(self, keys: set[K]) -> None:
        """Forget all state (positive and negative) for keys that left the source table."""
        for key in keys:
            self._key_to_sig.pop(key, None)
            self._ignored_keys.pop(key, None)
        if keys:
            logger.debug(
                "evict: removed=%d key_map=%d ignored_map=%d",
                len(keys),
                len(self._key_to_sig),
                len(self._ignored_keys),
            )

    def _obfuscate_single(self, raw_text: str) -> ObfuscationResult | None:
        return obfuscate_statement(raw_text, self._obfuscate_options, self._log_unobfuscated_queries)

    def _trim(self):
        self._trim_keys()
        self._trim_sig()
        self._trim_ignored()

    def _trim_keys(self):
        while len(self._key_to_sig) > self._maxsize:
            self._key_to_sig.popitem(last=False)

    def _trim_sig(self):
        while len(self._sig_to_result) > self._maxsize:
            self._sig_to_result.popitem(last=False)

    def _trim_ignored(self):
        while len(self._ignored_keys) > self._maxsize:
            self._ignored_keys.popitem(last=False)
