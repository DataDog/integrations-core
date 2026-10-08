# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from typing import Any

from datadog_checks.base.utils.db.utils import resolve_db_host as agent_host_resolver

from . import aws
from .config import MySQLConfig


class MySQLInstanceMixin:
    """
    How a MySQL check instance identifies its database and connects to it: hostnames, the
    `database_instance` identifier and core tags, and connection arguments. Shared by the `mysql`
    check and the one-off task check, which must identify and reach the database exactly like the
    instance it was derived from. Mixed into a `DatabaseCheck`.
    """

    def _init_instance(self, init_config: dict) -> None:
        """Parse the instance configuration and set the tags derived from it."""
        self._resolved_hostname = None
        self._database_hostname = None
        self._config = MySQLConfig(self.instance, init_config)
        self.tag_manager.set_tags_from_list(self._config.tags, replace=True)  # Initialize from static config tags
        self.add_core_tags()
        self._cloud_metadata = self._config.cloud_metadata
        # Determine if using AWS managed authentication
        self._uses_aws_managed_auth = (
            'aws' in self.cloud_metadata
            and 'managed_authentication' in self.cloud_metadata.get('aws', {})
            and self.cloud_metadata['aws']['managed_authentication'].get('enabled', False)
        )

    @property
    def reported_hostname(self):
        # type: () -> str
        if self._config.exclude_hostname:
            return None
        return self.resolved_hostname

    @property
    def resolved_hostname(self):
        # type: () -> str
        if self._resolved_hostname is None:
            if self._config.reported_hostname:
                self._resolved_hostname = self._config.reported_hostname
            else:
                self._resolved_hostname = self.resolve_db_host()
        return self._resolved_hostname

    @property
    def cloud_metadata(self):
        return self._cloud_metadata

    @property
    def database_identifier_template(self) -> str:
        return self._config.database_identifier.get('template') or '$resolved_hostname'

    @property
    def database_identifier_params(self) -> dict:
        return {
            'resolved_hostname': self.resolved_hostname,
            'host': str(self._config.host),
            'port': str(self._config.port),
            'mysql_sock': str(self._config.mysql_sock),
        }

    @property
    def database_hostname(self):
        # type: () -> str
        if self._database_hostname is None:
            self._database_hostname = self.resolve_db_host()
        return self._database_hostname

    def add_core_tags(self):
        """
        Add tags that should be attached to every metric/event but which require check calculations outside the config.
        """
        self.tag_manager.set_tag("database_hostname", self.database_hostname, replace=True)
        self.tag_manager.set_tag("database_instance", self.database_identifier, replace=True)

    def resolve_db_host(self):
        return agent_host_resolver(self._config.host)

    def _get_connection_args(self) -> dict[str, Any]:
        ssl = dict(self._config.ssl) if self._config.ssl else None
        connection_args = {
            'ssl': ssl,
            'connect_timeout': self._config.connect_timeout,
            'read_timeout': self._config.read_timeout,
            'autocommit': True,
        }
        if self._config.charset:
            connection_args['charset'] = self._config.charset

        if self._config.defaults_file != '':
            connection_args['read_default_file'] = self._config.defaults_file
            return connection_args

        connection_args.update({'user': self._config.user, 'passwd': self._config.password})
        if self._uses_aws_managed_auth:
            # Generate AWS IAM auth token
            aws_managed_authentication = self.cloud_metadata['aws']['managed_authentication']
            region = self.cloud_metadata['aws']['region']
            password = aws.generate_rds_iam_token(
                host=self._config.host,
                username=self._config.user,
                port=self._config.port,
                region=region,
                role_arn=aws_managed_authentication.get('role_arn'),
            )
            connection_args.update({'user': self._config.user, 'passwd': password})
        if self._config.mysql_sock != '':
            connection_args.update({'unix_socket': self._config.mysql_sock})
        else:
            connection_args.update({'host': self._config.host})

        if self._config.port:
            connection_args.update({'port': self._config.port})
        return connection_args
