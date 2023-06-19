# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from enum import Enum


class AppEnvVars:
    REPO = 'DDEV_REPO'
    INTERACTIVE = 'DDEV_INTERACTIVE'
    QUIET = 'DDEV_QUIET'
    VERBOSE = 'DDEV_VERBOSE'
    # https://no-color.org
    NO_COLOR = 'NO_COLOR'
    FORCE_COLOR = 'DDEV_COLOR'


class ConfigEnvVars:
    CONFIG = 'DDEV_CONFIG'


class VerbosityLevels(Enum):
    ERROR: int = -2
    WARN: int = -1
    QUIET: int = -1
    INFO: int = 0
    NORMAL: int = 0
    VERBOSE: int = 1
    VERY_VERBOSE: int = 2
    DEBUG: int = 3

    def __eq__(self, __value: object) -> bool:
        # Address mypy error: Unsupported operand types for == ("int" and "object")
        if not isinstance(__value, int):
            # If we return NotImplemented, Python will automatically try running __value.__eq__(self)
            return NotImplemented
        return self.value == __value

    def __lt__(self, __value: object) -> bool:
        # Address mypy error: Unsupported operand types for < ("int" and "object")
        if not isinstance(__value, int):
            # If we return NotImplemented, Python will automatically try running __value.__lt__(self)
            return NotImplemented
        return self.value < __value

    def __gt__(self, __value: object) -> bool:
        # Address mypy error: Unsupported operand types for > ("int" and "object")
        if not isinstance(__value, int):
            # If we return NotImplemented, Python will automatically try running __value.__gt__(self)
            return NotImplemented
        return self.value > __value
