# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import List, Optional

from datadog_checks.base import ConfigurationError, is_affirmative


class Config(object):
    """
    Hold instance configuration for a Snowflake check.
    Encapsulates the validation of an `instance` dictionary and authentication options.
    """

    DEFAULT_METRIC_GROUP = [
        'snowflake.query',
        'snowflake.billing',
        'snowflake.storage',
        'snowflake.logins',
    ]

    AUTHENTICATION_MODES = ['snowflake', 'oauth']

    def __init__(self, instance=None):
        if instance is None:
            instance = {}

        account = instance.get('account')
        user = instance.get('user')
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
        client_keep_alive = instance.get('client_session_keep_alive', False)

        metric_groups = instance.get('metric_groups', self.DEFAULT_METRIC_GROUP)

        if account is None:
            raise ConfigurationError('Must specify an account')

        if user is None or password is None:
            raise ConfigurationError('Must specify a user and password')

        if not isinstance(tags, list):
            raise ConfigurationError('tags {!r} must be a list (got {!r})'.format(tags, type(tags)))

        if is_affirmative(passcode_in_password) and passcode is None:
            raise ConfigurationError('MFA enabled, please specify a passcode')

        if authenticator not in self.AUTHENTICATION_MODES:
            raise ConfigurationError('The Authenticator method set is invalid: {}'.format(authenticator))

        if authenticator == 'oauth' and token is None:
            raise ConfigurationError('If using OAuth, you must specify a token')

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
        self.client_keep_alive = client_keep_alive
