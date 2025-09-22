# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from contextlib import closing
from typing import Any, Dict, Optional

from pymysql import Connection

from datadog_checks.base import is_affirmative
from datadog_checks.mysql.cursor import CommenterCursor


class GlobalVariables:
    """
    Handles collection and access to MySQL global variables.

    This class provides a centralized way to collect all global variables
    early in the check and access them through property methods.
    """

    def __init__(self):
        self._variables = None

    def collect(self, db: Connection):
        """
        Collect all global variables from the database.

        Args:
            db: Database connection
        """
        with closing(db.cursor(CommenterCursor)) as cursor:
            cursor.execute("SHOW GLOBAL VARIABLES;")
            self._variables = dict(cursor.fetchall())

    def _get_variable(self, variable_name: str, default: Any = None) -> Any:
        """
        Get a specific global variable value.

        Args:
            variable_name: The name of the variable to retrieve
            default: Default value if variable is not found

        Returns:
            The variable value or default if not found
        """
        if self._variables is None:
            return default
        return self._variables.get(variable_name, default)

    def _get_variable_enabled(self, variable_name: str) -> bool:
        """
        Check if a global variable is enabled (ON/YES/1).

        Args:
            variable_name: The name of the variable to check

        Returns:
            True if variable is enabled, False otherwise
        """
        value = self._get_variable(variable_name)
        return is_affirmative(value.lower().strip() if value is not None else value)

    @property
    def version(self) -> Optional[str]:
        return self._get_variable('version')

    @property
    def version_comment(self) -> Optional[str]:
        return self._get_variable('version_comment')

    @property
    def server_uuid(self) -> Optional[str]:
        return self._get_variable('server_uuid')

    @property
    def performance_schema_enabled(self) -> bool:
        return self._get_variable_enabled('performance_schema')

    @property
    def userstat_enabled(self) -> bool:
        return self._get_variable_enabled('userstat')

    @property
    def pid_file(self) -> Optional[str]:
        return self._get_variable('pid_file')

    @property
    def aurora_server_id(self) -> Optional[str]:
        return self._get_variable('aurora_server_id')

    @property
    def is_aurora(self) -> bool:
        return self.aurora_server_id is not None

    @property
    def log_bin_enabled(self) -> bool:
        return self._get_variable_enabled('log_bin')

    @property
    def key_buffer_size(self) -> Optional[int]:
        value = self._get_variable('key_buffer_size')
        try:
            return int(value) if value is not None else None
        except (ValueError, TypeError):
            return None

    @property
    def key_cache_block_size(self) -> Optional[int]:
        value = self._get_variable('key_cache_block_size')
        try:
            return int(value) if value is not None else None
        except (ValueError, TypeError):
            return None

    @property
    def all_variables(self) -> Dict[str, Any]:
        """Get all collected global variables."""
        if self._variables is None:
            return {}
        return self._variables.copy()
