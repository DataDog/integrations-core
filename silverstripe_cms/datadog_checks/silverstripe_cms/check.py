# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import re
import time

from datadog_checks.base import AgentCheck
from datadog_checks.base.errors import (
    ConfigurationError,
    ConfigValueError,
)

from . import constants
from .database_client import DatabaseClient


class SilverstripeCMSCheck(AgentCheck):
    # This will be the prefix of every metric and service check the integration sends
    __NAMESPACE__ = "silverstripe_cms"

    def __init__(self, name, init_config, instances):
        super(SilverstripeCMSCheck, self).__init__(name, init_config, instances)

        # Use self.instance to read the check configuration
        self.host_address = None
        self.database_type = self.instance.get("SILVERSTRIPE_DATABASE_TYPE")
        self.database_name = self.instance.get("SILVERSTRIPE_DATABASE_NAME")
        self.database_server_ip = self.instance.get("SILVERSTRIPE_DATABASE_SERVER_IP")
        self.database_port = self.instance.get("SILVERSTRIPE_DATABASE_PORT")
        self.database_username = self.instance.get("SILVERSTRIPE_DATABASE_USERNAME")
        self.database_password = self.instance.get("SILVERSTRIPE_DATABASE_PASSWORD")
        self.min_collection_interval = self.instance.get("min_collection_interval")
        self.custom_tags = self.instance.get("tags")

    def check(self, _) -> None:
        try:
            self.validate_configurations()
            message = "All the provided configurations in conf.yaml are valid."
            self.log.info(constants.LOG_TEMPLATE.format(host=self.database_server_ip, message=message))

            self.ingest_event(
                status=0,
                tags=constants.CONF_VAL_TAG,
                message=message,
                title=constants.CONF_VAL_TITLE,
                source_type=constants.CONF_VAL_SOURCE_TYPE,
            )
        except Exception:
            err_message = (
                "Error occurred while validating the provided configurations in conf.yaml."
                " Please check logs for more details."
            )
            self.ingest_event(
                status=2,
                tags=constants.CONF_VAL_TAG,
                message=err_message,
                title=constants.CONF_VAL_TITLE,
                source_type=constants.CONF_VAL_SOURCE_TYPE,
            )
            raise

        self.initialize_db_client()

        try:
            self.db_client.create_connection()
            message = "Authentication with Silverstripe CMS host is successful."
            self.log.info(constants.LOG_TEMPLATE.format(host=self.database_server_ip, message=message))

            self.ingest_event(
                status=0,
                tags=constants.AUTH_TAG,
                message=message,
                title=constants.AUTH_TITLE,
                source_type=constants.AUTH_SOURCE_TYPE,
            )
        except Exception:
            err_message = (
                "Error occurred while authenticating the Silverstripe CMS credentials."
                "Please check logs for more details."
            )
            self.ingest_event(
                status=2,
                tags=constants.AUTH_TAG,
                message=err_message,
                title=constants.AUTH_TITLE,
                source_type=constants.AUTH_SOURCE_TYPE,
            )
            raise

        self.metrics_collection_and_ingestion()
        self.db_client.close_connection()

    def validate_configurations(self) -> None:
        self.validate_string_configurations()
        self.validate_integer_configurations()
        self.validate_db_configurations()

        if not constants.MIN_COLLECTION_INTERVAL <= self.min_collection_interval <= constants.MAX_COLLECTION_INTERVAL:
            err_message = (
                f"'min_collection_interval' must be a positive integer in range of {constants.MIN_COLLECTION_INTERVAL}"
                f" to {constants.MAX_COLLECTION_INTERVAL}, got {self.min_collection_interval}."
            )
            self.log.error(constants.LOG_TEMPLATE.format(host=self.database_server_ip, message=err_message))
            raise ConfigValueError(err_message)

        if self.custom_tags and not isinstance(self.custom_tags, list):
            err_message = "'tags' field is not valid. Please provide proper custom tags."
            self.log.error(constants.LOG_TEMPLATE.format(host=self.database_server_ip, message=err_message))
            raise ConfigurationError(err_message)

    def validate_string_configurations(self) -> None:
        for field_name in constants.REQUIRED_STRING_FIELDS:
            value = self.instance.get(field_name)
            if value is None:
                raise ConfigurationError(f"'{field_name}' field is required.")
            if not isinstance(value, str):
                raise TypeError(f"'{field_name}' field must be a string.")
            if not value.strip():
                raise ValueError(f"Empty value is not allowed in '{field_name}'")

    def validate_integer_configurations(self) -> None:
        for field_name in constants.REQUIRED_INTEGER_FIELDS:
            value = self.instance.get(field_name)
            if value is None:
                raise ConfigurationError(f"'{field_name}' field is required.")
            if not isinstance(value, int) or isinstance(value, bool):
                raise TypeError(f"'{field_name}' field must be an integer.")

    def validate_db_configurations(self) -> None:
        if self.database_type not in constants.SUPPORTED_DATABASE_TYPES:
            err_message = (
                f"'SILVERSTRIPE_DATABASE_TYPE' must be one of {constants.SUPPORTED_DATABASE_TYPES}."
                " Please provide a valid SILVERSTRIPE_DATABASE_TYPE."
            )
            self.log.error(constants.LOG_TEMPLATE.format(host=self.database_server_ip, message=err_message))
            raise ConfigurationError(err_message)

        if not re.match(
            constants.IPV4_PATTERN,
            self.database_server_ip,
        ):
            err_message = (
                "'SILVERSTRIPE_DATABASE_SERVER_IP' is not valid."
                " Please provide a proper Silverstripe CMS database server IP address with ipv4 protocol."
            )
            self.log.error(constants.LOG_TEMPLATE.format(host=self.database_server_ip, message=err_message))
            raise ConfigurationError(err_message)

        if not constants.MIN_PORT <= self.database_port <= constants.MAX_PORT:
            err_message = (
                f"'SILVERSTRIPE_DATABASE_PORT' must be a positive integer in range of {constants.MIN_PORT}"
                f" to {constants.MAX_PORT}, got {self.database_port}."
            )
            self.log.error(constants.LOG_TEMPLATE.format(host=self.database_server_ip, message=err_message))
            raise ConfigurationError(err_message)

    def initialize_db_client(self) -> None:
        """Initializes Silverstripe CMS Database client."""
        self.db_client = DatabaseClient(
            self.database_type,
            self.database_name,
            self.database_server_ip,
            self.database_port,
            self.database_username,
            self.database_password,
            self.log,
        )

    def metrics_collection_and_ingestion(self) -> None:
        """Collects data from Silverstripe CMS database and ingests as the metrics."""
        message = "Start of the data collection/ingestion."
        self.log.info(constants.LOG_TEMPLATE.format(host=self.database_server_ip, message=message))
        start_time = time.time()

        for metric_name, table_config in constants.METRIC_TO_TABLE_CONFIG_MAPPING.items():
            try:
                sql_query = self.db_client.build_query(table_config)
                query_result = self.db_client.execute_query(sql_query)
                self.ingest_query_result(query_result, metric_name)
            except Exception as err:
                err_message = f"Error occurred while collecting/ingesting data. | Error={err}."
                self.log.error(constants.LOG_TEMPLATE.format(host=self.database_server_ip, message=err_message))

        for metric_name, sql_query in constants.METRIC_TO_QUERY_MAPPING.items():
            try:
                converted_query = self.db_client.convert_query_for_db(sql_query)
                query_result = self.db_client.execute_query(converted_query)
                self.ingest_query_result(query_result, metric_name)
            except Exception as err:
                err_message = f"Error occurred while collecting/ingesting data. | Error={err}."
                self.log.error(constants.LOG_TEMPLATE.format(host=self.database_server_ip, message=err_message))

        elapsed_time = time.time() - start_time
        message = f"End of the data collection/ingestion. Time taken: {elapsed_time:.3f} seconds."
        self.log.info(constants.LOG_TEMPLATE.format(host=self.database_server_ip, message=message))

    def ingest_query_result(self, query_result: list, metric_name: str) -> None:
        """Extracts the query result to make it ready for ingestion as metrics."""
        try:
            common_tags = [f"silverstripe_host:{self.database_server_ip}"] + (
                self.custom_tags if self.custom_tags else []
            )
            for row_data in query_result:
                tags = self.get_metric_tags(dict(row_data))
                if tags:
                    self.gauge(metric_name, row_data["RowCount"], tags=tags + common_tags)
        except Exception as err:
            err_message = f"Error occurred while processing/ingesting data. | Error={err}."
            self.log.error(constants.LOG_TEMPLATE.format(host=self.database_server_ip, message=err_message))

    def get_metric_tags(self, row_data: dict) -> list:
        """Return metric tags from each row along with custom tags."""
        tags = []
        for column_name, value in row_data.items():
            # Skipping None value and RowCount column in tag
            if value is None or column_name == "RowCount":
                continue
            elif column_name == "ClassName":
                class_name = value.rsplit("\\", 1)[-1]
                tag = constants.CLASSNAME_TO_TAG_MAPPING.get(class_name)
                if tag:
                    tags.append(tag)
            else:
                tags.append(f"{column_name.lower()}:{value}")
        return tags

    def ingest_event(self, **event_args) -> None:
        """
        Ingest Event for any particular milestone with success or error status.
        """
        self.event(
            {
                "host": self.host_address,
                "alert_type": constants.STATUS_NUMBER_TO_VALUE[event_args.get("status")],
                "tags": event_args.get("tags"),
                "msg_text": event_args.get("message"),
                "msg_title": event_args.get("title"),
                "source_type_name": event_args.get("source_type"),
            }
        )
