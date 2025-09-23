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


class ConfigNotSupportedError(ConfigurationError):
    """
    The instance configuration is not supported
    """


class SkipInstanceError(ConfigNotSupportedError):
    """
    Raise SkipInstanceError in a check's __new__ or __init__ to skip loading the
    provided instance without raising an error.
    Example usage is when the instance configuration should be processed by a
    different version of the check (Go vs Python check loader).
    """

    # Keep this error prefix in sync with the Python check loader in datadogagent.
    # The string is used to identify this error across the rtloader boundary.
    PREFIX_PATTERN = "The integration refused to load the check configuration, it may be too old or too new."

    def __init__(self, *args, **kwargs):
        args = list(args)
        if len(args) == 0:
            # Set a default error message if none is provided
            message = "Check the documentation for options that select the integration version to use."
            args = [message]

        # Prepend the identifying prefix.
        # args[0] = f"{self.PREFIX_PATTERN} {args[0]}"
        args[0] = "{} {}".format(self.PREFIX_PATTERN, args[0])
        super(SkipInstanceError, self).__init__(*args, **kwargs)
