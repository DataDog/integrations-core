# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

# DB fixtures and helpers
import pytest
import vertica_python as vertica

from . import common

BASE_DB_OPTIONS = common.connection_options_from_config(common.CONFIG)


@pytest.fixture
def setup_db_tables():
    """Fixture to set up tables to a specific state and tear down later.

    Important note: the schemas and tables are dropped after fixture use,
    without guarantees in regards to whether the schema originally existed.
    This should be good enough for a testing setup.
    """
    fixtures = []

    def _setup_db_table(schema_name, table_name, schema, data, options=None):
        fixture = VerticaFixture()
        fixtures.append(fixture)
        return fixture.set_up(schema_name, table_name, schema, data, options)

    yield _setup_db_table

    for fixture in fixtures:
        fixture.tear_down()


class VerticaFixture:
    default_config = common.connection_options_from_config(common.CONFIG)

    def set_up(self, schema_name, table_name, schema, data, options=None):
        self.schema_name = schema_name
        self.table_name = table_name
        self.options = options or VerticaFixture.default_config

        with vertica.connect(**self.options) as conn:
            cur = conn.cursor()

            # Create schema
            cur.execute('CREATE SCHEMA IF NOT EXISTS {}'.format(self.schema_name))

            # Create table
            column_definitions = ', '.join(' '.join(column) for column in schema)
            cur.execute(
                'CREATE TABLE {schema}.{table} ({column_definitions})'.format(
                    schema=self.schema_name,
                    table=self.table_name,
                    column_definitions=column_definitions,
                )
            )
            conn.commit()

            # Insert the data into the table through a copy
            columns = ', '.join(name for name, _type in schema)
            cur.copy(
                "COPY {schema}.{table} ({columns}) FROM stdin DELIMITER ','".format(
                    schema=self.schema_name,
                    table=self.table_name,
                    columns=columns,
                ),
                data,
            )

    def tear_down(self):
        # No nead to tear anything down if fixture has not been called
        if not hasattr(self, 'options'):
            return

        with vertica.connect(**self.options) as conn:
            cur = conn.cursor()

            # Drop table
            cur.execute('DROP TABLE IF EXISTS {}.{}'.format(self.schema_name, self.table_name))

            # Drop schema
            cur.execute('DROP SCHEMA IF EXISTS {}'.format(self.schema_name))

            conn.commit()
