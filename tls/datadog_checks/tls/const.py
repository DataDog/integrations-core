# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from .utils import days_to_seconds

SERVICE_CHECK_CAN_CONNECT = 'tls.can_connect'
SERVICE_CHECK_VERSION = 'tls.version'
SERVICE_CHECK_VALIDATION = 'tls.cert_validation'
SERVICE_CHECK_EXPIRATION = 'tls.cert_expiration'

DEFAULT_EXPIRE_DAYS_WARNING = 14
DEFAULT_EXPIRE_DAYS_CRITICAL = 7
DEFAULT_EXPIRE_SECONDS_WARNING = days_to_seconds(DEFAULT_EXPIRE_DAYS_WARNING)
DEFAULT_EXPIRE_SECONDS_CRITICAL = days_to_seconds(DEFAULT_EXPIRE_DAYS_CRITICAL)
