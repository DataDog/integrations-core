# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from contextlib import contextmanager

import pytest

from datadog_checks.base.checks.db import DatabaseCheck
from datadog_checks.base.utils.db.schemas import SchemaCollector, SchemaCollectorConfig


class TestDatabaseCheck(DatabaseCheck):
    __test__ = False
    def __init__(self):
        super().__init__()
        self._reported_hostname = "test_hostname"
        self._database_identifier = "test_database_identifier"
        self._dbms_version = "test_dbms_version"
        self._agent_version = "test_agent_version"
        self._tags = ["test_tag"]
        self._cloud_metadata = {"test_cloud_metadata": "test_cloud_metadata"}

    @property
    def reported_hostname(self):
        return self._reported_hostname

    @property
    def database_identifier(self):
        return self._database_identifier

    @property
    def dbms_version(self):
        return self._dbms_version

    @property
    def agent_version(self):
        return self._agent_version

    @property
    def tags(self):
        return self._tags

    @property
    def cloud_metadata(self):
        return self._cloud_metadata


class TestSchemaCollector(SchemaCollector):
    __test__ = False
    def __init__(self, check: DatabaseCheck, config: SchemaCollectorConfig):
        super().__init__(check, config)
        self._row_index = 0
        self._rows = [{'table_name': 'test_table'}]

    def _get_databases(self):
        return [{'name': 'test_database'}]

    @contextmanager
    def _get_cursor(self, database: str):
        yield {}

    def _get_next(self, _cursor):
        if self._row_index < len(self._rows):
            row = self._rows[self._row_index]
            self._row_index += 1
            return row
        return None

    def _map_row(self, database: str, cursor_row: dict):
        return {**database}


@pytest.mark.unit
def test_schema_collector():
    check = TestDatabaseCheck()
    collector = TestSchemaCollector(check, SchemaCollectorConfig())
    collector.collect_schemas()
