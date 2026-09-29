# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import logging
from collections.abc import Callable, Hashable
from dataclasses import dataclass
from enum import Enum, auto

from .cache import ObfuscationLookup
from .obfuscation import ObfuscationResult

logger = logging.getLogger(__name__)


class TextKind(Enum):
    """What a fetched statement text turned out to be.

    Callers report what they saw and :func:`resolve_obfuscations` decides what to do about it. The
    distinction that matters is whether the text is the statement's own, and if it is not, whether
    that can change. An integration knows its source's quirks; the caching policy those quirks
    imply is the same everywhere, so it lives here rather than in each integration.
    """

    STATEMENT = auto()
    """The statement's own text. The normal outcome: it is obfuscated and cached."""

    EXCLUDED = auto()
    """The statement's own text, for a statement that should not be reported.

    For statements that are an artifact of monitoring rather than application traffic, such as
    queries the Agent tags with ``/* DDIGNORE */`` or the ``EXPLAIN`` statements MySQL's plan
    collection leaves behind in the digest table. Because a key determines its text, this verdict
    cannot change while the key lives, so the key is negative-cached and never fetched again.
    """

    UNAVAILABLE = auto()
    """Not the statement's text, but a placeholder standing in for it.

    For text that describes the reader rather than the statement, such as the
    ``<insufficient privilege>`` placeholder Postgres returns to a role that may later be granted
    access. The key is left a miss so the next collection fetches it again. Text that will never
    become available needs a kind of its own, since this one is retried for as long as the key
    lives.
    """


@dataclass(frozen=True, slots=True)
class ResolveStats:
    hits: int
    """Keys served from the cache, needing neither a fetch nor obfuscation."""
    misses: int
    """Keys whose text had to be fetched."""
    fetched: int
    """Texts the fetch returned. Lower than ``misses`` when a key disappeared between the snapshot
    and the fetch."""
    ignored: int
    """Keys added to the negative cache, whether excluded by the caller or rejected by the
    obfuscator."""
    failed: int
    """Keys whose text could not be obfuscated."""
    dropped: int
    """Cache entries discarded because their key is no longer in the source table."""


@dataclass(frozen=True, slots=True)
class ResolveResult[K: Hashable]:
    results: dict[K, ObfuscationResult]
    stats: ResolveStats


def resolve_obfuscations[K: Hashable](
    lookup: ObfuscationLookup[K],
    live_keys: set[K],
    changed_keys: set[K],
    fetch_texts: Callable[[set[K]], dict[K, str]],
    classify: Callable[[str], TextKind],
) -> ResolveResult[K]:
    """Resolve *changed_keys* to obfuscated results, fetching text only for cache misses.

    Both key sets belong to the cache's key space, which for a source whose counters are keyed
    more finely than its text means projecting the snapshot down first. Taking the keys that are
    present rather than the ones that left keeps that projection safe: a caller can only misstate
    what is live, which shows up in the hit rate, instead of quietly dropping an entry that
    another live row still needs.

    The remaining steps are ordered, and getting them wrong is quiet rather than loud, which is
    why they live here rather than in each integration:

    - Retention runs before the lookup, and on every collection rather than only the ones that
      produced work, so entries do not outlive the statements they describe.
    - Empty text is left a miss without consulting *classify*, so callers do not each repeat that
      guard.
    - Keys the obfuscator rejects are negative-cached alongside the :attr:`TextKind.EXCLUDED` ones.
      Obfuscation is a pure function of the text, so retrying is guaranteed to fail again; without
      this an unobfuscatable statement is re-fetched on every collection in which it changes. Both
      kinds of negative entry are forgotten by :meth:`ObfuscationLookup.retain` once the key leaves
      the source table, so neither outlives the statement it describes.

    This emits no telemetry and knows nothing about the check. Counts come back in
    :attr:`ResolveResult.stats` for the caller to report under its own metric names.

    :param live_keys: Every key in the current snapshot. Cached keys absent from it are dropped.
    :param changed_keys: Keys needing resolution this collection; a subset of *live_keys*.
    :param fetch_texts: Reads statement text for a set of keys. May return fewer keys than asked
        for; the rest stay misses and are retried next collection.
    :param classify: Reports what one non-empty text turned out to be. See :class:`TextKind`.
    """
    dropped = lookup.retain(live_keys)

    stray = changed_keys - live_keys
    if stray:
        logger.warning(
            "resolve: %d of %d changed keys are absent from live_keys, so their results are "
            "discarded on the next collection; the two sets are projected inconsistently",
            len(stray),
            len(changed_keys),
        )

    if not changed_keys:
        return ResolveResult(
            results={},
            stats=ResolveStats(hits=0, misses=0, fetched=0, ignored=0, failed=0, dropped=dropped),
        )

    hits, misses = lookup.lookup(changed_keys)
    cache_hits = len(hits)
    fetched = 0
    ignorable: set[K] = set()
    failures: set[K] = set()

    if misses:
        raw_texts = fetch_texts(misses)
        fetched = len(raw_texts)

        cacheable: dict[K, str] = {}
        for key, text in raw_texts.items():
            if not text:
                continue
            kind = classify(text)
            if kind is TextKind.EXCLUDED:
                ignorable.add(key)
            elif kind is TextKind.STATEMENT:
                cacheable[key] = text

        populated, failures = lookup.populate(cacheable)
        lookup.mark_ignored(ignorable | failures)
        hits.update(populated)

    logger.debug(
        "resolve: changed=%d hits=%d misses=%d fetched=%d ignored=%d failed=%d dropped=%d resolved=%d",
        len(changed_keys),
        cache_hits,
        len(misses),
        fetched,
        len(ignorable),
        len(failures),
        dropped,
        len(hits),
    )

    return ResolveResult(
        results=hits,
        stats=ResolveStats(
            hits=cache_hits,
            misses=len(misses),
            fetched=fetched,
            ignored=len(ignorable) + len(failures),
            failed=len(failures),
            dropped=dropped,
        ),
    )
