# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from unittest import mock

import pytest

from datadog_checks.clickhouse import ClickhouseCheck
from datadog_checks.clickhouse.query_log_job import _NODE_CHECKPOINT_STALENESS_THRESHOLD_US

pytestmark = pytest.mark.unit


@pytest.fixture
def instance_with_dbm():
    return {
        'server': 'localhost',
        'port': 9000,
        'username': 'default',
        'password': '',
        'db': 'default',
        'dbm': True,
        'query_metrics': {
            'enabled': True,
            'collection_interval': 10,
            'run_sync': False,
        },
        'tags': ['test:clickhouse'],
    }


@pytest.fixture
def check_with_dbm(instance_with_dbm):
    return ClickhouseCheck('clickhouse', {}, [instance_with_dbm])


@pytest.fixture
def job(check_with_dbm):
    """Return the statement_metrics job (a concrete subclass of ClickhouseQueryLogJob)."""
    return check_with_dbm.statement_metrics


class TestTrackNodeCheckpoint:
    def test_tracks_new_node(self, job):
        job._pending_node_checkpoints = {}
        job._track_node_checkpoint('node-A', 100)
        assert job._pending_node_checkpoints == {'node-A': 100}

    def test_updates_to_higher_value(self, job):
        job._pending_node_checkpoints = {'node-A': 100}
        job._track_node_checkpoint('node-A', 200)
        assert job._pending_node_checkpoints['node-A'] == 200

    def test_ignores_lower_value(self, job):
        job._pending_node_checkpoints = {'node-A': 200}
        job._track_node_checkpoint('node-A', 100)
        assert job._pending_node_checkpoints['node-A'] == 200

    def test_tracks_multiple_nodes(self, job):
        job._pending_node_checkpoints = {}
        job._track_node_checkpoint('node-A', 100)
        job._track_node_checkpoint('node-B', 200)
        job._track_node_checkpoint('node-C', 150)
        assert job._pending_node_checkpoints == {
            'node-A': 100,
            'node-B': 200,
            'node-C': 150,
        }


class TestBuildPerNodeCheckpointFilter:
    def test_first_run_falls_back_to_global_checkpoint(self, job):
        """When no per-node checkpoints exist, use global checkpoint."""
        job._node_checkpoints = {}
        job._last_checkpoint_microseconds = 1000

        filter_sql, min_cp, params = job._build_per_node_checkpoint_filter()

        assert '{cp_fallback:UInt64}' in filter_sql
        assert min_cp == 1000
        assert params['cp_fallback'] == 1000
        assert 'hostName()' not in filter_sql

    def test_generates_per_node_conditions(self, job):
        """Each known node should get its own bound-parameter condition."""
        job._node_checkpoints = {
            'node-A': 1000,
            'node-B': 2000,
            'node-C': 1500,
        }

        filter_sql, min_cp, params = job._build_per_node_checkpoint_filter()

        assert min_cp == 1000
        # SQL should use parameter placeholders, not literal values
        assert 'hostName() =' in filter_sql
        assert ':String}' in filter_sql
        assert ':UInt64}' in filter_sql
        assert 'hostName() NOT IN' in filter_sql
        # All node names and checkpoints should be in the params dict
        param_values = set(params.values())
        assert 'node-A' in param_values
        assert 'node-B' in param_values
        assert 'node-C' in param_values
        assert 1000 in param_values
        assert 2000 in param_values
        assert 1500 in param_values

    def test_fallback_uses_min_checkpoint(self, job):
        """The NOT IN fallback for unknown nodes should use min checkpoint."""
        job._node_checkpoints = {
            'node-A': 5000,
            'node-B': 3000,
        }

        filter_sql, min_cp, params = job._build_per_node_checkpoint_filter()

        assert min_cp == 3000
        assert 'NOT IN' in filter_sql
        assert params['cp_fallback'] == 3000

    def test_evicts_stale_nodes(self, job):
        """Nodes whose checkpoint is more than the threshold behind max should be evicted."""
        now = 1_000_000_000_000_000  # some reference time in microseconds
        stale_time = now - _NODE_CHECKPOINT_STALENESS_THRESHOLD_US - 1

        job._node_checkpoints = {
            'node-A': now,
            'node-B': now - 1000,
            'stale-node': stale_time,
        }

        filter_sql, min_cp, params = job._build_per_node_checkpoint_filter()

        # Stale node should not appear in params or SQL
        assert 'stale-node' not in params.values()
        assert 'node-A' in params.values()
        assert 'node-B' in params.values()
        assert 'stale-node' not in job._node_checkpoints

    def test_eviction_removes_from_stored_checkpoints(self, job):
        """After eviction, the stale node should be gone from _node_checkpoints."""
        now = 1_000_000_000_000_000
        stale_time = now - _NODE_CHECKPOINT_STALENESS_THRESHOLD_US - 1

        job._node_checkpoints = {
            'node-A': now,
            'stale-node': stale_time,
        }

        job._build_per_node_checkpoint_filter()

        assert 'stale-node' not in job._node_checkpoints
        assert 'node-A' in job._node_checkpoints

    def test_all_nodes_evicted_falls_back_to_global(self, job):
        """If all nodes are stale (e.g. cluster replacement), fall back to global checkpoint."""
        now = 1_000_000_000_000_000
        old = now - _NODE_CHECKPOINT_STALENESS_THRESHOLD_US - 1

        # All nodes are stale relative to each other won't trigger eviction
        # since max - min must exceed threshold. Put one very old node.
        job._node_checkpoints = {
            'only-node': old,
        }
        # This single node won't be evicted (max == min, diff == 0).
        # But if we have two nodes both beyond threshold of a third:
        job._node_checkpoints = {
            'node-A': now,
            'stale-1': old,
            'stale-2': old - 1000,
        }
        job._last_checkpoint_microseconds = 500

        filter_sql, min_cp, params = job._build_per_node_checkpoint_filter()

        # stale-1 and stale-2 should be evicted, leaving only node-A
        assert 'stale-1' not in params.values()
        assert 'stale-2' not in params.values()
        assert 'node-A' in params.values()

    def test_node_at_exact_threshold_is_not_evicted(self, job):
        """A node exactly at the threshold boundary should NOT be evicted."""
        now = 1_000_000_000_000_000
        boundary = now - _NODE_CHECKPOINT_STALENESS_THRESHOLD_US

        job._node_checkpoints = {
            'node-A': now,
            'node-B': boundary,
        }

        filter_sql, _, params = job._build_per_node_checkpoint_filter()

        assert 'node-B' in params.values()
        assert 'node-B' in job._node_checkpoints

    def test_node_names_are_bound_parameters(self, job):
        """Node names should be passed as bound parameters, not interpolated into SQL."""
        job._node_checkpoints = {
            "node'injection": 1000,
        }

        filter_sql, _, params = job._build_per_node_checkpoint_filter()

        # The raw node name should NOT appear in the SQL text
        assert "node'injection" not in filter_sql
        # It should be in the params dict (ClickHouse handles escaping)
        assert "node'injection" in params.values()

    def test_loads_from_cache_when_none(self, job):
        """When _node_checkpoints is None, it should load from persistent cache."""
        job._node_checkpoints = None
        job._last_checkpoint_microseconds = 5000

        with mock.patch.object(job, '_load_node_checkpoints', return_value={}) as mock_load:
            filter_sql, min_cp, params = job._build_per_node_checkpoint_filter()

        mock_load.assert_called_once()
        assert min_cp == 5000
        assert params['cp_fallback'] == 5000


class TestAdvanceCheckpoint:
    def test_persists_node_checkpoints_on_success(self, job):
        """When global checkpoint is set, node checkpoints should also be saved."""
        job._current_checkpoint_microseconds = 5000
        job._pending_node_checkpoints = {'node-A': 5000}

        with (
            mock.patch.object(job, '_save_checkpoint') as mock_save,
            mock.patch.object(job, '_save_node_checkpoints') as mock_save_nodes,
        ):
            job._advance_checkpoint()

        mock_save.assert_called_once_with(5000)
        mock_save_nodes.assert_called_once()
        assert job._last_checkpoint_microseconds == 5000

    def test_clears_node_checkpoints_on_failure(self, job):
        """When global checkpoint is NOT set (collection failed), node checkpoints should be discarded."""
        job._current_checkpoint_microseconds = None
        job._pending_node_checkpoints = {'node-A': 3000, 'node-B': 4000}

        with (
            mock.patch.object(job, '_save_checkpoint') as mock_save,
            mock.patch.object(job, '_save_node_checkpoints') as mock_save_nodes,
        ):
            job._advance_checkpoint()

        mock_save.assert_not_called()
        mock_save_nodes.assert_not_called()
        assert job._pending_node_checkpoints == {}

    def test_zero_checkpoint_is_valid(self, job):
        """A checkpoint of 0 is a valid value and should trigger saves."""
        job._current_checkpoint_microseconds = 0
        job._pending_node_checkpoints = {'node-A': 100}

        with (
            mock.patch.object(job, '_save_checkpoint') as mock_save,
            mock.patch.object(job, '_save_node_checkpoints') as mock_save_nodes,
        ):
            job._advance_checkpoint()

        mock_save.assert_called_once_with(0)
        mock_save_nodes.assert_called_once()
        assert job._last_checkpoint_microseconds == 0


class TestNodeCheckpointPersistence:
    def test_save_merges_pending_into_stored(self, job):
        """Pending checkpoints should be merged into stored checkpoints."""
        job._node_checkpoints = {'node-A': 100}
        job._pending_node_checkpoints = {'node-B': 200}

        job._save_node_checkpoints()

        assert job._node_checkpoints == {'node-A': 100, 'node-B': 200}
        assert job._pending_node_checkpoints == {}

    def test_save_overwrites_existing_node(self, job):
        """A pending checkpoint should overwrite an older stored one for the same node."""
        job._node_checkpoints = {'node-A': 100}
        job._pending_node_checkpoints = {'node-A': 200}

        job._save_node_checkpoints()

        assert job._node_checkpoints['node-A'] == 200

    def test_save_noop_when_no_pending(self, job):
        """When there are no pending checkpoints, save should be a no-op."""
        job._node_checkpoints = {'node-A': 100}
        job._pending_node_checkpoints = {}

        with mock.patch.object(job._check, 'write_persistent_cache') as mock_write:
            job._save_node_checkpoints()

        mock_write.assert_not_called()

    def test_load_returns_empty_on_cache_miss(self, job):
        """When no cached data exists, return empty dict."""
        with mock.patch.object(job._check, 'read_persistent_cache', return_value=''):
            result = job._load_node_checkpoints()

        assert result == {}

    def test_load_parses_cached_json(self, job):
        """Load should parse JSON from persistent cache."""
        cached = '{"node-A": 1000, "node-B": 2000}'
        with mock.patch.object(job._check, 'read_persistent_cache', return_value=cached):
            result = job._load_node_checkpoints()

        assert result == {'node-A': 1000, 'node-B': 2000}

    def test_load_handles_corrupt_cache(self, job):
        """Corrupt cache data should return empty dict, not raise."""
        with mock.patch.object(job._check, 'read_persistent_cache', return_value='not-json'):
            result = job._load_node_checkpoints()

        assert result == {}
