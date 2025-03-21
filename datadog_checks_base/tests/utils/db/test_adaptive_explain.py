# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import time

import pytest

from datadog_checks.base.utils.db.adaptive_explain import (
    AdaptiveExplainConfig,
    AdaptiveExplainManager,
    ExplainVerbosityProvider,
    QueryScorer,
    SlidingWindow,
)


class MockQueryScorer(QueryScorer):
    def __init__(self, custom_scores=None):
        """Initialize with optional custom score overrides.

        Args:
            custom_scores: Optional dict mapping query_keys to predetermined scores
        """
        self.custom_scores = custom_scores or {}

    def score(self, query):
        # If this query has a custom score defined, use it
        query_key = query.get('signature', 'default_signature')
        if query_key in self.custom_scores:
            return self.custom_scores[query_key], query_key

        # Otherwise use the score from the query or calculate it
        score = query.get('score', 0)
        duration_ms = self.get_duration_ms(query)
        if duration_ms > 1000:
            score += 10
        return score, query_key

    def get_duration_ms(self, query):
        return query.get('duration_ms', 0)


class MockVerbosityProvider(ExplainVerbosityProvider):
    """Mock verbosity provider for testing."""

    def __init__(self):
        """Initialize with test verbosity levels."""
        super().__init__(
            verbosity_levels=[
                ('low', 0.0),
                ('medium', 0.5),
                ('high', 1.0),
            ]
        )


@pytest.fixture
def adaptive_explain_manager():
    # Define configuration using TypedDict
    config: AdaptiveExplainConfig = {
        'min_duration_ms': 100,
        'window_size_seconds': 300,
        'verbosity_score_thresholds': [
            ('low', 0),
            ('medium', 60),
            ('high', 80),
        ],
        'max_overhead_per_window': 20.0,
    }

    return AdaptiveExplainManager(
        config,
        MockQueryScorer(),
        MockVerbosityProvider(),
    )


@pytest.fixture
def sliding_window():
    """Create a test sliding window"""
    return SlidingWindow(window_size_seconds=0.5)


class TestSlidingWindow:
    """Tests for the optimized SlidingWindow implementation"""

    def test_add_and_retrieve(self, sliding_window):
        """Test adding items and retrieving them"""
        now = time.time()
        sliding_window.add(now, "key1", "value1")
        sliding_window.add(now, "key2", "value2")
        sliding_window.add(now, "key1", "value3")  # Add duplicate key

        # Check that we have the expected keys
        assert sliding_window.get_keys() == {"key1", "key2"}

        # Check item counts
        assert sliding_window.count_items() == 3
        assert sliding_window.get_unique_keys_count() == 2

        # Check retrieving items
        key1_items = sliding_window.get_items_for_key("key1")
        assert len(key1_items) == 2
        assert any(value == "value1" for _, value in key1_items)
        assert any(value == "value3" for _, value in key1_items)

        # Check most recent item
        most_recent = sliding_window.get_most_recent_item("key1")
        assert most_recent is not None
        assert most_recent[1] in ["value1", "value3"]

    def test_expiration(self, sliding_window):
        """Test that items expire correctly from the window"""
        now = time.time()

        # Add items with different timestamps
        sliding_window.add(now - 1.0, "old", "old_value")  # This should expire
        sliding_window.add(now - 0.25, "recent", "recent_value")  # This should stay
        sliding_window.add(now, "new", "new_value")  # This should stay

        # Initial state
        assert sliding_window.count_items() == 3
        assert sliding_window.get_unique_keys_count() == 3

        # Expire old items (window size is 0.5 seconds)
        expired = sliding_window.expire_old_items(now)

        # Check that "old" was expired
        assert len(expired) == 1
        assert expired[0][0] == "old"
        assert expired[0][1] == "old_value"

        # Check that the other items remain
        assert sliding_window.get_unique_keys_count() == 2
        assert "old" not in sliding_window.get_keys()
        assert "recent" in sliding_window.get_keys()
        assert "new" in sliding_window.get_keys()

    def test_score_tracking(self, sliding_window):
        """Test that scores are tracked correctly"""
        now = time.time()

        # Add items with scores
        sliding_window.add(now, "q1", 10)
        sliding_window.add(now, "q2", 20)
        sliding_window.add(now, "q3", 30)

        # Expire an item
        sliding_window.window_size = 0.1
        time.sleep(0.2)
        expired = sliding_window.expire_old_items(time.time())

        assert len(expired) == 3

        # Check counter resets after cleanup
        sliding_window._cleanup()
        assert sliding_window.count_items() == len(list(sliding_window.key_to_items.values()))


class TestVerbosityProvider:
    """Tests for the ExplainVerbosityProvider functionality"""

    def test_initialization_requirements(self):
        """Test that the class requires valid verbosity levels for initialization"""
        # Creating a provider without verbosity levels should raise TypeError
        with pytest.raises(TypeError):
            ExplainVerbosityProvider()

        # Creating a provider with empty verbosity levels should work but default_verbosity would fail
        with pytest.raises(IndexError):
            ExplainVerbosityProvider([])

    def test_property_access(self):
        """Test property-based access to verbosity provider functionality"""
        # Use our mock provider instead of the base class
        provider = MockVerbosityProvider()

        # Check properties access
        levels = provider.verbosity_levels
        assert len(levels) == 3
        assert levels[0][0] == 'low'

        # Verify levels are already sorted by overhead
        overhead_values = [level[1] for level in levels]
        assert overhead_values == [0.0, 0.5, 1.0]

        # Check default verbosity property
        assert provider.default_verbosity == 'low'

        # Check overhead map property
        overhead_map = provider.verbosity_overhead_map
        assert overhead_map['low'] == 0.0
        assert overhead_map['medium'] == 0.5
        assert overhead_map['high'] == 1.0

    def test_threshold_configuration(self):
        """Test threshold configuration with the provider"""
        provider = MockVerbosityProvider()

        # Check threshold configuration
        thresholds = provider.configure_verbosity_thresholds({})

        # The lowest overhead level should always have threshold 0
        assert thresholds['low'] == 0

        # Medium and high thresholds should be scaled based on overhead
        # With overheads [0.0, 0.5, 1.0], medium should be around 50 and high around 100
        assert 40 <= thresholds['medium'] <= 60
        assert 90 <= thresholds['high'] <= 100

        # Higher overhead levels should have higher thresholds
        assert thresholds['low'] < thresholds['medium'] < thresholds['high']

        # Check custom threshold configuration
        custom = provider.configure_verbosity_thresholds([('low', 10), ('medium', 70), ('high', 90)])
        assert custom['low'] == 10  # Custom value
        assert custom['medium'] == 70  # Custom value
        assert custom['high'] == 90  # Custom value

        # Test with a provider that has different overhead values
        custom_provider = ExplainVerbosityProvider([('minimal', 0.0), ('basic', 0.2), ('detailed', 0.8), ('full', 1.0)])

        custom_thresholds = custom_provider.configure_verbosity_thresholds({})
        assert custom_thresholds['minimal'] == 0

        # Check that thresholds follow overhead proportions
        # 'basic' overhead is 0.2, which is 20% of the way from minimal to full
        # 'detailed' overhead is 0.8, which is 80% of the way from minimal to full
        basic_normalized = 0.2 / 1.0  # = 0.2
        detailed_normalized = 0.8 / 1.0  # = 0.8

        assert abs(custom_thresholds['basic'] - int(basic_normalized * 100)) <= 20
        assert abs(custom_thresholds['detailed'] - int(detailed_normalized * 100)) <= 20

        # Check that thresholds increase with overhead
        assert (
            custom_thresholds['minimal']
            < custom_thresholds['basic']
            < custom_thresholds['detailed']
            < custom_thresholds['full']
        )


class TestAdaptiveExplainManager:
    def test_initialization(self, adaptive_explain_manager):
        """Test that the manager initializes with the correct configuration"""
        assert adaptive_explain_manager.min_duration_ms == 100
        assert adaptive_explain_manager.window_size_seconds == 300
        assert adaptive_explain_manager.sorted_verbosity_thresholds == [('high', 80), ('medium', 60), ('low', 0)]
        assert adaptive_explain_manager.default_verbosity == 'low'
        assert isinstance(adaptive_explain_manager.query_window, SlidingWindow)

    def test_verbosity_selection_based_on_score(self, adaptive_explain_manager):
        """Test that the manager selects verbosity based on query score"""
        # Low score query
        query_low = {
            'signature': 'q1',
            'score': 50,
            'duration_ms': 200,
        }
        verbosity_low = adaptive_explain_manager.get_verbosity_for_query(query_low)
        assert verbosity_low == 'low'

        # Medium score query
        query_medium = {
            'signature': 'q2',
            'score': 65,
            'duration_ms': 200,
        }
        verbosity_medium = adaptive_explain_manager.get_verbosity_for_query(query_medium)
        assert verbosity_medium == 'medium'

        # High score query
        query_high = {
            'signature': 'q3',
            'score': 85,
            'duration_ms': 200,
        }
        verbosity_high = adaptive_explain_manager.get_verbosity_for_query(query_high)
        assert verbosity_high == 'high'

    def test_duration_threshold(self, adaptive_explain_manager):
        """Test that queries below the minimum duration always get low verbosity"""
        # High score but low duration
        query = {
            'signature': 'q4',
            'score': 90,
            'duration_ms': 50,  # Below the threshold of 100
        }
        verbosity = adaptive_explain_manager.get_verbosity_for_query(query)
        assert verbosity == 'low'

    def test_select_verbosity_level(self, adaptive_explain_manager):
        """Test the verbosity selection logic directly"""
        # Test with various scenarios

        # High score, above duration threshold, not explained before
        verbosity = adaptive_explain_manager._select_verbosity_level(score=95, duration_ms=200, already_explained=False)
        assert verbosity == 'high'  # Should get high verbosity

        # Medium score, above duration threshold, not explained before
        verbosity = adaptive_explain_manager._select_verbosity_level(score=65, duration_ms=200, already_explained=False)
        assert verbosity == 'medium'  # Should get medium verbosity

        # High score, below duration threshold
        verbosity = adaptive_explain_manager._select_verbosity_level(
            score=95, duration_ms=50, already_explained=False  # Below threshold
        )
        assert verbosity == 'low'  # Should get low verbosity due to duration

        # High score, above duration threshold, but already explained
        verbosity = adaptive_explain_manager._select_verbosity_level(score=95, duration_ms=200, already_explained=True)
        assert verbosity == 'low'  # Should get low verbosity due to already explained

    def test_query_window_tracking(self, adaptive_explain_manager):
        """Test that queries are tracked in the rolling window"""
        # Add a few queries
        queries = [{'signature': f'q{i}', 'score': 60 + i * 10, 'duration_ms': 200} for i in range(5)]

        for q in queries:
            adaptive_explain_manager.get_verbosity_for_query(q)

        # Check that queries were added to the window
        # Rather than directly accessing the window, check using metrics
        assert adaptive_explain_manager.query_window.count_items() >= 5

        # Check for unique queries
        assert adaptive_explain_manager.query_window.get_unique_keys_count() >= 5

    def test_window_expiration(self, adaptive_explain_manager):
        """Test that queries expire from the window after the window size"""
        # Set a very small window size for testing
        adaptive_explain_manager.window_size_seconds = 0.1
        adaptive_explain_manager.query_window.window_size = 0.1

        # Add a query
        query = {
            'signature': 'test_q',
            'score': 85,
            'duration_ms': 200,
        }

        # Add with a specific timestamp
        now = time.time()
        adaptive_explain_manager.get_verbosity_for_query(query, timestamp=now)

        # Verify it's in the window via counters
        total_before = adaptive_explain_manager.query_window.count_items()
        assert total_before >= 1

        # Add another query after the window expires
        time.sleep(0.2)  # Wait longer than the window size

        # Add a new query to trigger expiration
        adaptive_explain_manager.get_verbosity_for_query(
            {
                'signature': 'new_q',
                'score': 70,
                'duration_ms': 200,
            }
        )

        # Force expiration explicitly
        adaptive_explain_manager.query_window.expire_old_items(time.time())

        # Check metrics again to confirm one was expired
        total_after = adaptive_explain_manager.query_window.count_items()
        assert total_after < total_before + 1

    def test_overhead_tracking(self, adaptive_explain_manager):
        """Test that overhead is tracked and managed correctly"""
        # Configure a smaller overhead budget for testing
        adaptive_explain_manager.max_overhead_per_window = 1.5

        # First query - high score, should get high verbosity
        query1 = {
            'signature': 'overhead_q1',
            'score': 90,
            'duration_ms': 200,
        }
        verbosity1 = adaptive_explain_manager.get_verbosity_for_query(query1)
        assert verbosity1 == 'high'
        assert adaptive_explain_manager.query_window.get_current_overhead() == 1.0

        # Second query - high score, but only medium verbosity due to overhead
        query2 = {
            'signature': 'overhead_q2',
            'score': 85,
            'duration_ms': 200,
        }
        verbosity2 = adaptive_explain_manager.get_verbosity_for_query(query2)
        assert verbosity2 == 'medium'
        assert adaptive_explain_manager.query_window.get_current_overhead() == 1.5

        # Third query - high score, but should get low verbosity due to overhead
        query3 = {
            'signature': 'overhead_q3',
            'score': 85,
            'duration_ms': 200,
        }
        verbosity3 = adaptive_explain_manager.get_verbosity_for_query(query3)
        assert verbosity3 == 'low'
        assert adaptive_explain_manager.query_window.get_current_overhead() == 1.5

    def test_comprehensive_query_sequence(self):
        """Test a comprehensive sequence of queries with different scores and behaviors.

        This test simulates a realistic scenario with:
        1. A sequence of queries with various scores
        2. Window expiration over time
        3. Overhead budget management
        4. Query priority based on scores
        """
        # Create a custom query scorer with predetermined scores
        custom_scorer = MockQueryScorer()

        # Create a verbosity provider with custom verbosity levels and overhead values
        verbosity_provider = ExplainVerbosityProvider(
            verbosity_levels=[
                ('low', 0.0),  # No overhead
                ('medium', 0.5),  # Medium overhead
                ('high', 1.0),  # High overhead
            ]
        )

        # Create a configuration with a small window size for easier testing
        # and a limited overhead budget
        config: AdaptiveExplainConfig = {
            'min_duration_ms': 100,
            'window_size_seconds': 1.0,  # 1 second window for faster testing
            'verbosity_score_thresholds': [
                ('low', 0),  # Always available
                ('medium', 50),  # Medium score threshold
                ('high', 80),  # High score threshold
            ],
            'max_overhead_per_window': 3.0,  # Allow 3 high-verbosity queries or 6 medium ones
        }

        # Create the manager
        manager = AdaptiveExplainManager(
            config,
            custom_scorer,
            verbosity_provider,
        )

        # Start with a specific timestamp for controlled testing
        start_time = time.time()
        current_time = start_time

        # Helper function to process a query and validate results
        def process_query(signature, score, duration_ms, expected_verbosity, timestamp):
            # Create the query with the given parameters
            query = {
                'signature': signature,
                'score': score,
                'duration_ms': duration_ms,
            }

            # Get the verbosity level for this query
            verbosity = manager.get_verbosity_for_query(query, timestamp=timestamp)

            # Check that the verbosity matches what we expect
            assert (
                verbosity == expected_verbosity
            ), f"Expected {expected_verbosity} for query {signature} with score {score}, got {verbosity}"

            return verbosity, manager.query_window.get_current_overhead()

        # 1. Process initial queries with different scores
        # First query: Score 85, should get high verbosity
        _, overhead = process_query("query1", 85, 200, "high", current_time)
        # Overhead should be 1.0 after first high query
        assert overhead == 1.0

        # Second query: Score 60, should get medium verbosity
        _, overhead = process_query("query2", 60, 200, "medium", current_time)
        # Overhead should be 1.5 after high + medium
        assert overhead == 1.5

        # Third query: Score 40, should get low verbosity (below medium threshold)
        _, overhead = process_query("query3", 40, 200, "low", current_time)
        # Low verbosity adds no overhead
        assert overhead == 1.5

        # 2. Test overhead budget limitation
        # A series of high-scoring queries that should hit the overhead cap

        # Fourth query: Score 90, should get high verbosity
        _, overhead = process_query("query4", 90, 200, "high", current_time)
        # Overhead now 2.5 (previous 1.5 + 1.0)
        assert overhead == 2.5

        # Fifth query: Score 85, should be limited to medium verbosity due to overhead
        _, overhead = process_query("query5", 85, 200, "medium", current_time)
        # Overhead now 3.0 (previous 2.5 + 0.5)
        assert overhead == 3.0

        # Sixth query: Score 95, but overhead is now 3.0, so there's no room left
        # This should get low verbosity despite high score
        _, overhead = process_query("query6", 95, 200, "low", current_time)
        # Overhead remains 3.0
        assert overhead == 3.0

        # Seventh query: Score 99, but overhead is maxed out at 3.0
        # Should be limited to low verbosity
        _, overhead = process_query("query7", 99, 200, "low", current_time)
        # Overhead still 3.0
        assert overhead == 3.0

        # 3. Test window expiration
        # Advance time beyond the window size
        current_time += 1.1  # Just beyond our 1.0s window

        # Eighth query after expiration: Score 85, should get high verbosity again
        # All previous queries have expired, so overhead should be reset
        _, overhead = process_query("query8", 85, 200, "high", current_time)
        # New overhead should be 1.0
        assert overhead == 1.0

        # 4. Test duration threshold
        # Query with high score but below duration threshold
        _, overhead = process_query("query9", 95, 50, "low", current_time)
        # Low verbosity due to duration threshold, overhead unchanged
        assert overhead == 1.0

        # 5. Test the same query twice scenario
        # Same query signature, should get low verbosity the second time
        _, overhead = process_query("query8", 85, 200, "low", current_time)
        # Already explained, so low verbosity, overhead unchanged
        assert overhead == 1.0

        # 6. Add more queries to reach the overhead cap again
        _, overhead = process_query("query10", 85, 200, "high", current_time)
        # High verbosity, overhead now 2.0
        assert overhead == 2.0

        # 7. Test expiration again, but with a more gradual approach
        # Move time forward incrementally to expire queries one by one
        for i in range(3):
            current_time += 0.22  # Move forward in smaller increments

            # Get current overhead before adding a new query
            current_overhead = manager.query_window.get_current_overhead()

            # Process a query after partial expiration
            query_num = 11 + i

            # Based on current overhead, determine expected verbosity
            if current_overhead <= 2.0:
                expected_verbosity = "high"
            elif current_overhead > 2.0 and current_overhead <= 2.5:
                expected_verbosity = "medium"
            else:
                expected_verbosity = "low"
            _, new_overhead = process_query(f"query{query_num}", 85, 200, expected_verbosity, current_time)

            # Verify overhead after query
            if expected_verbosity in ("high", "medium"):
                assert new_overhead <= 3.0, f"Overhead {new_overhead} exceeds maximum 3.0"

        # Final validation
        # Verify the count of queries in the window
        query_count = manager.query_window.count_items()
        assert query_count <= 7, f"Expected at most 7 queries in window, got {query_count}"
