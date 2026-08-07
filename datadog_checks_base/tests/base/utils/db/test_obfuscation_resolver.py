# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Unit tests for resolve_obfuscations."""

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
        result = resolve_obfuscations(lookup, {1, 2}, set(), fetcher, classify)
        assert set(result.results) == {1, 2}
        assert result.stats.hits == 0
        assert result.stats.misses == 2
        assert result.stats.fetched == 2

    def test_second_cycle_serves_from_cache_without_fetching(self):
        lookup = make_lookup()
        fetcher = FakeFetcher({1: 'SELECT 1', 2: 'SELECT 2'})
        resolve_obfuscations(lookup, {1, 2}, set(), fetcher, classify)

        second = FakeFetcher({1: 'SELECT 1', 2: 'SELECT 2'})
        result = resolve_obfuscations(lookup, {1, 2}, set(), second, classify)
        assert set(result.results) == {1, 2}
        assert result.stats.hits == 2
        assert result.stats.misses == 0
        assert second.calls == []

    def test_ignored_text_is_fetched_once_then_never_again(self):
        lookup = make_lookup()
        fetcher = FakeFetcher({1: DDIGNORE, 2: 'SELECT 2'})

        first = resolve_obfuscations(lookup, {1, 2}, set(), fetcher, classify)
        assert 1 not in first.results
        assert 2 in first.results
        assert first.stats.ignored == 1

        second = FakeFetcher({1: DDIGNORE, 2: 'SELECT 2'})
        result = resolve_obfuscations(lookup, {1, 2}, set(), second, classify)
        assert 1 not in result.results
        assert 1 not in second.requested

    def test_skipped_text_is_retried_next_cycle(self):
        lookup = make_lookup()
        fetcher = FakeFetcher({1: INSUFFICIENT_PRIVILEGE})

        result = resolve_obfuscations(lookup, {1}, set(), fetcher, classify)
        assert result.results == {}
        assert result.stats.ignored == 0

        # The privilege was granted; the same key now resolves.
        second = FakeFetcher({1: 'SELECT 1'})
        result = resolve_obfuscations(lookup, {1}, set(), second, classify)
        assert 1 in second.requested
        assert 1 in result.results

    def test_empty_text_is_retried_and_never_classified(self):
        lookup = make_lookup()
        fetcher = FakeFetcher({1: ''})
        classifier = mock.Mock(side_effect=classify)

        result = resolve_obfuscations(lookup, {1}, set(), fetcher, classifier)
        assert result.results == {}
        assert classifier.call_count == 0

        second = FakeFetcher({1: 'SELECT 1'})
        result = resolve_obfuscations(lookup, {1}, set(), second, classify)
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
            first = resolve_obfuscations(lookup, {1, 2}, set(), fetcher, classify)
            assert 1 not in first.results
            assert first.stats.failed == 1
            assert first.stats.ignored == 1

            second = FakeFetcher({1: 'BAD', 2: 'SELECT 2'})
            resolve_obfuscations(lookup, {1, 2}, set(), second, classify)
            assert 1 not in second.requested

    def test_vanished_keys_are_evicted_before_the_lookup(self):
        """A key that left and returned must not be served a result cached against the old one."""
        lookup = make_lookup()
        resolve_obfuscations(lookup, {1}, set(), FakeFetcher({1: 'SELECT 1'}), classify)

        # Key 1 vanishes and reappears in the same cycle, now with different text.
        fetcher = FakeFetcher({1: 'SELECT 999'})
        result = resolve_obfuscations(lookup, {1}, {1}, fetcher, classify)
        assert 1 in fetcher.requested
        assert result.stats.hits == 0
        assert result.results[1].obfuscated_query == 'SELECT 999'

    def test_vanished_keys_clear_the_negative_cache(self):
        lookup = make_lookup()
        resolve_obfuscations(lookup, {1}, set(), FakeFetcher({1: DDIGNORE}), classify)

        fetcher = FakeFetcher({1: 'SELECT 1'})
        result = resolve_obfuscations(lookup, {1}, {1}, fetcher, classify)
        assert 1 in fetcher.requested
        assert 1 in result.results

    def test_unresolvable_keys_stay_misses(self):
        """A fetch may return fewer keys than asked for; the rest are retried, not cached."""
        lookup = make_lookup()
        fetcher = FakeFetcher({1: 'SELECT 1'})

        result = resolve_obfuscations(lookup, {1, 2}, set(), fetcher, classify)
        assert result.stats.misses == 2
        assert result.stats.fetched == 1
        assert set(result.results) == {1}

        second = FakeFetcher({2: 'SELECT 2'})
        result = resolve_obfuscations(lookup, {1, 2}, set(), second, classify)
        assert second.requested == {2}
        assert 2 in result.results

    def test_keys_sharing_text_share_one_result(self):
        lookup = make_lookup()
        fetcher = FakeFetcher({1: 'SELECT 1', 2: 'SELECT 1'})
        result = resolve_obfuscations(lookup, {1, 2}, set(), fetcher, classify)
        assert result.results[1].query_signature == result.results[2].query_signature
        assert lookup.signature_map_size == 1
