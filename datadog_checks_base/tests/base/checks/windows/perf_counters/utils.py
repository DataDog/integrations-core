# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import socket

from datadog_checks.base import PerfCountersBaseCheck

SERVER = socket.gethostname().lower()
GLOBAL_TAGS = ('server:{}'.format(SERVER),)


def get_check(instance=None, init_config=None):
    if instance is None:
        instance = {}
    if init_config is None:
        init_config = {}

    check = PerfCountersBaseCheck('test', init_config, [instance])
    check.namespace = 'test'
    check.hostname = SERVER

    return check
