# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import sys


def pytest_ignore_collect(path, config):
    return sys.platform != 'win32'
