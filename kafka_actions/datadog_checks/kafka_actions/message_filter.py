# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Message filtering with jq-style capabilities."""

import json
import re
from typing import Any


class MessageFilter:
    """Filters Kafka messages based on jq-style filter expressions."""

    OPERATORS = {
        'eq': lambda a, b: a == b,
        'ne': lambda a, b: a != b,
        'gt': lambda a, b: a > b,
        'lt': lambda a, b: a < b,
        'gte': lambda a, b: a >= b,
        'lte': lambda a, b: a <= b,
        'contains': lambda a, b: b in str(a),
        'regex': lambda a, b: re.search(b, str(a)) is not None,
        'exists': lambda a, b: a is not None,
    }

    def __init__(self, filters: list[dict[str, Any]], log):
        """Initialize message filter.

        Args:
            filters: List of filter dictionaries with 'field', 'operator', 'value'
            log: Logger instance
        """
        self.filters = filters or []
        self.log = log

    def matches(self, message: Any) -> bool:
        """Check if a message matches all filters.

        Args:
            message: Kafka message object

        Returns:
            True if message matches all filters (AND logic)
        """
        if not self.filters:
            return True  # No filters means match all

        for filter_def in self.filters:
            if not self._match_single_filter(message, filter_def):
                return False

        return True

    def _match_single_filter(self, message: Any, filter_def: dict[str, Any]) -> bool:
        """Check if message matches a single filter.

        Args:
            message: Kafka message object
            filter_def: Filter definition dict

        Returns:
            True if matches
        """
        field = filter_def.get('field')
        operator = filter_def.get('operator')
        expected_value = filter_def.get('value')

        if not field or not operator:
            self.log.warning("Invalid filter definition: %s", filter_def)
            return True  # Skip invalid filters

        # Get field value from message
        field_value = self._get_field_value(message, field)

        # Apply operator
        if operator not in self.OPERATORS:
            self.log.warning("Unknown operator: %s", operator)
            return True

        try:
            # Type conversion for comparison
            if operator in ['gt', 'lt', 'gte', 'lte']:
                # Numeric comparison
                field_value = float(field_value) if field_value is not None else None
                expected_value = float(expected_value)
            elif operator == 'exists':
                # Exists just checks if field_value is not None
                return field_value is not None

            return self.OPERATORS[operator](field_value, expected_value)

        except (ValueError, TypeError) as e:
            self.log.debug("Filter comparison failed for field '%s': %s", field, e)
            return False

    def _get_field_value(self, message: Any, field_path: str) -> Any:
        """Extract field value from message using dot notation.

        Args:
            message: Kafka message object
            field_path: Field path like 'value.user_id', 'key', 'timestamp', 'offset'

        Returns:
            Field value or None if not found
        """
        # Special fields from Kafka message object
        if field_path == 'offset':
            return message.offset()
        elif field_path == 'timestamp':
            ts_type, ts_value = message.timestamp()
            return ts_value
        elif field_path == 'partition':
            return message.partition()
        elif field_path == 'topic':
            return message.topic()

        # Parse key or value
        if field_path.startswith('key'):
            data = self._parse_message_part(message.key())
            path_parts = field_path.split('.')[1:]  # Remove 'key' prefix
        elif field_path.startswith('value'):
            data = self._parse_message_part(message.value())
            path_parts = field_path.split('.')[1:]  # Remove 'value' prefix
        elif field_path == 'headers':
            return dict(message.headers() or [])
        else:
            # Try to parse as value field
            data = self._parse_message_part(message.value())
            path_parts = field_path.split('.')

        # Navigate through nested structure
        current = data
        for part in path_parts:
            if current is None:
                return None

            if isinstance(current, dict):
                current = current.get(part)
            elif isinstance(current, list):
                try:
                    index = int(part)
                    current = current[index]
                except (ValueError, IndexError):
                    return None
            else:
                return None

        return current

    def _parse_message_part(self, data: bytes | str | None) -> Any:
        """Parse message key or value (try JSON first, then string).

        Args:
            data: Raw message data

        Returns:
            Parsed data structure or original data
        """
        if data is None:
            return None

        if isinstance(data, bytes):
            try:
                data = data.decode('utf-8')
            except UnicodeDecodeError:
                return data  # Return bytes if not UTF-8

        # Try to parse as JSON
        try:
            return json.loads(data)
        except (json.JSONDecodeError, TypeError):
            return data  # Return as string if not JSON
