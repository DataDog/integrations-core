# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from typing import Any
from urllib.parse import quote_plus

from sqlalchemy import create_engine, text
from sqlalchemy.engine.cursor import CursorResult
from sqlalchemy.exc import SQLAlchemyError

from datadog_checks.base.errors import ConfigurationError

from .constants import (
    DB_CONNECTION_TIMEOUT_IN_SECONDS,
    LOG_TEMPLATE,
    MYSQL,
    MYSQL_DB_URL_PREFIX,
    POSTGRES_DB_URL_PREFIX,
)
from .dataclasses import TableConfig


class DatabaseClient:
    def __init__(
        self, db_type: str, db_name: str, db_host: str, db_port: int, db_username: str, db_password: str, logger
    ):
        self.log = logger
        self.db_type = db_type
        self.db_host = db_host
        self.db_connection_url = self._get_connection_url(db_type, db_name, db_host, db_port, db_username, db_password)
        self.connection = None

    def _get_connection_url(
        self, db_type: str, db_name: str, db_host: str, db_port: int, db_username: str, db_password: str
    ) -> str:
        """Build a Database connection url using based on database type"""
        connection_url_prefix = MYSQL_DB_URL_PREFIX if db_type == MYSQL else POSTGRES_DB_URL_PREFIX
        return f"{connection_url_prefix}://{quote_plus(db_username)}:{quote_plus(db_password)}@{db_host}:{db_port}/{db_name}"

    def create_connection(self) -> None:
        try:
            engine_instance = create_engine(
                self.db_connection_url,
                isolation_level="READ COMMITTED",
                connect_args={
                    "connect_timeout": DB_CONNECTION_TIMEOUT_IN_SECONDS,
                },
            )
            self.connection = engine_instance.connect()
            message = "Successfully authenticated with the database."
            self.log.info(LOG_TEMPLATE.format(host=self.db_host, message=message))

        except SQLAlchemyError as db_err:
            err_message = (
                f"Authentication failed for provided credentials. Please check the provided credentials."
                f" | Error={db_err}."
            )
            self.log.error(LOG_TEMPLATE.format(host=self.db_host, message=err_message))
            raise ConfigurationError(err_message)

    def close_connection(self) -> None:
        try:
            self.connection.close()
            message = "Connection closed successfully."
            self.log.info(LOG_TEMPLATE.format(host=self.db_host, message=message))
        except SQLAlchemyError as db_err:
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

    def execute_query(self, query: str) -> CursorResult[Any]:
        try:
            return self.connection.execute(text(query))
        except SQLAlchemyError as db_err:
            err_message = f"Error occurred while executing query: {query}. | Error={db_err}."
            self.log.error(LOG_TEMPLATE.format(host=self.db_host, message=err_message))
