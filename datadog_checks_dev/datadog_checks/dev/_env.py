# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

TEAR_DOWN_ENV = 'DDEV_TEAR_DOWN_ENV'


def tear_down_env():
    return os.getenv(TEAR_DOWN_ENV, 'true') != 'false'
