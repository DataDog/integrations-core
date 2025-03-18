# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

from unittest.mock import MagicMock, patch

import pytest

from datadog_checks.base import ConfigurationError
from datadog_checks.pgbouncer import PgBouncer


@pytest.mark.unit
def test_config_missing_host(instance):
    with pytest.raises(ConfigurationError):
        del instance['host']
        PgBouncer('pgbouncer', {}, [instance])


@pytest.mark.unit
def test_config_missing_user(instance):
    with pytest.raises(ConfigurationError):
        del instance['username']
        PgBouncer('pgbouncer', {}, [instance])


@pytest.mark.unit
@pytest.mark.parametrize('use_cached', [True, False])
def test_connection_cleanup_on_error(instance, use_cached):
    """
    This test ensures that connection resources are properly cleaned up when a connection fails to establish.
    """
    with patch('psycopg2.connect', side_effect=Exception("Connection failed")):
        check = PgBouncer('pgbouncer', {}, [instance])
        with pytest.raises(Exception):
            check._get_connection(use_cached=use_cached)

        # Verify no connection was stored
        assert check.connection is None


@pytest.mark.unit
def test_connection_lifecycle_without_caching(instance):
    """
    This test verifies the complete lifecycle of a connection when caching is disabled (use_cached=False).
    """
    mock_connection = MagicMock()
    mock_connection.notices = []
    mock_connection.cursor.return_value.__enter__.return_value.fetchone.return_value = ['1.2.3']

    with patch('psycopg2.connect', return_value=mock_connection) as mock_connect:
        instance['use_cached'] = False
        check = PgBouncer('pgbouncer', {}, [instance])

        # Run the check
        check.check(instance)

        # Verify exactly one connection was created and closed
        assert mock_connect.call_count == 1
        assert mock_connection.close.call_count == 1
        assert check.connection is None


@pytest.mark.unit
def test_connection_lifecycle_with_caching(instance):
    """
    This test verifies connection handling when caching is enabled (use_cached=True).
    This test ensures that cached connections persist correctly between checks while still being
    properly managed.
    """
    mock_connection = MagicMock()
    mock_connection.notices = []
    mock_connection.cursor.return_value.__enter__.return_value.fetchone.return_value = ['1.2.3']

    with patch('psycopg2.connect', return_value=mock_connection) as mock_connect:
        instance['use_cached'] = True
        check = PgBouncer('pgbouncer', {}, [instance])

        # Run the check
        check.check(instance)

        # Verify exactly one connection was created and kept open
        assert mock_connect.call_count == 1
        assert mock_connection.close.call_count == 0
        assert check.connection is not None


@pytest.mark.unit
@pytest.mark.parametrize('use_cached', [True, False])
def test_connection_cleanup_on_isolation_level_error(instance, use_cached):
    """
    This test ensures that connection resources are properly cleaned up when setting the isolation level fails.
    """
    mock_connection = MagicMock()
    mock_connection.set_isolation_level.side_effect = Exception("Failed to set isolation level")

    with patch('psycopg2.connect', return_value=mock_connection):
        check = PgBouncer('pgbouncer', {}, [instance])
        with pytest.raises(Exception):
            check._get_connection(use_cached=use_cached)

        # Verify connection was closed and not stored
        assert mock_connection.close.call_count == 1
        assert check.connection is None
