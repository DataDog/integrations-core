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

    def __init__(self, instance=None):
        if instance is None:
            instance = {}

        account = instance.get('account')
        user = instance.get('user')
        password = instance.get('password')
        role = instance.get('role', 'ACCOUNTADMIN')
        warehouse = instance.get('warehouse')
        passcode_in_password = instance.get('passcode_in_password', False)
        passcode = instance.get('passcode')
        client_prefetch_threads = instance.get('client_prefetch_threads', 4)
        login_timeout = instance.get('login_timeout', 60)
        ocsp_response_cache_filename = instance.get('ocsp_response_cache_filename')
        tags = instance.get('tags', [])

        # min_collection_interval defaults to 60 minutes
        min_collection = instance.get('min_collection_interval', 3600)

        metric_groups = instance.get('metric_groups', self.DEFAULT_METRIC_GROUP)

        if account is None:
            raise ConfigurationError('Must specify an account')

        if user is None or password is None:
            raise ConfigurationError('Must specify a user and password')

        if not isinstance(tags, list):
            raise ConfigurationError('tags {!r} must be a list (got {!r})'.format(tags, type(tags)))

        if is_affirmative(passcode_in_password) and passcode is None:
            raise ConfigurationError('MFA enabled, please specify a passcode')

        self.account = account  # type: str
        self.user = user  # type: str
        self.password = password  # type: str
        self.role = role  # type: Optional[str]
        self.warehouse = warehouse  # type: Optional[str]
        self.passcode_in_password = passcode_in_password  # type: bool
        self.passcode = passcode  # type: Optional[str]
        self.client_prefetch_threads = client_prefetch_threads  # type: int
        self.login_timeout = login_timeout  # type: int
        self.ocsp_response_cache_filename = ocsp_response_cache_filename  # type: Optional[str]
        self.tags = tags  # type: List[str]
        self.min_collection = min_collection
        self.metric_groups = metric_groups
