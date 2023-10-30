# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
class AppEnvVars:
    REPO = 'DDEV_REPO'
    INTERACTIVE = 'DDEV_INTERACTIVE'
    QUIET = 'DDEV_QUIET'
    VERBOSE = 'DDEV_VERBOSE'
    # https://no-color.org
    NO_COLOR = 'NO_COLOR'
    FORCE_COLOR = 'FORCE_COLOR'


class ConfigEnvVars:
    DATA = 'DDEV_DATA_DIR'
    CACHE = 'DDEV_CACHE_DIR'
    CONFIG = 'DDEV_CONFIG'


class VerbosityLevels:
    ERROR = -2
    WARNING = -1
    INFO = 0
    DEBUG = 1
    TRACE = 2
