# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import heapq
import time
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from typing import Any, Dict, List, NamedTuple, Optional, Set, Tuple, TypedDict, TypeVar


class VerbosityScoreThreshold(NamedTuple):
    """Mapping of verbosity levels to their score thresholds."""

    verbosity_level: str  # The verbosity level name
    score_threshold: int  # The score threshold for this verbosity level (0-100)


class AdaptiveExplainConfig(TypedDict):
    """Configuration for the AdaptiveExplainManager."""

    verbosity_score_thresholds: List[VerbosityScoreThreshold]  # Maps verbosity level to score threshold

    # Optional parameters with their defaults
    min_duration_ms: Optional[int]  # Minimum query duration to consider for adaptive explain (default: 100ms)
    window_size_seconds: Optional[int]  # Size of the rolling window (default: 300s)
    min_queries_for_decision: Optional[int]  # Minimum queries required for statistical decisions (default: 10)
    max_overhead_per_window: Optional[float]  # Maximum overhead budget per window (default: 20.0)


class SlidingWindow:
    """
    Efficient time-based sliding window implementation.

    This class implements a time-based sliding window that efficiently tracks
    items within a specified time window. It supports fast insertion, expiration
    of old items, and provides various statistics about the window contents.

    Time complexities:
    - add: O(log n) for heap operations
    - expire_old_items: O(k log n) where k is the number of expired items
    - count operations: O(1) with cached counters

    Space complexity: O(n) where n is the number of items in the window
    """

    def __init__(self, window_size_seconds: float):
        """Initialize a sliding window with the specified time window size.

        Args:
            window_size_seconds: Size of the time window in seconds
        """
        self.window_size = window_size_seconds
        self.items = deque()  # (timestamp, key, value) - Value can be any data we want to track
        self.key_to_items = defaultdict(list)  # key -> [(timestamp, value_index), ...]
        self.expiration_heap = []  # (timestamp, key) for efficient expiration

        self._total_item_count = 0

        # Track explained queries and their overhead
        self.explained_queries = {}  # {query_key: (timestamp, verbosity_level)}
        self.current_window_overhead = 0.0

    def add(self, timestamp: float, key: str, value: Any) -> None:
        """Add an item to the window.

        Args:
            timestamp: Time when the item was added
            key: Unique identifier for the item
            value: Value associated with the item
        """
        # Add new item to deque
        item_index = len(self.items)
        self.items.append((timestamp, key, value))

        # Track in our key map
        self.key_to_items[key].append((timestamp, item_index))

        # Add to expiration heap - directly use the key as the second element in tuple
        # Since keys are unique identifiers, this is sufficient for consistent ordering
        heapq.heappush(self.expiration_heap, (timestamp, key))

        self._total_item_count += 1

    def add_explained_query(
        self, timestamp: float, key: str, verbosity_level: str, overhead_map: Dict[str, float]
    ) -> float:
        """Track a query that was explained with a specific verbosity level.

        Args:
            timestamp: When the query was explained
            key: Unique identifier for the query
            verbosity_level: The verbosity level used
            overhead_map: Mapping of verbosity levels to their overhead values

        Returns:
            The updated total overhead in the window
        """
        # Get the overhead for this verbosity
        verbosity_overhead = overhead_map.get(verbosity_level, 0.0)

        # If we already explained this query, remove its previous overhead
        if key in self.explained_queries:
            prev_ts, prev_verbosity = self.explained_queries[key]
            prev_overhead = overhead_map.get(prev_verbosity, 0.0)
            self.current_window_overhead -= prev_overhead

        # Store the explained query
        self.explained_queries[key] = (timestamp, verbosity_level)

        # Add the new overhead
        self.current_window_overhead += verbosity_overhead

        return self.current_window_overhead

    def is_already_explained(self, key: str, current_time: float) -> bool:
        """Check if a query was already explained in the current window.

        Args:
            key: The query key to check
            current_time: The current timestamp

        Returns:
            True if the query was already explained in this window, False otherwise
        """
        if key in self.explained_queries:
            timestamp, _ = self.explained_queries[key]
            return timestamp >= current_time - self.window_size
        return False

    def get_current_overhead(self) -> float:
        """Get the current overhead total in the window.

        Returns:
            The total overhead in the current window
        """
        return self.current_window_overhead

    def expire_old_items(self, current_time: float, overhead_map: Dict[str, float] = None) -> List[Tuple[str, Any]]:
        """Remove items older than the window size and return them.

        Args:
            current_time: The current timestamp
            overhead_map: Optional mapping of verbosity levels to overhead values

        Returns:
            List of (key, value) tuples for items that were expired
        """
        window_start = current_time - self.window_size
        expired_items = []
        expired_score_sum = 0

        # Process items from the expiration heap
        while self.expiration_heap and self.expiration_heap[0][0] < window_start:
            # Pop the oldest item
            timestamp, key = heapq.heappop(self.expiration_heap)

            # Check if we have this key and timestamp in our tracking
            if key in self.key_to_items:
                # Find the corresponding item(s) with this timestamp
                key_items = self.key_to_items[key]
                if not key_items:
                    continue

                # Filter to find items with this timestamp
                expired_indices = []
                for i, (ts, idx) in enumerate(key_items):
                    if ts < window_start:
                        # Get the actual value from our items list
                        if idx < len(self.items):
                            _, item_key, item_value = self.items[idx]
                            if item_key == key:  # Double check key matches
                                expired_items.append((key, item_value))

                                # Update score sum if it's a query info
                                if hasattr(item_value, 'score'):
                                    expired_score_sum += item_value.score

                        expired_indices.append(i)

                # Remove expired indices from our tracking (in reverse to preserve indices)
                for i in sorted(expired_indices, reverse=True):
                    key_items.pop(i)

                # If no items left for this key, remove the key
                if not key_items:
                    del self.key_to_items[key]

        self._total_item_count -= len(expired_items)

        # Also expire explained queries
        if overhead_map:
            keys_to_remove = []
            for query_key, (timestamp, verbosity) in list(self.explained_queries.items()):
                if timestamp < window_start:
                    # Remove its overhead contribution
                    verbosity_overhead = overhead_map.get(verbosity, 0.0)
                    self.current_window_overhead -= verbosity_overhead
                    keys_to_remove.append(query_key)

            # Remove expired explained queries
            for key in keys_to_remove:
                del self.explained_queries[key]

        # We don't actually remove from the deque for efficiency, we just stop tracking expired items
        # Periodically clean up the deque if it gets too large
        if len(self.items) > 2 * sum(len(items) for items in self.key_to_items.values()):
            self._cleanup()

        return expired_items

    def _cleanup(self) -> None:
        """Periodically clean up the internal deque to avoid memory growth."""
        # Create a new deque with only the valid items
        new_items = deque()

        # Rebuild our key tracking
        new_key_to_items = defaultdict(list)

        # Copy over valid items
        for key, item_list in self.key_to_items.items():
            for timestamp, old_index in item_list:
                if old_index < len(self.items):
                    # Get the item and add it to our new collection
                    item = self.items[old_index]
                    new_index = len(new_items)
                    new_items.append(item)
                    new_key_to_items[key].append((timestamp, new_index))

        # Replace the old collections
        self.items = new_items
        self.key_to_items = new_key_to_items

        self._total_item_count = sum(len(items) for items in self.key_to_items.values())

        # Note: We don't need to refresh explained_queries during cleanup
        # as they're independently tracked and expired

    def get_keys(self) -> Set[str]:
        """Get the set of unique keys in the current window."""
        return set(self.key_to_items.keys())

    def get_items_for_key(self, key: str) -> List[Tuple[float, Any]]:
        """Get all items for a specific key.

        Args:
            key: The key to look up

        Returns:
            List of (timestamp, value) tuples for the key
        """
        result = []
        if key in self.key_to_items:
            for _, idx in self.key_to_items[key]:
                if idx < len(self.items):
                    item_timestamp, item_key, item_value = self.items[idx]
                    if item_key == key:
                        result.append((item_timestamp, item_value))
        return result

    def get_most_recent_item(self, key: str) -> Optional[Tuple[float, Any]]:
        """Get the most recent item for a key.

        Args:
            key: The key to look up

        Returns:
            (timestamp, value) tuple for the most recent item, or None if not found
        """
        items = self.get_items_for_key(key)
        if not items:
            return None
        return max(items, key=lambda x: x[0])

    def count_items(self) -> int:
        """Count the total number of valid items in the window in O(1) time."""
        return self._total_item_count

    def get_unique_keys_count(self) -> int:
        """Count the number of unique keys in the window in O(1) time."""
        return len(self.key_to_items)


class QueryScorer(ABC):
    """Interface for scoring database queries and providing query identification.

    This interface handles query scoring, query key generation, and duration extraction,
    which are typically specific to a particular DBMS implementation.
    """

    @abstractmethod
    def score(self, query: Dict[str, Any]) -> Tuple[int, str]:
        """Score a query based on its performance characteristics and generate a unique key.

        Args:
            query: Database query data directly from the DBMS,
            e.g. a Postgres query sampled from pg_stat_activity
            a MySQL query sampled from information_schema.events_statements_current
            or a MongoDB query sampled from the $currentOp pipeline

        Returns:
            (score, query_key): Tuple containing:
                - score: Integer score from 0-100
                - query_key: String unique identifier for this query
        """
        pass

    @abstractmethod
    def get_duration_ms(self, query: Dict[str, Any]) -> float:
        """Extract query duration in milliseconds.

        Args:
            query: Query data from the DBMS

        Returns:
            duration_ms: Duration in milliseconds
        """
        pass


class ExplainVerbosityProvider:
    """Provides verbosity level information and configuration.

    This class handles providing verbosity levels and their related information:
    1. Defining available verbosity levels with their overhead values
    2. Configuring score thresholds for each verbosity level

    Score Scale:
    - Query scores range from 0 to 100, with higher scores indicating queries that are
      more important to explain with higher verbosity.

    Overhead Scale:
    - Overhead values range from 0.0 to 1.0, representing relative cost/impact
      of using a particular verbosity level.
    - 0.0 represents minimum overhead (typically the default verbosity level)
    - 1.0 represents maximum overhead (the most expensive verbosity level)

    Implementations should override verbosity_levels property to provide database-specific levels.
    """

    def __init__(self, verbosity_levels: List[Tuple[str, float]], default_verbosity: Optional[str] = None):
        """Initialize the verbosity provider with specific levels.

        Args:
            verbosity_levels: List of (name, overhead) tuples, sorted by overhead (ascending)
            default_verbosity: Optional default verbosity level name (defaults to lowest overhead)
        """
        self.verbosity_levels = verbosity_levels
        self.default_verbosity = default_verbosity or verbosity_levels[0][0]
        self.verbosity_overhead_map = dict(verbosity_levels)

    def configure_verbosity_thresholds(self, custom_thresholds: List[VerbosityScoreThreshold] = None) -> Dict[str, int]:
        """Configure score thresholds for each verbosity level.

        This method creates default thresholds that correlate with the overhead values
        of each verbosity level. Higher overhead verbosity levels require higher score thresholds.

        If custom thresholds are provided, they override the defaults.

        Args:
            custom_thresholds: List of (name, threshold) tuples, where name is the verbosity level name
            and threshold is the minimum score threshold.
            e.g. [('normal', 20), ('detailed', 80)]

        Returns:
            thresholds: Dict mapping verbosity level to minimum score threshold
        """
        # Create default thresholds correlated with overhead
        thresholds = {}

        # Special case: If only one level, threshold is 0
        if len(self.verbosity_levels) == 1:
            if self.verbosity_levels:
                thresholds[self.verbosity_levels[0][0]] = 0
            return thresholds

        # Get min and max overhead for normalization
        min_overhead = self.verbosity_levels[0][1]  # Assuming verbosity_levels is sorted
        max_overhead = self.verbosity_levels[-1][1]
        overhead_range = max_overhead - min_overhead

        # Set thresholds proportional to overhead
        # The lowest overhead level gets threshold 0, highest gets 100
        for level_name, overhead in self.verbosity_levels:
            # Normalize overhead to 0-100 range
            if level_name == self.verbosity_levels[0][0]:
                # Always set lowest overhead level threshold to 0
                thresholds[level_name] = 0
            else:
                # Scale other thresholds based on their relative overhead
                normalized_overhead = (overhead - min_overhead) / overhead_range
                # Min score threshold is 20 to ensure separation between levels
                thresholds[level_name] = max(20, int(normalized_overhead * 100))

        # Override with custom thresholds if provided
        if custom_thresholds:
            for name, threshold in custom_thresholds:
                thresholds[name] = threshold

        return thresholds


T = TypeVar('T')


class AdaptiveExplainManager:
    """
    Universal adaptive explain verbosity manager with multi-level verbosity support.

    This class provides a flexible and configurable mechanism for managing the verbosity of
    database query explanations. It supports multiple verbosity levels and allows for dynamic
    selection of the most appropriate verbosity level based on query performance and overhead.

    The manager uses a rolling window to track query performance and overhead, and dynamically
    selects the verbosity level that balances query performance and overhead constraints.
    """

    def __init__(
        self,
        config: AdaptiveExplainConfig,
        query_scorer: QueryScorer,
        verbosity_provider: ExplainVerbosityProvider,
    ):
        """Initialize the adaptive explain manager.

        Args:
            config: Configuration parameters (AdaptiveExplainConfig)
            query_scorer: DBMS-specific query scorer implementation
            verbosity_provider: Provider of verbosity level information
        """
        # Core configuration
        self.min_duration_ms = config.get('min_duration_ms', 100)

        # Rolling window configuration
        self.window_size_seconds = config.get('window_size_seconds', 300)
        self.min_queries_for_decision = config.get('min_queries_for_decision', 10)
        self.max_overhead_per_window = config.get('max_overhead_per_window', 20.0)

        # Inject dependencies
        self.query_scorer = query_scorer
        self.verbosity_provider = verbosity_provider

        # Get verbosity configuration from the provider
        self.verbosity_levels = self.verbosity_provider.verbosity_levels
        self.default_verbosity = self.verbosity_provider.default_verbosity

        # Configure verbosity thresholds and pre-sort them for efficient lookup
        self.verbosity_score_thresholds = self.verbosity_provider.configure_verbosity_thresholds(
            config.get('verbosity_score_thresholds', [])
        )

        self.sorted_verbosity_thresholds = sorted(
            self.verbosity_score_thresholds.items(),
            key=lambda x: x[1],
            reverse=True,
        )

        self.verbosity_overhead_map = self.verbosity_provider.verbosity_overhead_map

        # Initialize sliding window for query tracking and overhead management
        self.query_window = SlidingWindow(self.window_size_seconds)

    def get_verbosity_for_query(self, query: Dict[str, Any], timestamp: float = None) -> str:
        """Determine the appropriate verbosity level for a query.

        Args:
            query: DBMS-specific query data
            timestamp: Query timestamp (or current time if None)

        Returns:
            verbosity_level: The selected verbosity level
        """
        if timestamp is None:
            timestamp = time.time()

        # Score the query and get its unique key directly from the scorer
        score, query_key = self.query_scorer.score(query)

        # Expire old items first for accurate window state
        self.query_window.expire_old_items(timestamp, self.verbosity_overhead_map)

        # Add the new query to the window
        self.query_window.add(timestamp, query_key, score)

        # Select the appropriate verbosity level
        selected_verbosity = self._select_verbosity_level(
            score=score,
            duration_ms=self.query_scorer.get_duration_ms(query),
            already_explained=self.query_window.is_already_explained(query_key, timestamp),
            current_overhead=self.query_window.get_current_overhead(),
        )

        # If a non-default verbosity was selected, update tracking with the window
        if selected_verbosity != self.default_verbosity:
            self.query_window.add_explained_query(timestamp, query_key, selected_verbosity, self.verbosity_overhead_map)

        return selected_verbosity

    def _select_verbosity_level(
        self, score: int, duration_ms: float, already_explained: bool = False, current_overhead: float = 0.0
    ) -> str:
        """Select the appropriate verbosity level based on score and constraints.

        Args:
            score: Query score (0-100)
            duration_ms: Query duration in milliseconds
            already_explained: Whether this query was already explained
            current_overhead: Current overhead in the window

        Returns:
            verbosity_level: Selected verbosity level
        """
        # Check minimum duration requirement
        if duration_ms < self.min_duration_ms:
            return self.default_verbosity

        # Check if already explained
        if already_explained:
            return self.default_verbosity

        # Use pre-sorted verbosity thresholds to find the highest eligible level
        selected_verbosity = self.default_verbosity
        for verbosity_name, threshold in self.sorted_verbosity_thresholds:
            if score >= threshold:
                # Found a matching verbosity level, now check overhead constraints
                verbosity_overhead = self.verbosity_overhead_map.get(verbosity_name, 0.0)

                # Check if adding this overhead would exceed our window limit
                if current_overhead + verbosity_overhead <= self.max_overhead_per_window:
                    selected_verbosity = verbosity_name
                    break

        return selected_verbosity
