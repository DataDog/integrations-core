# (C) Datadog, Inc. 2025-present
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
    obfuscated_query: str
    query_signature: str
    tables: list[str] | None
    commands: list[str] | None
    comments: list[str] | None


class ObfuscationLookup:
    """Two-tier cache that maps queryid -> ObfuscationResult without
    storing raw query text long-term.

    Tier 1: queryid -> query_signature  (thin, bounded to pgss_max)
    Tier 2: query_signature -> ObfuscationResult  (deduped, bounded)

    On a cache hit the caller gets the ObfuscationResult directly with no
    PG roundtrip and no FFI call.  On a miss the caller must supply the
    raw text (fetched from PG); we obfuscate it, learn the query_signature,
    store both mappings, and discard the raw text.
    """

    def __init__(self, maxsize: int, obfuscate_options: str, log_unobfuscated_queries: bool = False):
        self._maxsize = maxsize
        self._obfuscate_options = obfuscate_options
        self._log_unobfuscated_queries = log_unobfuscated_queries

        self._qid_to_sig: OrderedDict[int, str] = OrderedDict()
        self._sig_to_result: OrderedDict[str, ObfuscationResult] = OrderedDict()

        self._hits = 0
        self._misses = 0

    @property
    def queryid_map_size(self) -> int:
        return len(self._qid_to_sig)

    @property
    def signature_map_size(self) -> int:
        return len(self._sig_to_result)

    @property
    def hits(self) -> int:
        return self._hits

    @property
    def misses(self) -> int:
        return self._misses

    def reset_stats(self):
        self._hits = 0
        self._misses = 0

    def lookup(self, queryids: set[int]) -> tuple[dict[int, ObfuscationResult], set[int]]:
        """Look up ObfuscationResults for *queryids*.

        Returns (hits, misses) where hits is queryid -> ObfuscationResult
        and misses is the set of queryids that need raw text fetched from PG.
        """
        hits: dict[int, ObfuscationResult] = {}
        misses: set[int] = set()

        for qid in queryids:
            sig = self._qid_to_sig.get(qid)
            if sig is not None:
                self._qid_to_sig.move_to_end(qid)
                result = self._sig_to_result.get(sig)
                if result is not None:
                    self._sig_to_result.move_to_end(sig)
                    self._hits += 1
                    hits[qid] = result
                    continue
            self._misses += 1
            misses.add(qid)

        return hits, misses

    def populate(self, raw_texts: dict[int, str]) -> dict[int, ObfuscationResult]:
        """Obfuscate raw texts for cache-miss queryids and store the results.

        *raw_texts* maps queryid -> raw SQL text (as fetched from PG).
        Returns queryid -> ObfuscationResult for successfully obfuscated entries.
        Raw text is not retained after obfuscation.
        """
        results: dict[int, ObfuscationResult] = {}

        for qid, raw_text in raw_texts.items():
            result = self._obfuscate_single(raw_text)
            if result is None:
                continue

            self._qid_to_sig[qid] = result.query_signature
            self._trim_qid()

            if result.query_signature not in self._sig_to_result:
                self._sig_to_result[result.query_signature] = result
                self._trim_sig()
            else:
                self._sig_to_result.move_to_end(result.query_signature)

            results[qid] = result

        return results

    def evict(self, queryids: set[int]) -> None:
        """Remove tier-1 entries for queryids evicted from pgss."""
        for qid in queryids:
            self._qid_to_sig.pop(qid, None)

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

    def _trim_qid(self):
        while len(self._qid_to_sig) > self._maxsize:
            self._qid_to_sig.popitem(last=False)

    def _trim_sig(self):
        while len(self._sig_to_result) > self._maxsize:
            self._sig_to_result.popitem(last=False)
