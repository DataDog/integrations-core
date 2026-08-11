# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import logging
from collections import OrderedDict
from collections.abc import Hashable

from .obfuscation import ObfuscationResult, obfuscate_statement

logger = logging.getLogger(__name__)


class ObfuscationLookup[K: Hashable]:
    """LRU cache mapping statement identity keys to obfuscated query results.

    ``K`` is whatever identifies a statement in the source table: a
    ``(queryid, dbid, userid)`` triple for ``pg_stat_statements``, a digest string for MySQL's
    ``events_statements_summary_by_digest``, and so on. The cache never interprets the key.

    Caching is only sound where the key functionally determines the text, which is why both of
    those work: a queryid is derived from the normalized parse tree and a digest from the
    normalized token stream, so neither can name two statements. A source whose identity outlives
    the text it named, such as MySQL's ``prepared_statements_instances``, must go through
    :func:`~.obfuscation.obfuscate_statement` instead.

    A lookup resolves a key to one of three outcomes:

    - hit: the obfuscated result is cached, avoiding both the text fetch and FFI obfuscation.
      Stored as two tiers, key -> query_signature -> result, so multiple keys sharing a
      query_signature share one result.
    - miss: nothing is cached for the key; the caller must fetch its text and pass it to
      :meth:`populate` to obfuscate, store, and discard the raw text.
    - ignored: the key is known to resolve to nothing usable. These are neither hit nor miss;
      lookup skips them so they are never fetched again.

    The cache does not decide what is non-cacheable; :meth:`mark_ignored` is driven by
    :func:`~.resolver.resolve_obfuscations`, which owns that policy. The cache owns only storage
    and lifecycle. All three tiers are LRU-bounded by ``maxsize``, and :meth:`retain` drops the
    keys that have left the source table so entries do not sit at that bound long after the
    statements they describe.
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

        Entries are forgotten via :meth:`retain` once their key disappears from the source table.
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

    def retain(self, live_keys: set[K]) -> int:
        """Forget all state, positive and negative, for keys absent from *live_keys*.

        Returns how many keys were dropped.

        Callers pass the keys currently in the source table rather than the ones that left, so a
        caller whose cache key is a projection of a wider counter key cannot report a key as gone
        while another live row still needs it. MySQL is the case in point: its counters are keyed
        on ``(schema, digest)`` but one digest has one text, so a digest is only finished once no
        schema references it.

        This reclaims memory rather than protecting correctness. Because a key determines its
        text, an entry that outlives its key is unreachable rather than wrong. It does need to run
        on every collection, including quiet ones, or the cache sits at ``maxsize`` indefinitely.
        """
        stale = (self._key_to_sig.keys() | self._ignored_keys.keys()) - live_keys
        for key in stale:
            self._key_to_sig.pop(key, None)
            self._ignored_keys.pop(key, None)
        if stale:
            logger.debug(
                "retain: live=%d dropped=%d key_map=%d ignored_map=%d",
                len(live_keys),
                len(stale),
                len(self._key_to_sig),
                len(self._ignored_keys),
            )
        return len(stale)

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
