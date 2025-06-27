# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import psycopg
import pymysql
from psycopg import ClientCursor
from psycopg.rows import dict_row

from datadog_checks.base.errors import ConfigurationError

from .constants import (
    DB_CONNECTION_TIMEOUT_IN_SECONDS,
    LOG_TEMPLATE,
    MYSQL,
)
from .dataclasses import TableConfig


class DatabaseClient:
    def __init__(
        self, db_type: str, db_name: str, db_host: str, db_port: int, db_username: str, db_password: str, logger
    ):
        self.log = logger
        self.db_type = db_type
        self.db_host = db_host
        self.db_port = db_port
        self.db_username = db_username
        self.db_password = db_password
        self.db_name = db_name
        self.connection = None
        self.cursor = None

    def create_connection(self) -> None:
        try:
            if self.db_type == MYSQL:
                self.connection = pymysql.connect(
                    host=self.db_host,
                    port=self.db_port,
                    user=self.db_username,
                    password=self.db_password,
                    database=self.db_name,
                    cursorclass=pymysql.cursors.DictCursor,
                    connect_timeout=DB_CONNECTION_TIMEOUT_IN_SECONDS,
                )
            else:
                # PostgreSQL connection settings
                self.connection = psycopg.connect(
                    host=self.db_host,
                    port=self.db_port,
                    user=self.db_username,
                    password=self.db_password,
                    dbname=self.db_name,
                    cursor_factory=ClientCursor,
                    connect_timeout=DB_CONNECTION_TIMEOUT_IN_SECONDS,
                    autocommit=True,
                )
            message = f"Successfully authenticated with the {self.db_type} database."
            self.log.info(LOG_TEMPLATE.format(host=self.db_host, message=message))
            if self.db_type == MYSQL:
                self.cursor = self.connection.cursor()
            else:
                self.cursor = self.connection.cursor(row_factory=dict_row)
        except (pymysql.Error, psycopg.Error) as db_err:
            err_message = (
                f"Authentication failed for provided credentials. Please check the provided credentials."
                f" | Error={db_err}."
            )
            self.log.error(LOG_TEMPLATE.format(host=self.db_host, message=err_message))
            raise ConfigurationError(err_message)

    def close_connection(self) -> None:
        try:
            self.cursor.close()
            self.connection.close()
            message = "Connection closed successfully."
            self.log.info(LOG_TEMPLATE.format(host=self.db_host, message=message))
        except (pymysql.Error, psycopg.Error) as db_err:
            err_message = f"Error occurred while closing the connection. | Error={db_err}."
            self.log.error(LOG_TEMPLATE.format(host=self.db_host, message=err_message))

    def build_query(self, table_config: TableConfig) -> str:
        query_columns = f"""{", ".join(f"`{column}`" for column in table_config.group_by)}"""
        where_clause = (
            " WHERE "
            + f" {table_config.conditional_operator} ".join(
                f"`{column}`{comparison}{repr(value)}" for column, comparison, value in table_config.conditions
            )
            if table_config.conditions
            else ""
        )
        group_by_clause = f" GROUP BY {query_columns}"

        query = (
            f"SELECT {query_columns}, COUNT(*) as `RowCount` FROM `{table_config.name}`{where_clause}{group_by_clause}"
        )
        return self.convert_query_for_db(query)

    def convert_query_for_db(self, query: str) -> str:
        return query.replace("`", '"') if self.db_type == "PostgreSQL" else query

    def execute_query(self, query: str) -> list:
        try:
            self.cursor.execute(query)
            return self.cursor.fetchall()
        except (pymysql.Error, psycopg.Error) as db_err:
            err_message = f"Error occurred while executing query: {query}. | Error={db_err}."
            self.log.error(LOG_TEMPLATE.format(host=self.db_host, message=err_message))
