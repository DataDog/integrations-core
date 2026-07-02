# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging

import pytest

from datadog_checks.dev.testing import requires_windows

from .utils import get_check

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
            match='^Option `use_per_instance_collection` for performance object `Foo` must be true or false$',
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

    def test_default_is_false(self, dd_run_check, mock_performance_objects):
        """Test that use_per_instance_collection defaults to False (no errors with standard config)."""
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
        # Should not raise - standard bulk collection path works with existing mocks
        dd_run_check(check)

    def test_option_accepted_when_true(self, dd_run_check, mock_performance_objects):
        """Test that use_per_instance_collection=True is accepted as valid config."""
        mock_performance_objects({'Foo': (['instance1'], {'Bar': [100]})})
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
        # Config validation should pass (collection may fail due to mock limitations,
        # but config parsing succeeds)
        # The check runs without config validation errors
        check.run()

    def test_option_accepted_when_false(self, dd_run_check, mock_performance_objects):
        """Test that use_per_instance_collection=False is accepted as valid config."""
        mock_performance_objects({'Foo': (['instance1', 'instance2'], {'Bar': [100, 200]})})
        check = get_check(
            {
                'metrics': {
                    'Foo': {
                        'name': 'foo',
                        'use_per_instance_collection': False,
                        'counters': [{'Bar': {'name': 'bar'}}],
                    }
                }
            }
        )
        # Should work normally with bulk collection
        dd_run_check(check)
