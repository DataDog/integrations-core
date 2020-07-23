# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


class CheckException(Exception):
    """
    Generic base class for errors coming from checks
    """

    pass


class ConfigurationError(CheckException):
    """
    The configuration file is invalid
    """

    pass
