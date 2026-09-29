# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Unit tests for ObfuscationLookup."""

from unittest import mock

from datadog_checks.base.utils.db.query_metrics import ObfuscationLookup


class TestObfuscationLookup:
    def _make_lookup(self, maxsize=100):
        return ObfuscationLookup(maxsize=maxsize, obfuscate_options='{}')

    def test_empty_lookup_all_misses(self):
        lk = self._make_lookup()
        hits, misses = lk.lookup({(1, 1, 1), (2, 1, 1), (3, 1, 1)})
        assert hits == {}
        assert misses == {(1, 1, 1), (2, 1, 1), (3, 1, 1)}

    def test_populate_then_lookup(self):
        lk = self._make_lookup()
        lk.populate({(1, 1, 1): 'SELECT 1', (2, 1, 1): 'SELECT 2'})
        hits, misses = lk.lookup({(1, 1, 1), (2, 1, 1), (3, 1, 1)})
        assert (1, 1, 1) in hits
        assert (2, 1, 1) in hits
        assert misses == {(3, 1, 1)}
        assert hits[(1, 1, 1)].obfuscated_query is not None
        assert hits[(1, 1, 1)].query_signature is not None

    def test_hit_and_miss_counters(self):
        lk = self._make_lookup()
        lk.populate({(1, 1, 1): 'SELECT 1'})
        lk.reset_stats()
        lk.lookup({(1, 1, 1), (2, 1, 1)})
        assert lk.hits == 1
        assert lk.misses == 1

    def test_retain_drops_keys_absent_from_the_live_set(self):
        lk = self._make_lookup()
        lk.populate({(1, 1, 1): 'SELECT 1', (2, 1, 1): 'SELECT 2'})
        assert lk.retain({(2, 1, 1)}) == 1
        hits, misses = lk.lookup({(1, 1, 1), (2, 1, 1)})
        assert (1, 1, 1) in misses
        assert (2, 1, 1) in hits

    def test_retain_keeps_everything_when_all_keys_are_live(self):
        lk = self._make_lookup()
        lk.populate({(1, 1, 1): 'SELECT 1', (2, 1, 1): 'SELECT 2'})
        assert lk.retain({(1, 1, 1), (2, 1, 1)}) == 0
        hits, _ = lk.lookup({(1, 1, 1), (2, 1, 1)})
        assert len(hits) == 2

    def test_retain_ignores_live_keys_it_has_never_seen(self):
        """The live set is the whole snapshot, most of which was never a cache miss."""
        lk = self._make_lookup()
        lk.populate({(1, 1, 1): 'SELECT 1'})
        assert lk.retain({(1, 1, 1), (9, 9, 9)}) == 0
        assert lk.key_map_size == 1

    def test_multiple_keys_share_signature(self):
        """Different keys with the same normalized SQL share one ObfuscationResult."""
        lk = self._make_lookup()
        lk.populate({(1, 1, 1): 'SELECT 1', (2, 1, 1): 'SELECT 1'})
        hits, _ = lk.lookup({(1, 1, 1), (2, 1, 1)})
        assert hits[(1, 1, 1)].query_signature == hits[(2, 1, 1)].query_signature
        assert lk.key_map_size == 2
        assert lk.signature_map_size == 1

    def test_lru_eviction_on_max_size(self):
        lk = self._make_lookup(maxsize=2)
        lk.populate({(1, 1, 1): 'SELECT 1', (2, 2, 2): 'SELECT 2', (3, 3, 3): 'SELECT 3'})
        assert lk.key_map_size == 2
        _, misses = lk.lookup({(1, 1, 1)})
        assert (1, 1, 1) in misses

    def test_populate_returns_results(self):
        lk = self._make_lookup()
        results, failures = lk.populate({(1, 1, 1): 'SELECT 1', (2, 1, 1): 'SELECT 2'})
        assert (1, 1, 1) in results
        assert (2, 1, 1) in results
        assert results[(1, 1, 1)].obfuscated_query is not None
        assert failures == set()

    def test_populate_reports_obfuscation_failures(self):
        lk = self._make_lookup()

        def obfuscate(raw_text, _options):
            if raw_text == 'BAD':
                raise RuntimeError('cannot obfuscate')
            return {'query': raw_text, 'metadata': {}}

        with mock.patch(
            'datadog_checks.base.utils.db.query_metrics.obfuscation.obfuscate_sql_with_metadata',
            side_effect=obfuscate,
        ):
            results, failures = lk.populate({(1, 1, 1): 'SELECT 1', (2, 1, 1): 'BAD'})

        assert (1, 1, 1) in results
        assert failures == {(2, 1, 1)}
        # The failed key is not cached either way, so it stays a miss until the caller ignores it.
        assert lk.key_map_size == 1
        _, misses = lk.lookup({(2, 1, 1)})
        assert misses == {(2, 1, 1)}

    def test_retain_does_not_remove_shared_signature(self):
        """Dropping one key removes tier-1 mapping but keeps tier-2 if other keys share it."""
        lk = self._make_lookup()
        lk.populate({(1, 1, 1): 'SELECT 1', (2, 1, 1): 'SELECT 1'})
        lk.retain({(2, 1, 1)})
        hits, _ = lk.lookup({(2, 1, 1)})
        assert (2, 1, 1) in hits

    def test_retain_reclaims_orphaned_results(self):
        """Dropping the key mapping alone would leave the obfuscated text it named behind."""
        lk = self._make_lookup()
        lk.populate({(1, 1, 1): 'SELECT 1', (2, 1, 1): 'SELECT 2'})
        lk.retain({(2, 1, 1)})
        assert lk.key_map_size == 1
        assert lk.signature_map_size == 1

    def test_retain_reclaims_results_orphaned_by_lru_trimming(self):
        """A key also leaves by trimming, so the result sweep cannot be conditional on retain."""
        lk = self._make_lookup(maxsize=2)
        lk.populate({(1, 1, 1): 'SELECT 1', (2, 1, 1): 'SELECT 2'})
        # Two keys now share 'SELECT 2', so adding the third trims (1, 1, 1) off the key map
        # without pushing the result map past maxsize.
        lk.populate({(3, 1, 1): 'SELECT 2'})
        assert lk.key_map_size == 2
        assert lk.signature_map_size == 2

        assert lk.retain({(2, 1, 1), (3, 1, 1)}) == 0
        assert lk.signature_map_size == 1

    def test_retained_result_is_not_displaced_by_an_orphan(self):
        """An orphan left in the result map would evict a live statement once the map fills."""
        lk = self._make_lookup(maxsize=2)
        lk.populate({(1, 1, 1): 'SELECT 1', (2, 1, 1): 'SELECT 2'})
        # Make the soon-to-be orphan the most recently used of the two.
        lk.lookup({(1, 1, 1)})
        lk.retain({(2, 1, 1)})
        lk.populate({(3, 1, 1): 'SELECT 3'})

        hits, _ = lk.lookup({(2, 1, 1)})
        assert (2, 1, 1) in hits

    def test_lookup_updates_lru_order(self):
        lk = self._make_lookup(maxsize=2)
        lk.populate({(1, 1, 1): 'SELECT 1', (2, 2, 2): 'SELECT 2'})
        lk.lookup({(1, 1, 1)})
        lk.populate({(3, 3, 3): 'SELECT 3'})
        hits, _ = lk.lookup({(1, 1, 1)})
        assert (1, 1, 1) in hits
        _, misses = lk.lookup({(2, 2, 2)})
        assert (2, 2, 2) in misses

    def test_maxsize_setter_trims_immediately(self):
        lk = self._make_lookup(maxsize=3)
        lk.populate({(1, 1, 1): 'SELECT 1', (2, 2, 2): 'SELECT 2', (3, 3, 3): 'SELECT 3'})
        assert lk.key_map_size == 3

        lk.maxsize = 1
        assert lk.maxsize == 1
        assert lk.key_map_size == 1
        assert lk.signature_map_size == 1

    def test_maxsize_setter_growing_does_not_evict(self):
        lk = self._make_lookup(maxsize=2)
        lk.populate({(1, 1, 1): 'SELECT 1', (2, 2, 2): 'SELECT 2'})
        lk.maxsize = 10
        hits, _ = lk.lookup({(1, 1, 1), (2, 2, 2)})
        assert len(hits) == 2

    def test_maxsize_setter_trims_the_negative_cache(self):
        lk = self._make_lookup(maxsize=3)
        lk.mark_ignored({(1, 1, 1), (2, 2, 2), (3, 3, 3)})
        assert lk.ignored_map_size == 3
        lk.maxsize = 1
        assert lk.ignored_map_size == 1

    def test_keys_are_opaque_to_the_cache(self):
        """Any hashable works as a key; MySQL uses a digest string rather than a tuple."""
        lk = self._make_lookup()
        lk.populate({'digest_a': 'SELECT 1', 'digest_b': 'SELECT 2'})
        hits, misses = lk.lookup({'digest_a', 'digest_c'})
        assert 'digest_a' in hits
        assert misses == {'digest_c'}
        lk.retain({'digest_b'})
        _, misses = lk.lookup({'digest_a'})
        assert misses == {'digest_a'}

    # --- negative cache (ignored keys) ---

    def test_mark_ignored_excludes_from_hits_and_misses(self):
        """A negatively-cached key is neither a hit nor a miss on lookup."""
        lk = self._make_lookup()
        lk.mark_ignored({(1, 1, 1)})
        hits, misses = lk.lookup({(1, 1, 1), (2, 1, 1)})
        assert (1, 1, 1) not in hits
        assert (1, 1, 1) not in misses
        assert misses == {(2, 1, 1)}
        assert lk.ignored_map_size == 1

    def test_ignored_keys_do_not_increment_miss_counter(self):
        lk = self._make_lookup()
        lk.mark_ignored({(1, 1, 1)})
        lk.reset_stats()
        lk.lookup({(1, 1, 1)})
        assert lk.misses == 0
        assert lk.hits == 0

    def test_retain_forgets_ignored_key(self):
        """Dropping a departed key clears its negative-cache entry so it can be re-evaluated."""
        lk = self._make_lookup()
        lk.mark_ignored({(1, 1, 1)})
        assert lk.retain(set()) == 1
        assert lk.ignored_map_size == 0
        _, misses = lk.lookup({(1, 1, 1)})
        assert (1, 1, 1) in misses

    def test_ignored_keys_lru_trimmed_to_maxsize(self):
        lk = self._make_lookup(maxsize=2)
        lk.mark_ignored({(1, 1, 1), (2, 2, 2), (3, 3, 3)})
        assert lk.ignored_map_size == 2

    def test_mark_ignored_drops_stale_positive_mapping(self):
        """An ignored key must not resurface as a hit via a stale tier-1 mapping.

        Reproduces the case where a key keeps its tier-1 mapping after its tier-2
        signature was evicted: marking it ignored must drop the tier-1 entry so that,
        even after the negative entry is trimmed and the signature is repopulated by
        another key, the ignored key never produces a positive hit.
        """
        lk = self._make_lookup()
        # Two keys share the same normalized SQL (one signature).
        lk.populate({(1, 1, 1): 'SELECT 1', (2, 1, 1): 'SELECT 1'})
        assert lk.key_map_size == 2

        # Key (1, 1, 1) turns out to be ignorable; its tier-1 mapping must be dropped.
        lk.mark_ignored({(1, 1, 1)})
        assert (1, 1, 1) not in lk._key_to_sig

        # The shared signature is still cached (via the other key), but the ignored key
        # must not hit it.
        hits, misses = lk.lookup({(1, 1, 1)})
        assert (1, 1, 1) not in hits
        assert (1, 1, 1) not in misses
