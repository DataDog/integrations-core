# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


class CheckException(Exception):
    """
    Generic base class for errors coming from checks
    """


class ConfigurationError(CheckException):
    """
    The configuration file is invalid
    """


class ConfigTypeError(ConfigurationError):
    """
    The configuration file defines incorrect types
    """


class ConfigValueError(ConfigurationError):
    """
    The configuration file defines invalid values
    """


class ConfigMissingError(ConfigurationError):
    """
    The configuration file is missing settings
    """
