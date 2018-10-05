# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

E2E_FIXTURE_NAME = 'dd_environment'
E2E_SET_UP = 'DDEV_E2E_UP'
E2E_TEAR_DOWN = 'DDEV_E2E_DOWN'
TESTING_PLUGIN = 'DDEV_TESTING_PLUGIN'


def set_up_env():
    return os.getenv(E2E_SET_UP, 'true') != 'false'


def tear_down_env():
    return os.getenv(E2E_TEAR_DOWN, 'true') != 'false'
