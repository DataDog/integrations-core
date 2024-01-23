# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import List, Optional  # noqa: F401

from datadog_checks.base import ConfigurationError, is_affirmative


class Config(object):
    """
    Hold instance configuration for a Snowflake check.
    Encapsulates the validation of an `instance` dictionary and authentication options.
    """

    DEFAULT_METRIC_GROUPS = [
        'snowflake.query',
        'snowflake.billing',
        'snowflake.storage',
        'snowflake.logins',
    ]

    DEFAULT_ORG_METRIC_GROUPS = [
        'snowflake.organization.warehouse',
        'snowflake.organization.currency',
        'snowflake.organization.storage',
    ]

    AUTHENTICATION_MODES = ['snowflake', 'oauth', 'snowflake_jwt']

    def __init__(self, instance=None):
        if instance is None:
            instance = {}

        account = instance.get('account')
        user = instance.get('user') or instance.get('username')
        password = instance.get('password')
        role = instance.get('role')
        database = instance.get('database', 'SNOWFLAKE')
        schema = instance.get('schema', 'ACCOUNT_USAGE')
        warehouse = instance.get('warehouse')
        passcode_in_password = instance.get('passcode_in_password', False)
        passcode = instance.get('passcode')
        client_prefetch_threads = instance.get('client_prefetch_threads', 4)
        login_timeout = instance.get('login_timeout', 60)
        ocsp_response_cache_filename = instance.get('ocsp_response_cache_filename')
        tags = instance.get('tags', [])
        authenticator = instance.get('authenticator', 'snowflake')
        token = instance.get('token', None)
        token_path = instance.get('token_path', None)
        private_key_path = instance.get('private_key_path', None)
        private_key_password = instance.get('private_key_password', None)
        client_keep_alive = instance.get('client_session_keep_alive', False)
        aggregate_last_24_hours = instance.get('aggregate_last_24_hours', False)
        custom_queries_defined = len(instance.get('custom_queries', [])) > 0

        default_metric_groups = (
            self.DEFAULT_ORG_METRIC_GROUPS if schema == 'ORGANIZATION_USAGE' else self.DEFAULT_METRIC_GROUPS
        )
        metric_groups = instance.get('metric_groups', default_metric_groups)

        if account is None:
            raise ConfigurationError('Must specify an account')

        if user is None:
            raise ConfigurationError('Must specify a user')

        if authenticator == 'snowflake':
            if is_affirmative(passcode_in_password) and passcode is None:
                raise ConfigurationError('MFA enabled, please specify a passcode')

            if password is None and private_key_path is None:
                raise ConfigurationError('Must specify a password or a private key if using snowflake authentication')

        elif authenticator == 'oauth':
            if token is None and token_path is None:
                raise ConfigurationError('If using OAuth, you must specify a `token` or a `token_path`')

            if token and token_path:
                raise ConfigurationError('`token` and `token_path` are set, please set only one option')

        elif authenticator not in self.AUTHENTICATION_MODES:
            raise ConfigurationError('The Authenticator method set is invalid: {}'.format(authenticator))

        if not isinstance(tags, list):
            raise ConfigurationError('tags {!r} must be a list (got {!r})'.format(tags, type(tags)))

        if role is None:
            raise ConfigurationError('Must specify a role')

        self.account = account  # type: str
        self.user = user  # type: str
        self.password = password  # type: str
        self.role = role  # type: Optional[str]
        self.database = database  # type: str   # By default only queries SNOWFLAKE DB and ACCOUNT_USAGE schema
        self.schema = schema  # type: str
        self.warehouse = warehouse  # type: Optional[str]
        self.passcode_in_password = passcode_in_password  # type: bool
        self.passcode = passcode  # type: Optional[str]
        self.client_prefetch_threads = client_prefetch_threads  # type: int
        self.login_timeout = login_timeout  # type: int
        self.ocsp_response_cache_filename = ocsp_response_cache_filename  # type: Optional[str]
        self.tags = tags  # type: List[str]
        self.metric_groups = metric_groups
        self.authenticator = authenticator
        self.token = token
        self.token_path = token_path
        self.private_key_path = private_key_path
        self.private_key_password = private_key_password
        self.client_keep_alive = client_keep_alive
        self.aggregate_last_24_hours = aggregate_last_24_hours
        self.custom_queries_defined = custom_queries_defined
