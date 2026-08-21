# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from __future__ import annotations

import logging
from collections import OrderedDict
from dataclasses import dataclass

from datadog_checks.base.utils.db.sql import compute_sql_signature
from datadog_checks.base.utils.db.utils import obfuscate_sql_with_metadata

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ObfuscationResult:
    obfuscated_statement: str
    query_signature: str
    tables: list[str] | None
    commands: list[str] | None
    comments: list[str] | None


def obfuscate_statement(
    raw_text: str, obfuscate_options: str, log_unobfuscated_queries: bool = False
) -> ObfuscationResult | None:
    """Obfuscate one statement via the FFI, returning None if it cannot be obfuscated.

    Exposed separately from :class:`ObfuscationLookup` for statement sources whose identity does not
    determine their text, which therefore cannot be cached.
    """
    try:
        statement = obfuscate_sql_with_metadata(raw_text, obfuscate_options)
    except Exception as e:
        if log_unobfuscated_queries:
            logger.warning("Failed to obfuscate query=[%s] | err=[%s]", raw_text, e)
        else:
            logger.debug("Failed to obfuscate query | err=[%s]", e)
        return None

    obfuscated_statement = statement['query']
    metadata = statement['metadata']
    return ObfuscationResult(
        obfuscated_statement=obfuscated_statement,
        query_signature=compute_sql_signature(obfuscated_statement),
        tables=metadata.get('tables', None),
        commands=metadata.get('commands', None),
        comments=metadata.get('comments', None),
    )


class ObfuscationLookup:
    """LRU cache mapping statement digests to obfuscated query results.

    MySQL derives a digest by hashing the normalized statement text, so ``digest_text`` is a pure
    function of the digest: the same statement seen under several schemas needs one cache entry, and
    a digest's text never changes. That makes the digest a sufficient cache key and makes any
    outcome for a digest — including a failure — permanently valid.

    A lookup resolves a digest to one of three outcomes:

    - hit: the obfuscated result is cached, avoiding both the text fetch and FFI obfuscation.
      Stored as two tiers, digest -> query_signature -> result, so the several digests that
      normalize to one signature share a single result.
    - miss: nothing is cached for the digest; the caller must fetch its text and pass it to
      :meth:`populate` to obfuscate, store, and discard the raw text.
    - ignored: the digest is known to resolve to nothing usable, either because the caller
      rejected its text (e.g. an ``EXPLAIN`` statement) or because obfuscation failed. These are
      neither hit nor miss; lookup skips them so they are never fetched again.

    The caller decides what is non-cacheable (via :meth:`mark_ignored`); the cache only owns
    storage and lifecycle. All three tiers are LRU-bounded by :attr:`maxsize` and cleared for a
    digest by :meth:`evict` when it leaves the digest table.
    """

    def __init__(self, maxsize: int, obfuscate_options: str, log_unobfuscated_queries: bool = False):
        self._maxsize = maxsize
        self._obfuscate_options = obfuscate_options
        self._log_unobfuscated_queries = log_unobfuscated_queries

        self._digest_to_sig: OrderedDict[str, str] = OrderedDict()
        self._sig_to_result: OrderedDict[str, ObfuscationResult] = OrderedDict()
        # Negative cache: digests we have learned resolve to nothing cacheable.
        self._ignored_digests: OrderedDict[str, None] = OrderedDict()

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
    def digest_map_size(self) -> int:
        return len(self._digest_to_sig)

    @property
    def signature_map_size(self) -> int:
        return len(self._sig_to_result)

    @property
    def ignored_map_size(self) -> int:
        return len(self._ignored_digests)

    @property
    def hits(self) -> int:
        return self._hits

    @property
    def misses(self) -> int:
        return self._misses

    def reset_stats(self):
        self._hits = 0
        self._misses = 0

    def lookup(self, digests: set[str]) -> tuple[dict[str, ObfuscationResult], set[str]]:
        """Return (hits, misses) for the given digests.

        Digests in the negative cache are excluded from both: they are neither a hit (no result to
        return) nor a miss (must not be re-fetched).
        """
        hits: dict[str, ObfuscationResult] = {}
        misses: set[str] = set()
        ignored = 0

        for digest in digests:
            if digest in self._ignored_digests:
                self._ignored_digests.move_to_end(digest)
                ignored += 1
                continue
            sig = self._digest_to_sig.get(digest)
            if sig is not None:
                self._digest_to_sig.move_to_end(digest)
                result = self._sig_to_result.get(sig)
                if result is not None:
                    self._sig_to_result.move_to_end(sig)
                    self._hits += 1
                    hits[digest] = result
                    continue
            self._misses += 1
            misses.add(digest)

        logger.debug(
            "lookup: requested=%d hits=%d misses=%d ignored=%d digest_map=%d sig_map=%d ignored_map=%d",
            len(digests),
            len(hits),
            len(misses),
            ignored,
            len(self._digest_to_sig),
            len(self._sig_to_result),
            len(self._ignored_digests),
        )
        return hits, misses

    def mark_ignored(self, digests: set[str]) -> None:
        """Record digests that resolve to nothing usable so future lookups skip them.

        Because a digest's text never changes, both caller-side rejection and obfuscation failure
        are permanent outcomes, so caching them costs one fetch per digest ever rather than one per
        collection. Entries are forgotten via :meth:`evict` when the digest disappears from the
        digest table.
        """
        if not digests:
            return
        for digest in digests:
            # Drop any stale positive mapping so an ignored digest can never resurface as a hit
            # (e.g. if its signature is later repopulated by another digest after this negative
            # entry is LRU-trimmed).
            self._digest_to_sig.pop(digest, None)
            self._ignored_digests[digest] = None
            self._ignored_digests.move_to_end(digest)
        self._trim_ignored()
        logger.debug("mark_ignored: added=%d ignored_map=%d", len(digests), len(self._ignored_digests))

    def populate(self, raw_texts: dict[str, str]) -> tuple[dict[str, ObfuscationResult], set[str]]:
        """Obfuscate raw texts and store the results.

        Returns (results, failures), where failures are the digests whose text could not be
        obfuscated. The caller should pass those to :meth:`mark_ignored`, since retrying them is
        guaranteed to fail again.
        """
        results: dict[str, ObfuscationResult] = {}
        failures: set[str] = set()

        for digest, raw_text in raw_texts.items():
            result = self._obfuscate_single(raw_text)
            if result is None:
                failures.add(digest)
                continue

            self._digest_to_sig[digest] = result.query_signature
            self._trim_digests()

            if result.query_signature not in self._sig_to_result:
                self._sig_to_result[result.query_signature] = result
                self._trim_sig()
            else:
                self._sig_to_result.move_to_end(result.query_signature)

            results[digest] = result

        logger.debug(
            "populate: input=%d obfuscated=%d failed=%d digest_map=%d sig_map=%d",
            len(raw_texts),
            len(results),
            len(failures),
            len(self._digest_to_sig),
            len(self._sig_to_result),
        )
        return results, failures

    def evict(self, digests: set[str]) -> None:
        """Forget all state (positive and negative) for digests that left the digest table."""
        if not digests:
            return
        for digest in digests:
            self._digest_to_sig.pop(digest, None)
            self._ignored_digests.pop(digest, None)
        logger.debug(
            "evict: removed=%d digest_map=%d ignored_map=%d",
            len(digests),
            len(self._digest_to_sig),
            len(self._ignored_digests),
        )

    def _obfuscate_single(self, raw_text: str) -> ObfuscationResult | None:
        return obfuscate_statement(raw_text, self._obfuscate_options, self._log_unobfuscated_queries)

    def _trim(self):
        self._trim_digests()
        self._trim_sig()
        self._trim_ignored()

    def _trim_digests(self):
        while len(self._digest_to_sig) > self._maxsize:
            self._digest_to_sig.popitem(last=False)

    def _trim_sig(self):
        while len(self._sig_to_result) > self._maxsize:
            self._sig_to_result.popitem(last=False)

    def _trim_ignored(self):
        while len(self._ignored_digests) > self._maxsize:
            self._ignored_digests.popitem(last=False)
