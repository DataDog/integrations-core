# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging

import pytest

from datadog_checks.dev.testing import requires_windows

from .utils import GLOBAL_TAGS, get_check

pytestmark = [requires_windows]


class TestUsePerInstanceCollection:
    """Tests for the use_per_instance_collection option."""

    def test_not_boolean(self, dd_run_check, mock_performance_objects):
        """Test that use_per_instance_collection must be a boolean."""
        mock_performance_objects({'Foo': (['instance1'], {'Bar': [9000]})})
        check = get_check(
            {
                'metrics': {
                    'Foo': {
                        'name': 'foo',
                        'use_per_instance_collection': 'not_a_boolean',
                        'counters': [{'Bar': {'name': 'bar'}}],
                    }
                }
            }
        )

        with pytest.raises(
            Exception,
            match='^Option `use_per_instance_collection` for performance object `Foo` must be a boolean$',
        ):
            dd_run_check(check, extract_message=True)

    def test_single_instance_warning(self, dd_run_check, mock_performance_objects, caplog):
        """Test that a warning is logged when use_per_instance_collection is set on single-instance counters."""
        mock_performance_objects({'Foo': ([None], {'Bar': [9000]})})
        check = get_check(
            {
                'metrics': {
                    'Foo': {
                        'name': 'foo',
                        'use_per_instance_collection': True,
                        'counters': [{'Bar': {'name': 'bar'}}],
                    }
                }
            }
        )
        dd_run_check(check)

        expected_message = (
            'Ignoring option `use_per_instance_collection` for performance object `Foo` '
            'since it contains single instance counters'
        )
        for _, level, message in caplog.record_tuples:
            if level == logging.WARNING and message == expected_message:
                break
        else:
            raise AssertionError('Expected WARNING log with message `{}`'.format(expected_message))

    def test_multi_instance_collection(self, aggregator, dd_run_check, mock_performance_objects):
        """Test that metrics are collected correctly with use_per_instance_collection enabled."""
        mock_performance_objects({'Foo': (['instance1', 'instance2'], {'Bar': [100, 200]})})
        check = get_check(
            {
                'metrics': {
                    'Foo': {
                        'name': 'foo',
                        'use_per_instance_collection': True,
                        'counters': [{'Bar': {'name': 'bar'}}],
                    }
                }
            }
        )
        dd_run_check(check)

        tags_instance1 = ['instance:instance1'] + list(GLOBAL_TAGS)
        tags_instance2 = ['instance:instance2'] + list(GLOBAL_TAGS)

        aggregator.assert_metric('test.foo.bar', 100, tags=tags_instance1)
        aggregator.assert_metric('test.foo.bar', 200, tags=tags_instance2)
        aggregator.assert_all_metrics_covered()

    def test_multi_instance_collection_disabled_by_default(self, aggregator, dd_run_check, mock_performance_objects):
        """Test that use_per_instance_collection defaults to False (standard bulk collection)."""
        mock_performance_objects({'Foo': (['instance1', 'instance2'], {'Bar': [100, 200]})})
        check = get_check(
            {
                'metrics': {
                    'Foo': {
                        'name': 'foo',
                        # use_per_instance_collection not set, should default to False
                        'counters': [{'Bar': {'name': 'bar'}}],
                    }
                }
            }
        )
        dd_run_check(check)

        tags_instance1 = ['instance:instance1'] + list(GLOBAL_TAGS)
        tags_instance2 = ['instance:instance2'] + list(GLOBAL_TAGS)

        # Metrics should still be collected via standard bulk method
        aggregator.assert_metric('test.foo.bar', 100, tags=tags_instance1)
        aggregator.assert_metric('test.foo.bar', 200, tags=tags_instance2)
        aggregator.assert_all_metrics_covered()

    def test_per_instance_with_filters(self, aggregator, dd_run_check, mock_performance_objects):
        """Test that use_per_instance_collection works with include/exclude filters."""
        mock_performance_objects({'Foo': (['instance1', 'instance2', 'instance3'], {'Bar': [100, 200, 300]})})
        check = get_check(
            {
                'metrics': {
                    'Foo': {
                        'name': 'foo',
                        'use_per_instance_collection': True,
                        'include': ['instance1', 'instance2'],
                        'counters': [{'Bar': {'name': 'bar'}}],
                    }
                }
            }
        )
        dd_run_check(check)

        tags_instance1 = ['instance:instance1'] + list(GLOBAL_TAGS)
        tags_instance2 = ['instance:instance2'] + list(GLOBAL_TAGS)

        aggregator.assert_metric('test.foo.bar', 100, tags=tags_instance1)
        aggregator.assert_metric('test.foo.bar', 200, tags=tags_instance2)
        # instance3 should be excluded
        aggregator.assert_all_metrics_covered()

    def test_per_instance_with_custom_tag_name(self, aggregator, dd_run_check, mock_performance_objects):
        """Test that use_per_instance_collection respects custom tag_name."""
        mock_performance_objects({'Foo': (['instance1'], {'Bar': [100]})})
        check = get_check(
            {
                'metrics': {
                    'Foo': {
                        'name': 'foo',
                        'tag_name': 'workload_group',
                        'use_per_instance_collection': True,
                        'counters': [{'Bar': {'name': 'bar'}}],
                    }
                }
            }
        )
        dd_run_check(check)

        tags = ['workload_group:instance1'] + list(GLOBAL_TAGS)
        aggregator.assert_metric('test.foo.bar', 100, tags=tags)
        aggregator.assert_all_metrics_covered()
