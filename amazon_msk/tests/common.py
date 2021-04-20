# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from datadog_checks.dev import get_here
from datadog_checks.dev.utils import read_file

HERE = get_here()
FIXTURES_DIR = os.path.join(HERE, 'fixtures')


def get_fixture_path(name):
    return os.path.join(FIXTURES_DIR, name)


def read_fixture(name):
    return read_file(get_fixture_path(name))
