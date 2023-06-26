# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import os

from datadog_checks.dev import get_here

HERE = get_here()


def get_fixture_path(filename):
    return os.path.join(HERE, 'fixtures', filename)
