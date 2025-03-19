# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

from unittest.mock import MagicMock, patch

import psycopg2 as pg
import pytest

from datadog_checks.base import AgentCheck, ConfigurationError
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
    instance['use_cached'] = use_cached
    with patch('psycopg2.connect', side_effect=Exception("Connection failed")):
        check = PgBouncer('pgbouncer', {}, [instance])
        with pytest.raises(Exception):
            check._get_connection()

        # Verify no connection was stored
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
def test_connection_lifecycle(instance, use_cached):
    """
    This test verifies the complete lifecycle of a connection when caching is disabled (use_cached=False).
    """
    mock_connection = MagicMock()
    mock_connection.notices = []
    mock_connection.cursor.return_value.__enter__.return_value.fetchone.return_value = ['1.2.3']
    instance['use_cached'] = use_cached
    with patch('psycopg2.connect', return_value=mock_connection) as mock_connect:
        check = PgBouncer('pgbouncer', {}, [instance])

        # Run the check
        check.check(instance)

        # Verify exactly one connection was created and closed
        assert mock_connect.call_count == 1
        if not use_cached:
            assert mock_connection.close.call_count == 1
            assert check.connection is None
        else:
            assert mock_connection.close.call_count == 0
            assert check.connection is not None


@pytest.mark.unit
def test_metadata_collection(instance):
    """
    This test verifies that metadata collection works correctly.
    """
    mock_connection = MagicMock()
    mock_connection.notices = []
    mock_connection.cursor.return_value.__enter__.return_value.fetchone.return_value = ['PgBouncer 1.2.3']

    with patch('psycopg2.connect', return_value=mock_connection):
        check = PgBouncer('pgbouncer', {}, [instance])
        with patch.object(check, 'set_metadata') as mock_set_metadata:
            check.check(instance)
            mock_set_metadata.assert_called_once_with('version', '1.2.3')


@pytest.mark.unit
def test_metadata_collection_without_connection(instance):
    """
    This test verifies that metadata collection handles the case where no connection is available.
    """
    check = PgBouncer('pgbouncer', {}, [instance])

    # Try to collect metadata without a connection
    with patch.object(check, 'set_metadata') as mock_set_metadata:
        check._collect_metadata(None)
        mock_set_metadata.assert_not_called()


@pytest.mark.unit
@pytest.mark.parametrize('use_cached', [True, False])
def test_connection_cleanup_on_isolation_level_error(instance, use_cached):
    """
    This test ensures that connection resources are properly cleaned up when setting the isolation level fails.
    """
    instance['use_cached'] = use_cached
    mock_connection = MagicMock()
    mock_connection.set_isolation_level.side_effect = Exception("Failed to set isolation level")

    with patch('psycopg2.connect', return_value=mock_connection):
        check = PgBouncer('pgbouncer', {}, [instance])
        with pytest.raises(Exception):
            check.check(instance)

        # Verify connection was closed and not stored
        assert mock_connection.close.call_count == 1
        assert check.connection is None


@pytest.mark.unit
@pytest.mark.parametrize('use_cached', [True, False])
def test_connection_lifecycle_pg_error_once(instance, use_cached):
    """
    This test ensures that when a pg.Error occurs once inside _collect_stats,
    the connection is properly closed and a new connection is established.
    The second attempt succeeds, and the check completes successfully.
    """
    instance['use_cached'] = use_cached

    # First connection: simulate failure by having cursor() raise pg.Error.
    mock_conn1 = MagicMock()
    mock_conn1.cursor.side_effect = pg.Error("Simulated pg.Error on first connection")

    # Second connection: simulate a successful cursor (empty result set).
    mock_conn2 = MagicMock()
    fake_cursor = MagicMock()
    fake_cursor.__enter__.return_value = fake_cursor
    fake_cursor.execute.return_value = None
    fake_cursor.__iter__.return_value = iter([])  # No rows returned
    mock_conn2.cursor.return_value = fake_cursor

    # pg.connect will return mock_conn1 first, then mock_conn2.
    with patch('psycopg2.connect', side_effect=[mock_conn1, mock_conn2]) as mock_connect:
        check = PgBouncer('pgbouncer', {}, [instance])
        # Patch _collect_metadata to avoid its side effects
        with patch.object(check, '_collect_metadata', return_value=None):
            with patch.object(check, 'service_check') as service_check_patch:
                # Running check() should trigger a restart:
                check.check(instance)

                # The first connection should be closed during the restart
                mock_conn1.close.assert_called_once()
                # The second connection should be closed in the finally clause (since use_cached is False)
                if not use_cached:
                    mock_conn2.close.assert_called_once()
                else:
                    mock_conn2.close.assert_not_called()
                # Two connections should have been created
                assert mock_connect.call_count == 2
                # The final service check should be sent with status OK
                service_check_patch.assert_called_with(
                    PgBouncer.SERVICE_CHECK_NAME, AgentCheck.OK, tags=check._get_service_checks_tags()
                )


@pytest.mark.unit
@pytest.mark.parametrize('use_cached', [True, False])
def test_connection_lifecycle_pg_error_twice(instance, use_cached):
    """
    This test ensures that when a pg.Error occurs twice inside _collect_stats,
    the connection is properly closed and a new connection is attempted.
    Since the second attempt also fails, the check ultimately raises an exception.
    """
    instance['use_cached'] = use_cached

    # Both connections simulate failure.
    mock_conn1 = MagicMock()
    mock_conn1.cursor.side_effect = pg.Error("Simulated pg.Error on first connection")

    mock_conn2 = MagicMock()
    mock_conn2.cursor.side_effect = pg.Error("Simulated pg.Error on second connection")

    with patch('psycopg2.connect', side_effect=[mock_conn1, mock_conn2]) as mock_connect:
        check = PgBouncer('pgbouncer', {}, [instance])
        with patch.object(check, '_collect_metadata', return_value=None):
            with patch.object(check, 'service_check') as service_check_patch:
                with pytest.raises(Exception):
                    check.check(instance)

                assert mock_connect.call_count == 2
                mock_conn1.close.assert_called_once()
                mock_conn2.close.assert_called_once()
                # The service check should not be called since both connections failed
                service_check_patch.assert_not_called()


@pytest.mark.unit
def test_no_new_connection_when_cached_exists(instance):
    """
    This test verifies that when use_cached is True and self.connection is already set,
    no new connection is created during check execution.
    """
    instance['use_cached'] = True

    # Create a mock connection that will be set as self.connection
    mock_existing_connection = MagicMock()
    mock_existing_connection.notices = []
    mock_existing_connection.cursor.return_value.__enter__.return_value.fetchone.return_value = ['1.2.3']

    with patch('psycopg2.connect') as mock_connect:
        check = PgBouncer('pgbouncer', {}, [instance])

        # Set the existing connection
        check.connection = mock_existing_connection

        check.check(instance)

        # Verify that no new connection was created
        mock_connect.assert_not_called()

        # Verify that the existing connection is still open
        assert check.connection is not None
