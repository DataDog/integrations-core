# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base.errors import CheckException


class ConnectionError(CheckException):
    pass


class BadVersionError(CheckException):
    pass
