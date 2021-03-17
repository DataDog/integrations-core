# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import time

from six import PY3

from datadog_checks.base.utils.platform import Platform

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
DRIVER_CONFIG_DIR = os.path.join(CURRENT_DIR, 'data', 'driver_config')

if PY3:
    # use higher precision clock available in Python3
    time_func = time.perf_counter
elif Platform.is_win32():
    # for tiny time deltas, time.time on Windows reports the same value
    # of the clock more than once, causing the computation of response_time
    # to be often 0; let's use time.clock that is more precise.
    time_func = time.clock
else:
    time_func = time.time


def set_default_driver_conf():
    if Platform.is_containerized():
        # Use default `./driver_config/odbcinst.ini` when Agent is running in docker.
        # `freetds` is shipped with the Docker Agent.
        os.environ.setdefault('ODBCSYSINI', DRIVER_CONFIG_DIR)


def construct_use_statement(database):
    return 'use [{}]'.format(database)
