# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from contextlib import closing

import pytest

from datadog_checks.mysql import MySql
from datadog_checks.mysql.cursor import CommenterCursor
from datadog_checks.mysql.global_variables import GlobalVariables

from . import common


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_global_variables_collection_and_access(instance_basic, root_conn):
    """Test that GlobalVariables class can collect and access global variables correctly."""
    mysql_check = MySql(common.CHECK_NAME, {}, [instance_basic])
    global_vars = GlobalVariables()

    # Query database directly to get expected values
    expected_variables = {}
    with closing(root_conn.cursor(CommenterCursor)) as cursor:
        cursor.execute("SHOW GLOBAL VARIABLES;")
        expected_variables = dict(cursor.fetchall())

    # Use GlobalVariables class to collect variables
    with mysql_check._connect() as db:
        global_vars.collect(db)

        # Test that all_variables returns the complete set
        collected_variables = global_vars.all_variables
        assert collected_variables is not None
        assert len(collected_variables) > 0
        assert collected_variables == expected_variables

        # Test specific variable properties
        _test_version_properties(global_vars, expected_variables)
        _test_boolean_properties(global_vars, expected_variables)
        _test_numeric_properties(global_vars, expected_variables)
        _test_aurora_properties(global_vars, expected_variables)

    mysql_check.cancel()


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_global_variables_uninitialized_state(instance_basic):
    """Test GlobalVariables behavior when not initialized."""
    global_vars = GlobalVariables()

    # Test that properties return None/default when not collected
    assert global_vars.version is None
    assert global_vars.version_comment is None
    assert global_vars.server_uuid is None
    assert global_vars.performance_schema_enabled is False
    assert global_vars.userstat_enabled is False
    assert global_vars.pid_file is None
    assert global_vars.aurora_server_id is None
    assert global_vars.is_aurora is False
    assert global_vars.log_bin_enabled is False
    assert global_vars.key_buffer_size is None
    assert global_vars.key_cache_block_size is None
    assert global_vars.all_variables == {}


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_global_variables_integration_with_mysql_check(instance_basic, root_conn):
    """Test that GlobalVariables integrates correctly with the main MySQL check."""
    mysql_check = MySql(common.CHECK_NAME, {}, [instance_basic])

    # Query database directly for comparison
    expected_variables = {}
    with closing(root_conn.cursor(CommenterCursor)) as cursor:
        cursor.execute("SHOW GLOBAL VARIABLES;")
        expected_variables = dict(cursor.fetchall())

    # Run the check which should collect global variables
    with mysql_check._connect() as db:
        # Manually collect global variables (this is what the check does)
        mysql_check.global_variables.collect(db)

        # Verify the check's global variables match direct query
        check_variables = mysql_check.global_variables.all_variables
        assert check_variables == expected_variables

        # Test that the check uses global variables correctly
        _test_check_uses_global_variables(mysql_check, expected_variables)

    mysql_check.cancel()


def _test_version_properties(global_vars, expected_variables):
    """Test version-related properties."""
    # Test version property
    expected_version = expected_variables.get('version')
    assert global_vars.version == expected_version
    assert isinstance(global_vars.version, str) if expected_version else global_vars.version is None

    # Test version_comment property
    expected_version_comment = expected_variables.get('version_comment')
    assert global_vars.version_comment == expected_version_comment
    assert (
        isinstance(global_vars.version_comment, str)
        if expected_version_comment
        else global_vars.version_comment is None
    )

    # Test server_uuid property
    expected_server_uuid = expected_variables.get('server_uuid')
    assert global_vars.server_uuid == expected_server_uuid
    assert isinstance(global_vars.server_uuid, str) if expected_server_uuid else global_vars.server_uuid is None


def _test_boolean_properties(global_vars, expected_variables):
    """Test boolean properties that check if features are enabled."""
    # Test performance_schema_enabled
    expected_performance_schema = expected_variables.get('performance_schema', '').lower()
    expected_performance_schema_enabled = expected_performance_schema in ('on', 'yes', '1')
    assert global_vars.performance_schema_enabled == expected_performance_schema_enabled

    # Test userstat_enabled - this variable might not exist in all MySQL versions
    expected_userstat = expected_variables.get('userstat', '').lower()
    expected_userstat_enabled = expected_userstat in ('on', 'yes', '1')
    # If userstat variable doesn't exist, the method should return False
    if 'userstat' not in expected_variables:
        assert global_vars.userstat_enabled is False
    else:
        assert global_vars.userstat_enabled == expected_userstat_enabled

    # Test log_bin_enabled
    expected_log_bin = expected_variables.get('log_bin', '').lower()
    expected_log_bin_enabled = expected_log_bin in ('on', 'yes', '1')
    assert global_vars.log_bin_enabled == expected_log_bin_enabled


def _test_numeric_properties(global_vars, expected_variables):
    """Test numeric properties that should be converted to integers."""
    # Test key_buffer_size
    expected_key_buffer_size = expected_variables.get('key_buffer_size')
    if expected_key_buffer_size:
        try:
            expected_key_buffer_size_int = int(expected_key_buffer_size)
            assert global_vars.key_buffer_size == expected_key_buffer_size_int
            assert isinstance(global_vars.key_buffer_size, int)
        except ValueError:
            # If the value can't be converted to int, it should return None
            assert global_vars.key_buffer_size is None
    else:
        assert global_vars.key_buffer_size is None

    # Test key_cache_block_size
    expected_key_cache_block_size = expected_variables.get('key_cache_block_size')
    if expected_key_cache_block_size:
        try:
            expected_key_cache_block_size_int = int(expected_key_cache_block_size)
            assert global_vars.key_cache_block_size == expected_key_cache_block_size_int
            assert isinstance(global_vars.key_cache_block_size, int)
        except ValueError:
            # If the value can't be converted to int, it should return None
            assert global_vars.key_cache_block_size is None
    else:
        assert global_vars.key_cache_block_size is None


def _test_aurora_properties(global_vars, expected_variables):
    """Test Aurora-specific properties."""
    # Test aurora_server_id
    expected_aurora_server_id = expected_variables.get('aurora_server_id')
    assert global_vars.aurora_server_id == expected_aurora_server_id
    assert (
        isinstance(global_vars.aurora_server_id, str)
        if expected_aurora_server_id
        else global_vars.aurora_server_id is None
    )

    # Test is_aurora
    expected_is_aurora = expected_aurora_server_id is not None
    assert global_vars.is_aurora == expected_is_aurora

    # Test pid_file
    expected_pid_file = expected_variables.get('pid_file')
    assert global_vars.pid_file == expected_pid_file
    assert isinstance(global_vars.pid_file, str) if expected_pid_file else global_vars.pid_file is None


def _test_check_uses_global_variables(mysql_check, expected_variables):
    """Test that the MySQL check uses global variables correctly."""
    global_vars = mysql_check.global_variables

    # Test that the check uses global variables for key cache calculations
    key_buffer_size = global_vars.key_buffer_size
    key_cache_block_size = global_vars.key_cache_block_size

    if key_buffer_size is not None and key_cache_block_size is not None:
        # The check should be able to use these values for calculations
        assert isinstance(key_buffer_size, int)
        assert isinstance(key_cache_block_size, int)
        assert key_buffer_size >= 0
        assert key_cache_block_size > 0

    # Test that the check can determine Aurora status
    is_aurora = global_vars.is_aurora
    assert isinstance(is_aurora, bool)

    # Test that the check can determine performance schema status
    performance_schema_enabled = global_vars.performance_schema_enabled
    assert isinstance(performance_schema_enabled, bool)

    # Test that the check can determine userstat status
    userstat_enabled = global_vars.userstat_enabled
    assert isinstance(userstat_enabled, bool)

    # Test that the check can determine binary logging status
    log_bin_enabled = global_vars.log_bin_enabled
    assert isinstance(log_bin_enabled, bool)


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_global_variables_edge_cases(instance_basic, root_conn):
    """Test edge cases and error handling in GlobalVariables."""
    mysql_check = MySql(common.CHECK_NAME, {}, [instance_basic])
    global_vars = GlobalVariables()

    with mysql_check._connect() as db:
        global_vars.collect(db)

        # Test _get_variable with non-existent variable
        non_existent_value = global_vars._get_variable('non_existent_variable', 'default_value')
        assert non_existent_value == 'default_value'

        # Test _get_variable_enabled with non-existent variable
        non_existent_enabled = global_vars._get_variable_enabled('non_existent_variable')
        assert non_existent_enabled is False

        # Test _get_variable_enabled with empty/null values
        # We can't easily test this with real MySQL, but we can verify the method exists
        assert hasattr(global_vars, '_get_variable_enabled')
        assert callable(global_vars._get_variable_enabled)

    mysql_check.cancel()


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_global_variables_multiple_collections(instance_basic, root_conn):
    """Test that GlobalVariables can be collected multiple times."""
    mysql_check = MySql(common.CHECK_NAME, {}, [instance_basic])
    global_vars = GlobalVariables()

    with mysql_check._connect() as db:
        # First collection
        global_vars.collect(db)
        first_collection = global_vars.all_variables.copy()
        first_version = global_vars.version

        # Second collection
        global_vars.collect(db)
        second_collection = global_vars.all_variables.copy()
        second_version = global_vars.version

        # Values should be the same (MySQL version doesn't change during test)
        assert first_collection == second_collection
        assert first_version == second_version

    mysql_check.cancel()
