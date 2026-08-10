# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Unit tests for resolve_obfuscations."""

import logging
from unittest import mock

from datadog_checks.base.utils.db.obfuscation_lookup import (
    ObfuscationLookup,
    TextDisposition,
    resolve_obfuscations,
)

DDIGNORE = '/* DDIGNORE */ SELECT 1'
INSUFFICIENT_PRIVILEGE = '<insufficient privilege>'


def classify(text):
    """A classifier shaped like the one Postgres will use, covering all three dispositions."""
    if text.startswith('/* DDIGNORE */'):
        return TextDisposition.IGNORE
    if text == INSUFFICIENT_PRIVILEGE:
        return TextDisposition.SKIP
    return TextDisposition.CACHE


class FakeFetcher:
    """Stands in for the integration's text query, recording what it was asked for."""

    def __init__(self, texts):
        self.texts = texts
        self.calls = []

    def __call__(self, keys):
        self.calls.append(set(keys))
        return {key: self.texts[key] for key in keys if key in self.texts}

    @property
    def requested(self):
        """Every key this fetcher was ever asked to resolve, across all calls."""
        return set().union(*self.calls) if self.calls else set()


def make_lookup(maxsize=100):
    return ObfuscationLookup(maxsize=maxsize, obfuscate_options='{}')


class TestResolveObfuscations:
    def test_empty_changed_keys_skips_the_fetch(self):
        lookup = make_lookup()
        fetcher = FakeFetcher({})
        result = resolve_obfuscations(lookup, set(), set(), fetcher, classify)
        assert result.results == {}
        assert result.stats.hits == 0
        assert result.stats.misses == 0
        assert fetcher.calls == []

    def test_first_cycle_fetches_and_obfuscates(self):
        lookup = make_lookup()
        fetcher = FakeFetcher({1: 'SELECT 1', 2: 'SELECT 2'})
        result = resolve_obfuscations(lookup, {1, 2}, {1, 2}, fetcher, classify)
        assert set(result.results) == {1, 2}
        assert result.stats.hits == 0
        assert result.stats.misses == 2
        assert result.stats.fetched == 2

    def test_second_cycle_serves_from_cache_without_fetching(self):
        lookup = make_lookup()
        fetcher = FakeFetcher({1: 'SELECT 1', 2: 'SELECT 2'})
        resolve_obfuscations(lookup, {1, 2}, {1, 2}, fetcher, classify)

        second = FakeFetcher({1: 'SELECT 1', 2: 'SELECT 2'})
        result = resolve_obfuscations(lookup, {1, 2}, {1, 2}, second, classify)
        assert set(result.results) == {1, 2}
        assert result.stats.hits == 2
        assert result.stats.misses == 0
        assert second.calls == []

    def test_ignored_text_is_fetched_once_then_never_again(self):
        lookup = make_lookup()
        fetcher = FakeFetcher({1: DDIGNORE, 2: 'SELECT 2'})

        first = resolve_obfuscations(lookup, {1, 2}, {1, 2}, fetcher, classify)
        assert 1 not in first.results
        assert 2 in first.results
        assert first.stats.ignored == 1

        second = FakeFetcher({1: DDIGNORE, 2: 'SELECT 2'})
        result = resolve_obfuscations(lookup, {1, 2}, {1, 2}, second, classify)
        assert 1 not in result.results
        assert 1 not in second.requested

    def test_skipped_text_is_retried_next_cycle(self):
        lookup = make_lookup()
        fetcher = FakeFetcher({1: INSUFFICIENT_PRIVILEGE})

        result = resolve_obfuscations(lookup, {1}, {1}, fetcher, classify)
        assert result.results == {}
        assert result.stats.ignored == 0

        # The privilege was granted; the same key now resolves.
        second = FakeFetcher({1: 'SELECT 1'})
        result = resolve_obfuscations(lookup, {1}, {1}, second, classify)
        assert 1 in second.requested
        assert 1 in result.results

    def test_empty_text_is_retried_and_never_classified(self):
        lookup = make_lookup()
        fetcher = FakeFetcher({1: ''})
        classifier = mock.Mock(side_effect=classify)

        result = resolve_obfuscations(lookup, {1}, {1}, fetcher, classifier)
        assert result.results == {}
        assert classifier.call_count == 0

        second = FakeFetcher({1: 'SELECT 1'})
        result = resolve_obfuscations(lookup, {1}, {1}, second, classify)
        assert 1 in second.requested
        assert 1 in result.results

    def test_obfuscation_failures_are_negative_cached(self):
        lookup = make_lookup()

        def obfuscate(raw_text, _options):
            if raw_text == 'BAD':
                raise RuntimeError('cannot obfuscate')
            return {'query': raw_text, 'metadata': {}}

        with mock.patch(
            'datadog_checks.base.utils.db.obfuscation_lookup.obfuscate_sql_with_metadata',
            side_effect=obfuscate,
        ):
            fetcher = FakeFetcher({1: 'BAD', 2: 'SELECT 2'})
            first = resolve_obfuscations(lookup, {1, 2}, {1, 2}, fetcher, classify)
            assert 1 not in first.results
            assert first.stats.failed == 1
            assert first.stats.ignored == 1

            second = FakeFetcher({1: 'BAD', 2: 'SELECT 2'})
            resolve_obfuscations(lookup, {1, 2}, {1, 2}, second, classify)
            assert 1 not in second.requested

    # --- retention ---

    def test_a_key_absent_from_the_live_set_is_dropped(self):
        """Retention reclaims entries for statements that left the source table.

        The cached result was not wrong -- a key determines its text -- it was unreachable, and
        holding it would keep the cache pinned at maxsize.
        """
        lookup = make_lookup()
        resolve_obfuscations(lookup, {1, 2}, {1, 2}, FakeFetcher({1: 'SELECT 1', 2: 'SELECT 2'}), classify)
        assert lookup.key_map_size == 2

        # Key 1 is gone from the source table, and nothing changed this collection.
        result = resolve_obfuscations(lookup, {2}, set(), FakeFetcher({}), classify)
        assert result.stats.dropped == 1
        assert lookup.key_map_size == 1

        # It comes back, so its text has to be fetched again.
        fetcher = FakeFetcher({1: 'SELECT 1'})
        result = resolve_obfuscations(lookup, {1, 2}, {1}, fetcher, classify)
        assert fetcher.requested == {1}
        assert result.stats.hits == 0

    def test_retention_runs_on_a_collection_with_nothing_changed(self):
        """Departures are noticed even when no statement executed, so the cache cannot grow
        stale on a quiet instance."""
        lookup = make_lookup()
        resolve_obfuscations(lookup, {1}, {1}, FakeFetcher({1: 'SELECT 1'}), classify)

        fetcher = FakeFetcher({})
        result = resolve_obfuscations(lookup, set(), set(), fetcher, classify)
        assert result.stats.dropped == 1
        assert lookup.key_map_size == 0
        assert fetcher.calls == []

    def test_retention_clears_the_negative_cache(self):
        lookup = make_lookup()
        resolve_obfuscations(lookup, {1}, {1}, FakeFetcher({1: DDIGNORE}), classify)
        assert lookup.ignored_map_size == 1

        resolve_obfuscations(lookup, set(), set(), FakeFetcher({}), classify)
        assert lookup.ignored_map_size == 0

        fetcher = FakeFetcher({1: 'SELECT 1'})
        result = resolve_obfuscations(lookup, {1}, {1}, fetcher, classify)
        assert 1 in fetcher.requested
        assert 1 in result.results

    def test_a_live_key_is_kept_even_while_another_holder_leaves(self):
        """The case a vanished-key argument gets wrong: MySQL keys counters on (schema, digest)
        but caches on the digest, so one schema going quiet must not evict a digest another
        schema is still running."""
        lookup = make_lookup()
        counter_keys = {('shop_a', 'digest1'), ('shop_b', 'digest1')}
        live = {digest for _schema, digest in counter_keys}
        resolve_obfuscations(lookup, live, live, FakeFetcher({'digest1': 'SELECT 1'}), classify)

        # shop_a's row leaves; shop_b is still running the same digest.
        counter_keys = {('shop_b', 'digest1')}
        live = {digest for _schema, digest in counter_keys}
        fetcher = FakeFetcher({'digest1': 'SELECT 1'})
        result = resolve_obfuscations(lookup, live, live, fetcher, classify)
        assert result.stats.dropped == 0
        assert result.stats.hits == 1
        assert fetcher.calls == []

    def test_changed_keys_outside_the_live_set_are_reported(self, caplog):
        lookup = make_lookup()
        with caplog.at_level(logging.WARNING):
            resolve_obfuscations(lookup, {1}, {1, 2}, FakeFetcher({1: 'SELECT 1', 2: 'SELECT 2'}), classify)
        assert 'projected inconsistently' in caplog.text

    # --- fetch behaviour ---

    def test_unresolvable_keys_stay_misses(self):
        """A fetch may return fewer keys than asked for; the rest are retried, not cached."""
        lookup = make_lookup()
        fetcher = FakeFetcher({1: 'SELECT 1'})

        result = resolve_obfuscations(lookup, {1, 2}, {1, 2}, fetcher, classify)
        assert result.stats.misses == 2
        assert result.stats.fetched == 1
        assert set(result.results) == {1}

        second = FakeFetcher({2: 'SELECT 2'})
        result = resolve_obfuscations(lookup, {1, 2}, {1, 2}, second, classify)
        assert second.requested == {2}
        assert 2 in result.results

    def test_keys_sharing_text_share_one_result(self):
        lookup = make_lookup()
        fetcher = FakeFetcher({1: 'SELECT 1', 2: 'SELECT 1'})
        result = resolve_obfuscations(lookup, {1, 2}, {1, 2}, fetcher, classify)
        assert result.results[1].query_signature == result.results[2].query_signature
        assert lookup.signature_map_size == 1
